# exchanges/bingx_exchange.py
"""
BingX 거래소 어댑터
- Perpetual (영구 선물) 거래 지원
- API: ccxt (공식 SDK 없음)
- 심볼 형식: BTC-USDT
- 특이사항: recvWindow 설정 필요
"""

import time
import logging
import pandas as pd
from typing import Any, cast
from datetime import datetime
from typing import Optional, Any, Dict, Union

from .base_exchange import BaseExchange, Position

try:
    import ccxt
except ImportError:
    ccxt = None


class BingXExchange(BaseExchange):
    """BingX 거래소 어댑터"""
    
    @property
    def name(self) -> str:
        return "BingX"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.testnet = config.get('testnet', False)
        self.exchange: Optional[Any] = None  # ccxt.Exchange type
        self.time_offset = 0
        self.hedge_mode = False
        
        # [FIX] BingX 심볼 형식 정규화 - 내부 저장은 BTCUSDT, _convert_symbol에서 BTC/USDT:USDT로 변환
        self.symbol = self.symbol.replace('/', '').replace('-', '').replace(':USDT', '').upper()

    
    def connect(self) -> bool:
        """API 연결"""
        if ccxt is None:
            logging.error("ccxt not installed!")
            return False
        
        try:
            self.exchange = ccxt.bingx({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                    'recvWindow': 60000,
                    'adjustForTimeDifference': True,
                }
            })
            
            # 시간 동기화
            self.sync_time()
            
            self.exchange.load_markets()
            
            logging.info(f"BingX connected. Time offset: {self.time_offset}ms")
            return True
            
        except Exception as e:
            logging.error(f"BingX connect error: {e}")
            return False
    
    def _convert_symbol(self, symbol: str) -> str:
        """심볼 변환 (BTCUSDT -> BTC/USDT:USDT)"""
        base = symbol.replace('USDT', '')
        return f"{base}/USDT:USDT"
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return None
        try:
            tf_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h'}
            timeframe = tf_map.get(interval, interval)
            
            symbol = self._convert_symbol(self.symbol)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=cast(Any, ['timestamp', 'open', 'high', 'low', 'close', 'volume']))
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """현재 가격"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return 0.0
        try:
            symbol = self._convert_symbol(self.symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker.get('last', 0) or 0)
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0.0
    
    def place_market_order(self, side: str, size: float, stop_loss: float, take_profit: float = 0, client_order_id: Optional[str] = None) -> Union[bool, dict]:
        """시장가 주문"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return False
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                symbol = self._convert_symbol(self.symbol)
                order_side = 'buy' if side == 'Long' else 'sell'
                
                params: Dict[str, Any] = {'recvWindow': 60000}
                
                # [NEW] Hedge Mode Check (BingX usually One-Way, but if Hedge enabled:)
                # BingX Standard Params for Hedge: positionSide=LONG/SHORT
                if self.hedge_mode:
                     params['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=order_side,
                    amount=size,
                    params=params
                )
                
                if order:
                    price = self.get_current_price()
                    
                    # SL 설정
                    if stop_loss > 0:
                        try:
                            sl_side = 'sell' if side == 'Long' else 'buy'
                            sl_params: Dict[str, Any] = {
                                'stopPrice': stop_loss,
                                'reduceOnly': True
                            }
                            # [FIX] Hedge Mode Support (BingX using positionSide)
                            if self.hedge_mode:
                                sl_params['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'

                            self.exchange.create_order(
                                symbol=symbol,
                                type='stop_market',
                                side=sl_side,
                                amount=size,
                                params=sl_params
                            )
                        except Exception as sl_err:
                            # 🔴 CRITICAL: SL 실패 시 즉시 청산
                            logging.error(f"[BingX] ❌ SL Setting FAILED! Closing position immediately: {sl_err}")
                            try:
                                close_params: Dict[str, Any] = {'reduceOnly': True}
                                if self.hedge_mode:
                                    close_params['positionSide'] = 'LONG' if side == 'Long' else 'SHORT'
                                self.exchange.create_order(
                                    symbol=symbol,
                                    type='market',
                                    side=sl_side,
                                    amount=size,
                                    params=close_params
                                )
                                logging.warning("[BingX] ⚠️ Emergency Close Done.")
                            except Exception as close_err:
                                logging.critical(f"[BingX] 🚨 EMERGENCY CLOSE FAILED! CHECK BINGX APP: {close_err}")
                            return False

                    
                    self.position = Position(
                        symbol=self.symbol,
                        side=side,
                        entry_price=price,
                        size=size,
                        stop_loss=stop_loss,
                        initial_sl=stop_loss,
                        risk=abs(price - stop_loss),
                        be_triggered=False,
                        entry_time=datetime.now()
                    )
                    
                    logging.info(f"[BingX] Order placed: {side} {size} @ {price}")
                    return True
                    
            except Exception as e:
                logging.error(f"[BingX] Order error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return False
        try:
            symbol = self._convert_symbol(self.symbol)
            
            # 기존 스탑 주문 취소
            try:
                if self.exchange:
                    orders = self.exchange.fetch_open_orders(symbol)
                    for order in orders:
                        if isinstance(order, dict) and order.get('type') in ['stop_market', 'stop']:
                            oid = order.get('id')
                            if oid:
                                self.exchange.cancel_order(oid, symbol)
            except Exception as e:
                logging.debug(f'무시된 예외: {e}')
            
            # 새 스탑 주문
            if self.position:
                if self.exchange is None:
                    return False
                sl_side = 'sell' if self.position.side == 'Long' else 'buy'
                params: Dict[str, Any] = {
                    'stopPrice': new_sl,
                    'reduceOnly': True
                }
                # [FIX] Hedge Mode Support (BingX using positionSide)
                if self.hedge_mode:
                    params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'
                
                self.exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=sl_side,
                    amount=self.position.size,
                    params=params
                )
                self.position.stop_loss = new_sl
                logging.info(f"[BingX] SL updated: {new_sl}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[BingX] SL update error: {e}")
            return False
    
    def close_position(self) -> bool:
        """포지션 청산"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return False
        try:
            if not self.position:
                return True
            
            symbol = self._convert_symbol(self.symbol)
            close_side = 'sell' if self.position.side == 'Long' else 'buy'
            
            params: Dict[str, Any] = {'reduceOnly': True}
            # [FIX] Hedge Mode Support (BingX using positionSide)
            if self.hedge_mode:
                params['positionSide'] = 'LONG' if self.position.side == 'Long' else 'SHORT'

            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=self.position.size,
                params=params
            )
            
            if order:
                price = self.get_current_price()
                if self.position.side == 'Long':
                    pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                else:
                    pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                
                profit_usd = self.capital * self.leverage * (pnl / 100)
                self.capital += profit_usd
                
                logging.info(f"[BingX] Position closed: PnL {pnl:.2f}%")
                self.position = None
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[BingX] Close error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return False
        try:
            if not self.position or side != self.position.side:
                return False
            
            symbol = self._convert_symbol(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=size
            )
            
            if order:
                price = self.get_current_price()
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[BingX] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[BingX] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회 (Perpetual 선물 계정)"""
        if self.exchange is None:
            return 0
        try:
            from utils.helpers import safe_float
            # [FIX] 무기한 선물(Perpetual) 계정 지갑 명시적 조회
            balance = self.exchange.fetch_balance(params={'type': 'swap'})
            return safe_float(balance.get('USDT', {}).get('free', 0))
        except Exception as e:
            logging.error(f"[BingX] Balance error: {e}")
            return 0

    def sync_time(self) -> bool:
        """BingX 서버 시간 동기화"""
        if self.exchange is None:
            return False
        try:
            server_time = self.exchange.fetch_time()
            if server_time is None:
                logging.error("[BingX] Failed to fetch server time")
                return False
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time
            logging.info(f"[BingX] Time synced. Offset: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"[BingX] sync_time error: {e}")
            return False

    def get_positions(self) -> list:
        """모든 열린 포지션 조회 (긴급청산용)"""
        if self.exchange is None:
            return []
        try:
            if self.exchange is None:
                return []
            positions_data = self.exchange.fetch_positions()
            
            positions = []
            for pos in positions_data:
                size = abs(float(pos.get('contracts', 0)))
                if size > 0:
                    positions.append({
                        'symbol': pos.get('symbol', '').replace('/USDT:USDT', 'USDT'),
                        'side': 'Buy' if pos.get('side') == 'long' else 'Sell',
                        'size': size,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'leverage': int(pos.get('leverage', 1))
                    })
            
            logging.info(f"[BingX] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return []
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return False
        try:
            symbol = self._convert_symbol(self.symbol)
            self.exchange.set_leverage(leverage, symbol)
            self.leverage = leverage
            logging.info(f"[BingX] Leverage set to {leverage}x")
            return True
        except Exception as e:
            if "leverage not modified" in str(e).lower():
                self.leverage = leverage
                return True
            logging.error(f"[BingX] Leverage error: {e}")
            return False

# Alias for compatibility

    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='bingx', 
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            if self.ws_handler:
                asyncio.create_task(self.ws_handler.connect())
            
            logging.info(f"[BingX] WebSocket connected: {self.symbol}")
            return True
        except Exception as e:
            logging.error(f"[BingX] WebSocket failed: {e}")
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
        if not hasattr(self, '_last_sync'):
            self._last_sync = 0

        if time.time() - self._last_sync > 300:
            self.sync_time()
            self._last_sync = time.time()

    def fetchTime(self) -> int:
        """서버 시간 조회"""
        try:
            if self.exchange and hasattr(self.exchange, 'fetch_time'):
                if self.exchange is None: return int(time.time() * 1000)
                result = self.exchange.fetch_time()
                if result is not None:
                    return int(result)
        except Exception:
            pass
        return int(time.time() * 1000)

    # ========== [NEW] 매매 히스토리 API ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회 (CCXT)"""
        if self.exchange is None:
            logging.error("Exchange not connected")
            return []
        try:
            if self.exchange is None:
                return super().get_trade_history(limit)
            
            symbol = self._convert_symbol(self.symbol)
            raw_trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            
            trades = []
            for t in raw_trades:
                trade_dict: Dict[str, Any] = t if isinstance(t, dict) else {}
                trades.append({
                    'symbol': self.symbol,
                    'side': str(trade_dict.get('side', '')).upper(),
                    'qty': float(trade_dict.get('amount', 0)),
                    'entry_price': float(trade_dict.get('price', 0)),
                    'exit_price': float(trade_dict.get('price', 0)),
                    'pnl': float(trade_dict.get('info', {}).get('realizedPnl', 0) if isinstance(trade_dict.get('info'), dict) else 0),
                    'created_time': str(trade_dict.get('timestamp', '')),
                    'updated_time': str(trade_dict.get('timestamp', ''))
                })
            
            logging.info(f"[BingX] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.error(f"[BingX] Trade history error: {e}")
            return []

    def get_realized_pnl(self, limit: int = 100) -> float:
        """API로 실현 손익 조회"""
        try:
            trades = self.get_trade_history(limit=limit)
            total_pnl = float(sum(t.get('pnl', 0) for t in trades))
            logging.info(f"[BingX] Realized PnL: ${total_pnl:.2f} from {len(trades)} trades")
            return total_pnl
        except Exception as e:
            logging.error(f"[BingX] get_realized_pnl error: {e}")
            return 0.0

    def get_compounded_capital(self, initial_capital: float) -> float:
        """복리 자본 조회 (초기 자본 + 누적 수익)"""
        realized_pnl = self.get_realized_pnl()
        compounded = initial_capital + realized_pnl
        # 최소 자본 보장 (초기의 10%)
        min_capital = initial_capital * 0.1
        return max(compounded, min_capital)


BingxExchange = BingXExchange
