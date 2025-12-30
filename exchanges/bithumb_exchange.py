# exchanges/bithumb_exchange.py
"""
빗썸 거래소 어댑터 (현물 전용)
- 현물 거래만 지원 (선물 없음)
- API: pybithumb 또는 ccxt
- 심볼 형식: BTC_KRW
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
    from utils.helpers import safe_float
except ImportError:
    def safe_float(value, default=0.0):
        if value is None:
            return default
        if isinstance(value, dict):
            return float(value.get('free', value.get('total', value.get('available', default))))
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

try:
    import pybithumb
except ImportError:
    pybithumb = None

try:
    import ccxt
except ImportError:
    ccxt = None


class BithumbExchange(BaseExchange):
    """빗썸 거래소 어댑터 (현물 전용)"""
    
    @property

    def fetchTime(self):
        """Bithumb는 시간 API 미지원 - 로컬 시간 반환"""
        import time
        return int(time.time() * 1000)

    def name(self) -> str:
        return "Bithumb"
    
    def sync_time(self) -> bool:
        """Bithumb은 fetchTime 미지원 → 스킵 (로컬 시간 사용)"""
        self.time_offset = 0
        logging.info("[TIME] Bithumb: using local time (fetchTime not supported)")
        return True

    def get_server_time(self) -> int:
        """로컬 시간 반환 (ms)"""
        import time
        return int(time.time() * 1000)
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # [NEW] 통화 통합 시스템 - 현물/KRW 거래소
        self.quote_currency = 'KRW'
        self.market_type = 'spot'
        
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.bithumb = None
        self.use_ccxt = False
        
        # 심볼 변환 (BTCUSDT -> BTC)
        raw_symbol = config.get('symbol', 'BTCUSDT')
        self.symbol = self._normalize_symbol(raw_symbol)
        self.coin = self.symbol  # 코인 심볼 (BTC, ETH 등)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """심볼 정규화 (BTCUSDT -> BTC)"""
        return symbol.replace('USDT', '').replace('USD', '').replace('KRW', '').replace('_', '').replace('-', '')
    
    def connect(self) -> bool:
        """API 연결"""
        # pybithumb 우선, 없으면 ccxt 사용
        if pybithumb is not None:
            return self._connect_pybithumb()
        elif ccxt is not None:
            return self._connect_ccxt()
        else:
            logging.error("pybithumb or ccxt not installed!")
            return False
    
    def _connect_pybithumb(self) -> bool:
        """pybithumb로 연결"""
        try:
            if self.api_key and self.api_secret:
                self.bithumb = pybithumb.Bithumb(self.api_key, self.api_secret)
                balance = self.get_balance()
                logging.info(f"Bithumb connected (pybithumb). KRW Balance: {balance:,.0f}원")
            else:
                logging.info("Bithumb connected (read-only mode)")
            return True
            
        except Exception as e:
            logging.error(f"Bithumb connect error: {e}")
            return False
    
    def _connect_ccxt(self) -> bool:
        """ccxt로 연결"""
        try:
            self.bithumb = ccxt.bithumb({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
            })
            self.use_ccxt = True
            self.bithumb.load_markets()
            logging.info("Bithumb connected (ccxt)")
            return True
            
        except Exception as e:
            logging.error(f"Bithumb ccxt connect error: {e}")
            return False
    
    def get_klines(self, symbol=None, interval: str = '15m', limit: int = 500) -> list:
        """
        빗썸 캔들 데이터 조회
        - 업비트 데이터를 마스터로 사용
        - 빗썸 API는 실시간 보조용 (최대 3000개)
        """
        try:
            # 1) 먼저 업비트에서 가져오기 시도
            upbit_symbol = self._convert_to_upbit_symbol(symbol)
            
            if upbit_symbol:
                try:
                    import pyupbit
                    
                    interval_map = {
                        '1m': 'minute1', '3m': 'minute3', '5m': 'minute5',
                        '15m': 'minute15', '30m': 'minute30',
                        '60m': 'minute60', '1h': 'minute60',
                        '240m': 'minute240', '4h': 'minute240',
                        'day': 'day', '1d': 'day'
                    }
                    interval_str = interval_map.get(interval, 'minute15')
                    
                    all_candles = []
                    remaining = limit
                    to = None
                    
                    while remaining > 0:
                        count = min(remaining, 200)
                        df = pyupbit.get_ohlcv(upbit_symbol, interval=interval_str, count=count, to=to)
                        
                        if df is None or df.empty:
                            break
                        
                        for idx, row in df.iterrows():
                            all_candles.append({
                                'timestamp': int(idx.timestamp() * 1000),
                                'open': float(row['open']),
                                'high': float(row['high']),
                                'low': float(row['low']),
                                'close': float(row['close']),
                                'volume': float(row['volume'])
                            })
                        
                        to = df.index[0]
                        remaining -= len(df)
                        
                        if len(df) < count:
                            break
                    
                    all_candles.sort(key=lambda x: x['timestamp'])
                    logging.info(f"[Bithumb] Loaded {len(all_candles)} candles from Upbit (master)")
                    return all_candles
                    
                except Exception as e:
                    logging.warning(f"[Bithumb] Upbit fallback failed: {e}, using native API")
            
            # 2) 업비트 실패 시 빗썸 자체 API (최대 3000개)
            return self._get_klines_native(symbol, interval, min(limit, 3000))
            
        except Exception as e:
            logging.error(f"[Bithumb] get_klines error: {e}")
            return []

    def _convert_to_upbit_symbol(self, symbol):
        """빗썸 심볼 → 업비트 심볼 변환"""
        # BTC_KRW → KRW-BTC
        if symbol is None:
            symbol = self.symbol
        
        if '_KRW' in symbol:
            base = symbol.replace('_KRW', '')
            return f'KRW-{base}'
        elif '_' in symbol:
            base = symbol.split('_')[0]
            return f'KRW-{base}'
        else:
            # If it's just 'BTC'
            return f'KRW-{symbol}'

    def _get_klines_native(self, symbol, interval, limit):
        """빗썸 자체 API (백업용, 최대 3000개)"""
        try:
            import requests
            symbol = symbol or self.symbol
            
            # interval conversion for bithumb API
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
                '60m': '1h', '1h': '1h', '240m': '4h', '4h': '4h', 'day': '24h', '1d': '24h'
            }
            bithumb_interval = interval_map.get(interval, '15m')
            
            # Convert symbol to Bithumb format if needed (e.g. BTC_KRW)
            if '-' in symbol:
                symbol = symbol.replace('KRW-', '') + '_KRW'
            elif '_' not in symbol:
                symbol = f"{symbol}_KRW"

            url = f'https://api.bithumb.com/public/candlestick/{symbol}/{bithumb_interval}'
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('status') != '0000':
                return []
            
            candles = data.get('data', [])[-limit:]
            
            result = []
            for c in candles:
                result.append({
                    'timestamp': int(c[0]),
                    'open': float(c[1]),
                    'close': float(c[2]),
                    'high': float(c[3]),
                    'low': float(c[4]),
                    'volume': float(c[5])
                })
            
            logging.info(f"[Bithumb] Loaded {len(result)} candles (native, max 3000)")
            return result
            
        except Exception as e:
            logging.error(f"[Bithumb] native API error: {e}")
            return []
    
    def _get_klines_pybithumb(self, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """pybithumb로 캔들 조회"""
        interval_map = {
            '1': '1m', '5': '5m', '15': '15m', '30': '30m',
            '60': '1h', '240': '4h', '1440': '24h'
        }
        chart_interval = interval_map.get(interval, '1h')
        
        df = pybithumb.get_candlestick(self.coin, chart_intervals=chart_interval)
        
        if df is None or len(df) == 0:
            return None
        
        df = df.reset_index()
        df = df.rename(columns={'time': 'timestamp'})
        # df = df.tail(limit)  # [REMOVED] 전체 데이터 반환
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    def _get_klines_ccxt(self, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """ccxt로 캔들 조회"""
        tf_map = {'1': '1m', '5': '5m', '15': '15m', '60': '1h', '240': '4h'}
        timeframe = tf_map.get(interval, '1h')
        
        symbol = f"{self.coin}/KRW"
        ohlcv = self.bithumb.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    
    def get_current_price(self) -> float:
        """현재 가격"""
        try:
            if self.use_ccxt:
                symbol = f"{self.coin}/KRW"
                ticker = self.bithumb.fetch_ticker(symbol)
                return float(ticker['last'])
            else:
                return pybithumb.get_current_price(self.coin)
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> bool:
        """시장가 주문"""
        try:
            if self.bithumb is None:
                logging.error("Bithumb not authenticated")
                return False
            
            price = self.get_current_price()
            
            if self.use_ccxt:
                return self._place_order_ccxt(side, size, stop_loss, price)
            else:
                return self._place_order_pybithumb(side, size, stop_loss, price)
                
        except Exception as e:
            logging.error(f"[Bithumb] Order error: {e}")
            return False
    
    def _place_order_pybithumb(self, side: str, size: float, stop_loss: float, price: float) -> bool:
        """pybithumb로 주문"""
        if side == 'Long':
            result = self.bithumb.buy_market_order(self.coin, size)
        else:
            result = self.bithumb.sell_market_order(self.coin, size)
        
        if result and result[0] == 'success':
            order_id = str(result[2]) if len(result) > 2 else "True"
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
            logging.info(f"[Bithumb] Order placed: {side} @ {price:,.0f}원 (ID: {order_id})")
            return order_id
        
        logging.error(f"[Bithumb] Order failed: {result}")
        return False
    
    def _place_order_ccxt(self, side: str, size: float, stop_loss: float, price: float) -> bool:
        """ccxt로 주문"""
        symbol = f"{self.coin}/KRW"
        order_side = 'buy' if side == 'Long' else 'sell'
        
        order = self.bithumb.create_order(
            symbol=symbol,
            type='market',
            side=order_side,
            amount=size
        )
        
        if order:
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
            logging.info(f"[Bithumb] Order placed: {side} @ {price:,.0f}원 (ID: {order_id})")
            return order_id
        
        return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정 (로컬 관리 - 빗썸은 SL 미지원)"""
        if self.position:
            self.position.stop_loss = new_sl
            logging.info(f"[Bithumb] SL updated (local): {new_sl:,.0f}원")
            return True
        return False
    
    def close_position(self) -> bool:
        """포지션 청산"""
        try:
            if not self.position:
                return True
            
            if self.bithumb is None:
                return False
            
            balance = self.get_coin_balance()
            
            if balance > 0:
                if self.use_ccxt:
                    symbol = f"{self.coin}/KRW"
                    self.bithumb.create_order(symbol, 'market', 'sell', balance)
                else:
                    self.bithumb.sell_market_order(self.coin, balance)
                
                price = self.get_current_price()
                pnl = (price - self.position.entry_price) / self.position.entry_price * 100
                
                logging.info(f"[Bithumb] Position closed: PnL {pnl:.2f}%")
            
            self.position = None
            return True
            
        except Exception as e:
            logging.error(f"[Bithumb] Close error: {e}")
            return False
    
    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입"""
        try:
            if not self.position or side != self.position.side:
                return False
            
            price = self.get_current_price()
            
            if self.use_ccxt:
                symbol = f"{self.coin}/KRW"
                order_side = 'buy' if side == 'Long' else 'sell'
                result = self.bithumb.create_order(symbol, 'market', order_side, size)
            else:
                if side == 'Long':
                    result = self.bithumb.buy_market_order(self.coin, size)
                else:
                    result = self.bithumb.sell_market_order(self.coin, size)
            
            if result and (self.use_ccxt or result[0] == 'success'):
                order_id = ""
                if self.use_ccxt:
                    order_id = str(result.get('id', ''))
                elif len(result) > 2:
                    order_id = str(result[2])
                
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                self.position.order_id = order_id
                
                logging.info(f"[Bithumb] Added: {size} @ {price:,.0f}원 (ID: {order_id})")
                return order_id
            
            return False
            
        except Exception as e:
            logging.error(f"[Bithumb] Add position error: {e}")
            return False
    
    def get_balance(self) -> float:
        """KRW 잔고 조회"""
        if self.bithumb is None:
            return 0
        try:
            if self.use_ccxt:
                balance = self.bithumb.fetch_balance()
                return float(balance.get('KRW', {}).get('free', 0))
            else:
                return safe_float(self.bithumb.get_balance("KRW"))
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0

    def get_positions(self) -> list:
        """모든 보유 코인 조회 (현물 포지션으로 간주)"""
        if self.bithumb is None:
            return []
        try:
            positions = []
            if self.use_ccxt:
                balance = self.bithumb.fetch_balance()
                # 0이 아닌 잔고들을 포지션으로 변환
                for coin, data in balance.get('free', {}).items():
                    _data_val = safe_float(data)
                    if coin != 'KRW' and _data_val > 0:
                        positions.append({
                            'symbol': f"{coin}_KRW",
                            'side': 'Buy',
                            'size': _data_val,
                            'entry_price': 0, # 현물은 진입가 추적이 어려움 (API 지원에 따라 다름)
                            'unrealized_pnl': 0,
                            'leverage': 1
                        })
            else:
                # pybithumb는 전체 잔고 조회가 무거우므로 현재 심볼 위주로 체크하거나 전체 순회
                # 여기서는 현재 심볼 코인만 우선 체크
                bal = self.get_coin_balance()
                if bal > 0:
                    positions.append({
                        'symbol': f"{self.coin}_KRW",
                        'side': 'Buy',
                        'size': bal,
                        'entry_price': 0,
                        'unrealized_pnl': 0,
                        'leverage': 1
                    })
            return positions
        except Exception as e:
            logging.error(f"포지션 조회 에러: {e}")
            return []
    
    def get_coin_balance(self) -> float:
        """코인 잔고 조회"""
        try:
            if self.bithumb is None:
                return 0
            
            if self.use_ccxt:
                balance = self.bithumb.fetch_balance()
                return float(balance.get(self.coin, {}).get('free', 0))
            else:
                return float(self.bithumb.get_balance(self.coin) or 0)
        except Exception as e:
            logging.error(f"Coin balance error: {e}")
            return 0
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정 (현물이라 미지원)"""
        logging.info(f"[Bithumb] Spot market - leverage not supported (ignored: {leverage}x)")
        self.leverage = 1
        return True

    # ============================================
    # WebSocket + 자동 시간 동기화 (Phase 2+3)
    # ============================================
    
    async def start_websocket(self, interval='15m', on_candle_close=None, on_price_update=None, on_connect=None):
        """웹소켓 시작"""
        try:
            from exchanges.ws_handler import WebSocketHandler
            
            self.ws_handler = WebSocketHandler(
                exchange='bithumb', # lower case for handler
                symbol=self.symbol,
                interval=interval
            )
            
            self.ws_handler.on_candle_close = on_candle_close
            self.ws_handler.on_price_update = on_price_update
            self.ws_handler.on_connect = on_connect
            
            import asyncio
            asyncio.create_task(self.ws_handler.connect())
            
            import logging
            logging.info(f"[Bithumb] WebSocket connected: {{self.symbol}}")
            return True
        except Exception as e:
            import logging
            logging.error(f"[Bithumb] WebSocket failed: {{e}}")
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
                logging.debug(f"[Bithumb] Time synced: offset={{self.time_offset}}ms")
                return True
        except Exception as e:
            logging.debug(f"[Bithumb] Time sync failed: {{e}}")
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
        """API로 청산된 거래 히스토리 조회 (Bithumb/CCXT)"""
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
                    'pnl': 0,  # Spot doesn't have realized PnL
                    'created_time': str(t.get('timestamp', '')),
                    'updated_time': str(t.get('timestamp', ''))
                })
            
            logging.info(f"[Bithumb] Trade history loaded: {len(trades)} trades")
            return trades
            
        except Exception as e:
            logging.warning(f"[Bithumb] Trade history error: {e}")
            return super().get_trade_history(limit)

