# exchanges/okx_exchange.py
"""
OKX 거래소 어댑터
- Swap (영구 선물) 거래 지원
- API: ccxt
- 심볼 형식: BTC-USDT-SWAP
- 특이사항: passphrase 필요
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Optional

from .base_exchange import BaseExchange, Position

try:
    import ccxt
except ImportError:
    ccxt = None


class OKXExchange(BaseExchange):
    """OKX 거래소 어댑터"""
    
    @property
    def name(self) -> str:
        return "OKX"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.passphrase = config.get('passphrase', '')
        self.testnet = config.get('testnet', False)
        self.exchange = None
        self.time_offset = 0
        
        # [FIX] OKX 심볼 형식 정규화 - 내부 저장은 BTCUSDT, _convert_symbol에서 BTC/USDT:USDT로 변환
        self.symbol = self.symbol.replace('/', '').replace('-', '').replace(':USDT', '').upper()

    
    def connect(self) -> bool:
        """API 연결"""
        if ccxt is None:
            logging.error("ccxt not installed!")
            return False
        
        try:
            self.exchange = ccxt.okx({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'password': self.passphrase,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                    'recvWindow': 60000,
                }
            })
            
            if self.testnet:
                self.exchange.set_sandbox_mode(True)
            
            # 시간 동기화
            self.sync_time()
            
            self.exchange.load_markets()
            
            logging.info(f"OKX connected. Time offset: {self.time_offset}ms")
            return True
            
        except Exception as e:
            logging.error(f"OKX connect error: {e}")
            return False
    
    def _convert_symbol(self, symbol: str) -> str:
        """심볼 변환 (BTCUSDT -> BTC/USDT:USDT)"""
        base = symbol.replace('USDT', '')
        return f"{base}/USDT:USDT"
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            tf_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1H', '240': '4H'}
            timeframe = tf_map.get(interval, interval)
            
            symbol = self._convert_symbol(self.symbol)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def get_current_price(self) -> float:
        """현재 가격"""
        try:
            symbol = self._convert_symbol(self.symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> bool:
        """시장가 주문"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                symbol = self._convert_symbol(self.symbol)
                order_side = 'buy' if side == 'Long' else 'sell'
                
                # OKX는 posSide 필요 (User Script check: positionSide)
                pos_side = 'long' if side == 'Long' else 'short'
                
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=order_side,
                    amount=size,
                    params={
                        'posSide': pos_side,
                        'tdMode': 'cross'
                    }
                )
                
                if order:
                    price = self.get_current_price()
                    
                    if stop_loss > 0:
                        try:
                            sl_side = 'sell' if side == 'Long' else 'buy'
                            self.exchange.create_order(
                                symbol=symbol,
                                type='stop_market',
                            side=sl_side,
                            amount=size,
                            params={
                                'stopPrice': stop_loss,
                                'posSide': pos_side,
                                'reduceOnly': True
                            }
                        )
                        except Exception as sl_err:
                            # 🔴 CRITICAL: SL 실패 시 즉시 청산
                            logging.error(f"[OKX] ❌ SL Setting FAILED! Closing position immediately: {sl_err}")
                            try:
                                self.exchange.create_order(
                                    symbol=symbol,
                                    type='market',
                                    side=sl_side,
                                    amount=size,
                                    params={'posSide': pos_side, 'reduceOnly': True}
                                )
                                logging.warning("[OKX] ⚠️ Emergency Close Done.")
                            except Exception as close_err:
                                logging.critical(f"[OKX] 🚨 EMERGENCY CLOSE FAILED! CHECK OKX APP: {close_err}")
                            return False

                    
                    order_id = str(order.get('id', ''))
                    self.position = Position(
                        symbol=self.symbol,
                        side=side,
                        entry_price=price,
                        size=size,
                        stop_loss=stop_loss,
                        initial_sl=stop_loss,
                        risk=abs(price - stop_loss),
                        be_triggered=False,
                        entry_time=datetime.now(),
                        order_id=order_id
                    )
                    
                    logging.info(f"[OKX] Order placed: {side} {size} @ {price} (ID: {order_id})")
                    return order_id
                    
            except Exception as e:
                logging.error(f"[OKX] Order error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        try:
            symbol = self._convert_symbol(self.symbol)
            
            # 기존 스탑 주문 취소
            try:
                orders = self.exchange.fetch_open_orders(symbol)
                for order in orders:
                    if order.get('type') in ['stop_market', 'stop']:
                        if isinstance(order, dict) and order.get('id'):
                            self.exchange.cancel_order(order['id'], symbol)
            except Exception as e:
                logging.debug(f"Order cancel ignored: {e}")
            
            # 새 스탑 주문
            if self.position:
                sl_side = 'sell' if self.position.side == 'Long' else 'buy'
                pos_side = 'long' if self.position.side == 'Long' else 'short'
                
                self.exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=sl_side,
                    amount=self.position.size,
                    params={
                        'stopPrice': new_sl,
                        'posSide': pos_side,
                        'reduceOnly': True
                    }
                )
                self.position.stop_loss = new_sl
                logging.info(f"[OKX] SL updated: {new_sl}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OKX] SL update error: {e}")
            return False
    
    def close_position(self) -> bool:
        """포지션 청산"""
        try:
            if not self.position:
                return True
            
            symbol = self._convert_symbol(self.symbol)
            close_side = 'sell' if self.position.side == 'Long' else 'buy'
            pos_side = 'long' if self.position.side == 'Long' else 'short'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=self.position.size,
                params={
                    'posSide': pos_side,
                    'reduceOnly': True
                }
            )
            
            if order:
                price = self.get_current_price()
                if self.position.side == 'Long':
                    pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                else:
                    pnl = (self.position.entry_price - price) / self.position.entry_price * 100
                
                profit_usd = self.capital * self.leverage * (pnl / 100)
                self.capital += profit_usd
                
                logging.info(f"[OKX] Position closed: PnL {pnl:.2f}%")
                self.position = None
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OKX] Close error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            symbol = self._convert_symbol(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            pos_side = 'long' if side == 'Long' else 'short'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=size,
                params={
                    'posSide': pos_side,
                    'tdMode': 'cross'
                }
            )
            
            if order:
                price = self.get_current_price()
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                
                logging.info(f"[OKX] Added: {size} @ {price}, Avg: {avg_price:.2f}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"[OKX] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """잔고 조회"""
        if self.exchange is None:
            return 0
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get('USDT', {}).get('free', 0))
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0

    def sync_time(self) -> bool:
        """OKX 서버 시간 동기화"""
        if self.exchange is None:
            return False
        try:
            server_time = self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time
            logging.info(f"[OKX] Time synced. Offset: {self.time_offset}ms")
            return True
        except Exception as e:
            logging.error(f"[OKX] sync_time error: {e}")
            return False
    
    def get_positions(self) -> list:
        """모든 열린 포지션 조회 (긴급청산용)"""
        try:
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
            
            logging.info(f"[OKX] 열린 포지션: {len(positions)}개")
            return positions
            
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return []
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정"""
        try:
            symbol = self._convert_symbol(self.symbol)
            
            # OKX는 long/short 각각 설정
            self.exchange.set_leverage(leverage, symbol, params={'mgnMode': 'cross', 'posSide': 'long'})
            self.exchange.set_leverage(leverage, symbol, params={'mgnMode': 'cross', 'posSide': 'short'})
            
            self.leverage = leverage
            logging.info(f"[OKX] Leverage set to {leverage}x")
            return True
        except Exception as e:
            if "leverage not modified" in str(e).lower():
                self.leverage = leverage
                return True
            logging.error(f"[OKX] Leverage error: {e}")
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
                exchange='okx', 
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            import logging
            logging.info(f"[Okx] WebSocket connected: {{self.symbol}}")
            return True
        except Exception as e:
            import logging
            logging.error(f"[Okx] WebSocket failed: {{e}}")
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
                logging.debug(f"[Okx] Time synced: offset={{self.time_offset}}ms")
                return True
        except Exception as e:
            logging.debug(f"[Okx] Time sync failed: {{e}}")
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

    # ========== [NEW] 매매 히스토리 API ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """API로 청산된 거래 히스토리 조회 (CCXT)"""
        try:
            if not self.exchange:
                return super().get_trade_history(limit)
            
            symbol = self._convert_symbol(self.symbol)
            raw_trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            
            trades = []
            for t in raw_trades:
                trades.append({
                    'symbol': self.symbol,
                    'side': t.get('side', '').upper(),
                    'qty': float(t.get('amount', 0)),
                    'entry_price': float(t.get('price', 0)),
                    'exit_price': float(t.get('price', 0)),
                    'pnl': float(t.get('info', {}).get('realizedPnl', 0)),
                    'created_time': str(t.get('timestamp', '')),
                    'updated_time': str(t.get('timestamp', ''))
                })
            
            logging.info(f"[OKX] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.warning(f"[OKX] Trade history error: {e}")
            return super().get_trade_history(limit)


OkxExchange = OKXExchange
