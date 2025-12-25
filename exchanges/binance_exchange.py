# exchanges/binance_exchange.py
"""
Binance 거래소 어댑터
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

from .base_exchange import BaseExchange, Position

try:
    from binance.client import Client
    from binance.enums import *
except ImportError:
    Client = None

from storage.secure_storage import get_secure_storage


class BinanceExchange(BaseExchange):
    """Binance 거래소 어댑터"""
    
    @property
    def name(self) -> str:
        return "Binance"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.testnet = config.get('testnet', False)
        self.client = None
        self.authenticated = False
    
    def connect(self) -> bool:
        """API 연결 (SecureStorage 연동)"""
        if Client is None:
            logging.error("python-binance not installed!")
            return False
            
        try:
            storage = get_secure_storage()
            keys = storage.get_exchange_keys('binance')
            
            if keys and keys.get('api_key') and keys.get('api_secret'):
                # [FIX] 시간 동기화 및 타임아웃 설정
                client_params = {
                    'api_key': keys['api_key'],
                    'api_secret': keys['api_secret'],
                    'requests_params': {'timeout': 30},
                    'adjust_for_session_time_difference': True
                }
                
                if self.testnet:
                    client_params['testnet'] = True
                
                self.client = Client(**client_params)
                    
                self.sync_time()
                
                self.client.futures_ping()
                account = self.client.futures_account()
                balance = account.get('totalWalletBalance', 0)
                self.authenticated = True
                logging.info(f"[Binance] 인증 연결 성공. 잔고: {balance} USDT")
            else:
                self.client = Client()
                self.authenticated = False
                logging.info("[Binance] 시세 조회 전용 모드")
                
            return True
            
        except Exception as e:
            logging.error(f"[Binance] 연결 실패: {e}")
            return False
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            # Binance interval 변환
            interval_map = {
                '1': '1m', '3': '3m', '5': '5m', '15': '15m', 
                '30': '30m', '60': '1h', '240': '4h', '1440': '1d'
            }
            binance_interval = interval_map.get(interval, interval)
            
            klines = self.client.futures_klines(
                symbol=self.symbol,
                interval=binance_interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """현재 가격"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            return float(ticker['price'])
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0
    
    def place_market_order(self, side: str, size: float, stop_loss: float = None) -> bool:
        """시장가 주문 실행 + SL 실패 시 즉시 청산"""
        if not self.authenticated:
            logging.error("[Binance] Not authenticated - cannot place orders")
            return False
        
        try:
            # 주문 방향 설정 (상수 대신 문자열 사용으로 의존성 및 에러 최소화)
            order_side = 'BUY' if side == 'Long' else 'SELL'
            sl_side = 'SELL' if side == 'Long' else 'BUY'
            
            # 수량 처리 (간단히 소수점 3자리)
            qty = round(size, 3)
            current_price = self.get_current_price()
            
            logging.info(f"[Binance] Placing {order_side} {qty} {self.symbol} @ {current_price} (SL: {stop_loss})")
            
            # 1. 메인 주문 실행
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=order_side,
                type='MARKET',
                quantity=qty
            )
            
            if not order:
                logging.error("[Binance] Main order failed (no response)")
                return False
            
            order_id = order.get('orderId')
            logging.info(f"[Binance] Main Order Success: {order_id}")
            
            # 2. SL 주문 설정
            if stop_loss and stop_loss > 0:
                try:
                    sl_order = self.client.futures_create_order(
                        symbol=self.symbol,
                        side=sl_side,
                        type='STOP_MARKET',
                        stopPrice=round(stop_loss, 2),
                        closePosition='true'  # reduceOnly와 유사하지만 포지션 전체 청산
                    )
                    logging.info(f"[Binance] SL Order Set: {stop_loss}")
                    
                except Exception as sl_error:
                    # 🔴 CRITICAL: SL 실패 시 즉시 청산
                    logging.error(f"[Binance] ❌ SL Setting FAILED! Closing position immediately: {sl_error}")
                    
                    try:
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side=sl_side,
                            type='MARKET',
                            quantity=qty,
                            reduceOnly='true'
                        )
                        logging.warning(f"[Binance] ⚠️ Emregency Close Done.")
                    except Exception as close_error:
                        logging.critical(f"[Binance] 🚨 EMERGENCY CLOSE FAILED! CHECK BINANCE APP: {close_error}")
                    
                    return False

            # 3. Position 객체 업데이트 (GUI 표시용)
            self.position = Position(
                symbol=self.symbol,
                side=side,
                entry_price=current_price,
                size=qty,
                stop_loss=stop_loss if stop_loss else 0,
                initial_sl=stop_loss if stop_loss else 0,
                risk=abs(current_price - stop_loss) if stop_loss else 0,
                be_triggered=False,
                entry_time=datetime.now()
            )
            
            return True
            
        except Exception as e:
            logging.error(f"[Binance] Order execution error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        try:
            # 기존 스탑 주문 취소
            self.client.futures_cancel_all_open_orders(symbol=self.symbol)
            
            # 새 스탑 주문 생성
            sl_side = SIDE_SELL if self.position.side == 'Long' else SIDE_BUY
            sl_order = self.client.futures_create_order(
                symbol=self.symbol,
                side=sl_side,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                stopPrice=round(new_sl, 2),
                closePosition='true'
            )
            
            if sl_order:
                self.position.stop_loss = new_sl
                logging.info(f"SL updated: {new_sl}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"SL update error: {e}")
            return False
    
    def close_position(self) -> bool:
        """포지션 청산"""
        try:
            if not self.position:
                return True
            
            side = SIDE_SELL if self.position.side == 'Long' else SIDE_BUY
            
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=self.position.size,
                reduceOnly='true'
            )
            
            if order:
                price = self.get_current_price()
                if self.position.side == 'Long':
                    pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                else:
                    pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                
                profit_usd = self.capital * self.leverage * (pnl / 100)
                self.capital += profit_usd
                
                logging.info(f"Position closed: PnL {pnl:.2f}% (${profit_usd:.2f})")
                self.position = None
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Close error: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회"""
        if self.client is None:
            return 0
        try:
            account = self.client.futures_account()
            return float(account.get('totalWalletBalance', 0))
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0

    def sync_time(self) -> bool:
        """Binance 서버 시간 동기화"""
        if self.client is None:
            return False
        try:
            # adjust_for_session_time_difference=True가 설정되어 있어도
            # 명시적으로 시간을 맞추고 싶을 때 사용
            server_time = self.client.get_server_time()
            server_ts = server_time['serverTime']
            local_ts = int(time.time() * 1000)
            self.time_offset = server_ts - local_ts
            logging.info(f"[Binance] Time synced. Offset: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"[Binance] sync_time error: {e}")
            return False
    
    def get_positions(self) -> list:
        """모든 열린 포지션 조회 (긴급청산용)"""
        try:
            positions_data = self.client.futures_position_information()
            
            positions = []
            for pos in positions_data:
                size = abs(float(pos.get('positionAmt', 0)))
                if size > 0:
                    positions.append({
                        'symbol': pos.get('symbol'),
                        'side': 'Buy' if float(pos.get('positionAmt', 0)) > 0 else 'Sell',
                        'size': size,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'unrealized_pnl': float(pos.get('unRealizedProfit', 0)),
                        'leverage': int(pos.get('leverage', 1))
                    })
            
            logging.info(f"[Binance] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return []
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            self.client.futures_change_leverage(
                symbol=self.symbol,
                leverage=leverage
            )
            self.leverage = leverage
            logging.info(f"[Binance] Leverage set to {leverage}x")
            return True
        except Exception as e:
            logging.error(f"[Binance] Leverage error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (물타기)"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            price = self.get_current_price()
            qty = round(size, 3)
            
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=SIDE_BUY if side == 'Long' else SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=qty
            )
            
            if order:
                total_size = self.position.size + qty
                avg_price = (self.position.entry_price * self.position.size + price * qty) / total_size
                self.position.size = total_size
                self.position.entry_price = avg_price
                logging.info(f"[Binance] Added: {qty} @ {price}, Avg: {avg_price:.2f}")
                return True
            return False
        except Exception as e:
            logging.error(f"[Binance] Add position error: {e}")
            return False

    # ============================================
    # WebSocket 연동 (Phase 2)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """Binance 웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='binance',
                symbol=self.symbol,
                interval=interval
            )
            
            # 콜백 등록
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            # 연결 (비동기 태스크로 실행)
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            import logging
            logging.info(f"[Binance] WebSocket started: {self.symbol} {interval}")
            return True
            
        except Exception as e:
            import logging
            logging.error(f"[Binance] WebSocket failed: {e}")
            return False
    
    def stop_websocket(self):
        """웹소켓 중지"""
        if hasattr(self, 'ws_handler') and self.ws_handler:
            self.ws_handler.disconnect()
            for task in asyncio.all_tasks():
                if 'connect' in str(task):
                    task.cancel()
            import logging
            logging.info("[Binance] WebSocket stopped")
    
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
            
    def fetchTime(self):
        """서버 시간 조회 (통일된 인터페이스)"""
        import time
        try:
            if self.client:
                server_time = self.client.get_server_time()
                return server_time['serverTime']
        except Exception:
            pass
        return int(time.time() * 1000)
