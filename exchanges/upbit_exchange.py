# exchanges/upbit_exchange.py
"""
업비트 거래소 어댑터 (현물 전용)
- 현물 거래만 지원 (선물 없음)
- API: pyupbit
- 심볼 형식: KRW-BTC
- 특이사항: 레버리지 없음, SL은 로컬 관리
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

from .base_exchange import BaseExchange, Position

try:
    import pyupbit
except ImportError:
    pyupbit = None


class UpbitExchange(BaseExchange):
    """업비트 거래소 어댑터 (현물 전용)"""
    
    @property

    def fetchTime(self):
        """Upbit는 시간 API 미지원 - 로컬 시간 반환"""
        import time
        return int(time.time() * 1000)
    
    def sync_time(self):
        """시간 동기화 (Upbit는 스킵)"""
        self.time_offset = 0
        return True

    def name(self) -> str:
        return "Upbit"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.upbit = None
        
        # 심볼 변환 (BTCUSDT -> KRW-BTC)
        raw_symbol = config.get('symbol', 'BTCUSDT')
        self.symbol = self._normalize_symbol(raw_symbol)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """심볼 정규화 (BTCUSDT/BTCUSD -> KRW-BTC)"""
        base = symbol.replace('USDT', '').replace('USD', '').replace('KRW', '').replace('-', '')
        return f"KRW-{base}"
    
    def connect(self) -> bool:
        """API 연결"""
        if pyupbit is None:
            logging.error("pyupbit not installed! Run: pip install pyupbit")
            return False
        
        try:
            if self.api_key and self.api_secret:
                self.upbit = pyupbit.Upbit(self.api_key, self.api_secret)
                balance = self.get_balance()
                logging.info(f"Upbit connected. KRW Balance: {balance:,.0f}원")
            else:
                logging.info("Upbit connected (read-only mode)")
            return True
            
        except Exception as e:
            logging.error(f"Upbit connect error: {e}")
            return False
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            # interval 변환 (분 단위)
            interval_map = {
                '1': 'minute1', '5': 'minute5', '15': 'minute15',
                '30': 'minute30', '60': 'minute60', '240': 'minute240',
                '1440': 'day'
            }
            
            interval_type = interval_map.get(interval, 'minute15')
            
            if 'minute' in interval_type:
                df = pyupbit.get_ohlcv(self.symbol, interval=interval_type, count=limit)
            else:
                df = pyupbit.get_ohlcv(self.symbol, interval='day', count=limit)
            
            if df is None or len(df) == 0:
                return None
            
            # 컬럼명 통일
            df = df.reset_index()
            df = df.rename(columns={'index': 'timestamp'})
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """현재 가격"""
        try:
            return pyupbit.get_current_price(self.symbol)
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> bool:
        """시장가 주문 (현물: 매수/매도)"""
        try:
            if self.upbit is None:
                logging.error("Upbit not authenticated")
                return False
            
            price = self.get_current_price()
            
            if side == 'Long':
                # 매수: size는 KRW 금액
                order_amount = size * price  # 코인 수량 * 가격 = KRW
                result = self.upbit.buy_market_order(self.symbol, order_amount)
            else:
                # 매도: size는 코인 수량
                result = self.upbit.sell_market_order(self.symbol, size)
            
            if result and result.get('uuid'):
                order_id = str(result.get('uuid'))
                self.position = Position(
                    symbol=self.symbol,
                    side=side,
                    entry_price=price,
                    size=size,
                    stop_loss=stop_loss,  # 로컬 관리
                    initial_sl=stop_loss,
                    risk=abs(price - stop_loss),
                    be_triggered=False,
                    entry_time=datetime.now(),
                    order_id=order_id
                )
                
                logging.info(f"[Upbit] Order placed: {side} @ {price:,.0f}원 (ID: {order_id})")
                return order_id
            else:
                logging.error(f"[Upbit] Order failed: {result}")
                return False
                
        except Exception as e:
            logging.error(f"[Upbit] Order error: {e}")
            return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정 (로컬 관리 - 업비트는 SL 미지원)"""
        if self.position:
            self.position.stop_loss = new_sl
            logging.info(f"[Upbit] SL updated (local): {new_sl:,.0f}원")
            return True
        return False
    
    def close_position(self) -> bool:
        """포지션 청산 (현물: 전량 매도)"""
        try:
            if not self.position:
                return True
            
            if self.upbit is None:
                logging.error("Upbit not authenticated")
                return False
            
            # 현재 보유 수량 확인
            coin = self.symbol.split('-')[1]
            balance = self.upbit.get_balance(coin)
            
            if balance and balance > 0:
                result = self.upbit.sell_market_order(self.symbol, balance)
                
                if result and result.get('uuid'):
                    price = self.get_current_price()
                    if self.position.side == 'Long':
                        pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                    else:
                        pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                    
                    logging.info(f"[Upbit] Position closed: PnL {pnl:.2f}%")
                    self.position = None
                    return True
            
            self.position = None
            return True
            
        except Exception as e:
            logging.error(f"[Upbit] Close error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (현물: 추가 매수)"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            if self.upbit is None:
                return False
            
            price = self.get_current_price()
            
            if side == 'Long':
                order_amount = size * price
                result = self.upbit.buy_market_order(self.symbol, order_amount)
            else:
                result = self.upbit.sell_market_order(self.symbol, size)
            
            if result and result.get('uuid'):
                order_id = str(result.get('uuid'))
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                self.position.order_id = order_id
                
                logging.info(f"[Upbit] Added: {size} @ {price:,.0f}원 (ID: {order_id})")
                return order_id
            
            return False
            
        except Exception as e:
            logging.error(f"[Upbit] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """KRW 잔고 조회"""
        if self.upbit is None:
            return 0
        try:
            return float(self.upbit.get_balance("KRW") or 0)
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0

    def sync_time(self) -> bool:
        """Upbit 서버 시간 동기화 (로컬 시간 사용)"""
        # 업비트는 특별히 시간 오차에 민감한 서명 방식을 쓰지 않거나
        # pyupbit가 알아서 처리하므로 로컬 시간 사용
        self.time_offset = 0
        logging.info("[Upbit] Using local time (sync_time skipped)")
        return True
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정 (현물이라 미지원)"""
        logging.info(f"[Upbit] Spot market - leverage not supported (ignored: {leverage}x)")
        self.leverage = 1  # 현물은 항상 1배
        return True
    
    def get_coin_balance(self, coin: str = None) -> float:
        """특정 코인 잔고 조회"""
        try:
            if self.upbit is None:
                return 0
            if coin is None:
                coin = self.symbol.split('-')[1]
            return float(self.upbit.get_balance(coin) or 0)
        except Exception as e:
            logging.error(f"Coin balance error: {e}")
            return 0

    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='upbit', # lower case for handler
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            import logging
            logging.info(f"[Upbit] WebSocket connected: {{self.symbol}}")
            return True
        except Exception as e:
            import logging
            logging.error(f"[Upbit] WebSocket failed: {{e}}")
            return False
    
    def stop_websocket(self):
        """웹소켓 중지"""
        if hasattr(self, 'ws_handler') and self.ws_handler:
            self.ws_handler.disconnect()
    
    async def restart_websocket(self):
        """웹소켓 재시작"""
        self.stop_websocket()
        import asyncio
        await asyncio.sleep(1)
        return await self.start_websocket()
    
    def _auto_sync_time(self):
        """API 호출 전 자동 시간 동기화 (5분마다)"""
        import time
        if not hasattr(self, '_last_sync'):
            self._last_sync = 0
        
        if time.time() - self._last_sync > 300:
            self.sync_time()
            self._last_sync = time.time()
    
    def sync_time(self):
        """서버 시간 동기화"""
        import time
        import logging
        try:
            # ccxt 기반 거래소의 경우
            if hasattr(self, 'exchange') and hasattr(self.exchange, 'fetch_time'):
                server_time = self.exchange.fetch_time()
                local_time = int(time.time() * 1000)
                self.time_offset = local_time - server_time
                logging.debug(f"[Upbit] Time synced: offset={{self.time_offset}}ms")
                return True
        except Exception as e:
            logging.debug(f"[Upbit] Time sync failed: {{e}}")
        self.time_offset = 0
        return False
    
    def fetchTime(self):
        """서버 시간 조회"""
        import time
        try:
            if hasattr(self, 'exchange') and hasattr(self.exchange, 'fetch_time'):
                return self.exchange.fetch_time()
        except Exception as e:
            logging.debug(f"WS close ignored: {e}")
        return int(time.time() * 1000)

