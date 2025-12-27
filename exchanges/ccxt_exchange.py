# exchanges/ccxt_exchange.py
"""
CCXT 기반 범용 거래소 어댑터
100개 이상의 거래소를 하나의 어댑터로 지원
+ WebSocket 실시간 데이터 지원
"""

import logging
import pandas as pd
import threading
from datetime import datetime
from typing import Optional, Callable

from .base_exchange import BaseExchange, Position

# WebSocket 핸들러 import (선택적)
try:
    from .ws_handler import WebSocketHandler
except ImportError:
    WebSocketHandler = None
    logging.info("WebSocket handler not available, using REST only")

from .base_exchange import BaseExchange, Position

try:
    import ccxt
except ImportError:
    ccxt = None

# 지원 거래소 목록 (선물 거래 가능)
SUPPORTED_EXCHANGES = {
    # 해외 거래소 (선물)
    'bybit': {
        'class': 'bybit', 
        'type': 'swap', 
        'has_futures': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT']
    },
    'binance': {
        'class': 'binance', 
        'type': 'future', 
        'has_futures': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
    },
    'okx': {
        'class': 'okx', 
        'type': 'swap', 
        'has_futures': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'LTCUSDT']
    },
    'bitget': {
        'class': 'bitget', 
        'type': 'swap', 
        'has_futures': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'ARBUSDT']
    },
    'bingx': {
        'class': 'bingx', 
        'type': 'swap', 
        'has_futures': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'ARBUSDT', 'OPUSDT']
    },
    'gate': {
        'class': 'gate', 
        'type': 'swap', 
        'has_futures': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT', 'ATOMUSDT']
    },
    
    # 한국 거래소 (현물만)
    'upbit': {
        'class': 'upbit', 
        'type': 'spot', 
        'has_futures': False,
        'symbols': ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-DOGE', 'KRW-ADA', 'KRW-AVAX', 'KRW-LINK', 'KRW-DOT', 'KRW-MATIC']
    },
    'bithumb': {
        'class': 'bithumb', 
        'type': 'spot', 
        'has_futures': False,
        'symbols': ['BTC-KRW', 'ETH-KRW', 'XRP-KRW', 'SOL-KRW', 'DOGE-KRW', 'ADA-KRW', 'AVAX-KRW', 'LINK-KRW', 'DOT-KRW', 'MATIC-KRW']
    },
}


def get_symbols_for_exchange(exchange_id: str) -> list:
    """거래소별 지원 심볼 목록 반환"""
    exchange = SUPPORTED_EXCHANGES.get(exchange_id.lower())
    if exchange:
        return exchange.get('symbols', ['BTCUSDT', 'ETHUSDT'])
    return ['BTCUSDT', 'ETHUSDT']


class CCXTExchange(BaseExchange):
    """CCXT 기반 범용 거래소 어댑터"""
    
    def __init__(self, exchange_id: str, config: dict):
        """
        exchange_id: 거래소 ID (bybit, binance, okx, bitget 등)
        config: API 설정
        """
        super().__init__(config)
        
        if ccxt is None:
            raise ImportError("ccxt not installed! Run: pip install ccxt")
        
        self.exchange_id = exchange_id.lower()
        self.api_key = config.get('api_key', '')
        self.api_secret = config.get('api_secret', '')
        self.passphrase = config.get('passphrase', '')  # OKX, Bitget 등
        self.testnet = config.get('testnet', False)
        
        self.exchange_info = SUPPORTED_EXCHANGES.get(self.exchange_id)
        if not self.exchange_info:
            logging.warning(f"Exchange {exchange_id} not in predefined list, trying anyway...")
            self.exchange_info = {'class': exchange_id, 'type': 'swap', 'has_futures': True}
        
        self.ccxt_exchange = None
        self._exchange_name = exchange_id.upper()
        
        # WebSocket 관련
        self.ws_handler = None
        self.ws_thread = None
        self.use_websocket = False
        self._ws_last_price = None
    
    @property
    def name(self) -> str:
        return self._exchange_name
    
    # ========== WebSocket 지원 ==========
    
    def start_websocket(self, interval: str = '15m',
                        on_candle_close: Callable = None,
                        on_price_update: Callable = None):
        """웹소켓 연결 시작"""
        if WebSocketHandler is None:
            logging.warning("[WS] WebSocketHandler not available")
            return False
        
        if self.ws_handler and self.ws_handler.running:
            logging.info("[WS] Already running")
            return True
        
        self.ws_handler = WebSocketHandler(self.exchange_id, self.symbol, interval)
        
        # 콜백 저장 (재시작 시 사용)
        self._ws_interval = interval
        self._ws_candle_cb = on_candle_close
        self._ws_price_cb = on_price_update
        
        # 내부 가격 저장 콜백
        def _internal_price_update(price):
            self._ws_last_price = price
            if on_price_update:
                on_price_update(price)
        
        self.ws_handler.on_candle_close = on_candle_close
        self.ws_handler.on_price_update = _internal_price_update
        self.use_websocket = True
        
        # 별도 스레드에서 실행
        self.ws_thread = threading.Thread(target=self.ws_handler.run_sync, daemon=True)
        self.ws_thread.start()
        logging.info(f"[WS] Started for {self.symbol} @ {interval}")
        return True
    
    def restart_websocket(self):
        """웹소켓 재연결"""
        import time
        self.stop_websocket()
        time.sleep(1)
        if hasattr(self, '_ws_interval') and hasattr(self, '_ws_candle_cb'):
            return self.start_websocket(
                interval=self._ws_interval,
                on_candle_close=self._ws_candle_cb,
                on_price_update=self._ws_price_cb
            )
        return False
    
    def stop_websocket(self):
        """웹소켓 연결 중지"""
        if self.ws_handler:
            self.ws_handler.stop()
            self.use_websocket = False
            self._ws_last_price = None
            logging.info("[WS] Stopped")
    
    def get_current_price_fast(self) -> float:
        """웹소켓 가격 우선, 없으면 REST fallback"""
        if self.use_websocket and self._ws_last_price is not None:
            return self._ws_last_price
        return self.get_current_price()
    
    def is_ws_connected(self) -> bool:
        """웹소켓 연결 상태"""
        return self.ws_handler is not None and self.ws_handler.is_connected
    
    def connect(self) -> bool:
        """거래소 연결"""
        try:
            exchange_class = self.exchange_info['class']
            
            # CCXT 거래소 객체 생성
            exchange_config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': self.exchange_info['type'],
                    'recvWindow': 60000, # 기본 60초 설정 (Bybit 등 지원)
                    'adjustForTimeDifference': True, # 시간 차이 자동 보정
                }
            }
            
            # Passphrase 필요한 거래소
            if self.passphrase:
                exchange_config['password'] = self.passphrase
            
            # Testnet 설정
            if self.testnet:
                exchange_config['sandbox'] = True
            
            # 거래소 객체 생성
            self.ccxt_exchange = getattr(ccxt, exchange_class)(exchange_config)
            
            # 시간 동기화 로드
            if hasattr(self.ccxt_exchange, 'load_time_difference'):
                 self.ccxt_exchange.load_time_difference()

            # 시장 정보 로드
            self.ccxt_exchange.load_markets()
            
            # 잔고 확인
            if self.api_key:
                balance = self.get_balance()
                logging.info(f"{self.name} connected. Balance: {balance:.2f} USDT")
            else:
                logging.info(f"{self.name} connected (read-only mode)")
            
            return True
            
        except Exception as e:
            logging.error(f"{self.name} connect error: {e}")
            return False
    
    def get_klines(self, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회"""
        try:
            # 타임프레임 변환
            tf_map = {
                '1': '1m', '5': '5m', '15': '15m', '30': '30m',
                '60': '1h', '240': '4h', '1440': '1d'
            }
            timeframe = tf_map.get(interval, interval)
            
            # 심볼 형식 변환 (거래소마다 다름)
            symbol = self._convert_symbol(self.symbol)
            
            ohlcv = self.ccxt_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logging.error(f"Kline fetch error: {e}")
            return None
    
    def _convert_symbol(self, symbol: str) -> str:
        """심볼 형식 변환"""
        # BTCUSDT -> BTC/USDT:USDT (선물)
        # BTCUSDT -> BTC/USDT (현물)
        
        base = symbol.replace('USDT', '').replace('USD', '')
        quote = 'USDT' if 'USDT' in symbol else 'USD'
        
        if self.exchange_info['has_futures']:
            return f"{base}/{quote}:{quote}"
        else:
            return f"{base}/{quote}"
    
    def get_current_price(self) -> float:
        """현재 가격"""
        try:
            symbol = self._convert_symbol(self.symbol)
            ticker = self.ccxt_exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logging.error(f"Price fetch error: {e}")
            return 0
    
    def place_market_order(self, side: str, size: float, stop_loss: float) -> bool:
        """시장가 주문"""
        try:
            symbol = self._convert_symbol(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            
            # 시장가 주문
            order = self.ccxt_exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=size,
                params={'recvWindow': 60000}
            )
            
            if order:
                price = self.get_current_price()
                
                # 손절 주문 설정 (거래소 지원 여부에 따라)
                try:
                    sl_side = 'sell' if side == 'Long' else 'buy'
                    sl_order = self.ccxt_exchange.create_order(
                        symbol=symbol,
                        type='stop_market',
                        side=sl_side,
                        amount=size,
                        params={
                            'stopPrice': stop_loss,
                            'reduceOnly': True
                        }
                    )
                except Exception as sl_err:
                    logging.warning(f"SL order not supported or failed: {sl_err}")
                
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
                
                logging.info(f"Order placed: {side} {size} @ {price} (ID: {order_id})")
                return order_id
            
            return False
            
        except Exception as e:
            logging.error(f"Order error: {e}")
            return False
    
    def update_stop_loss(self, new_sl: float) -> bool:
        """손절가 수정"""
        try:
            symbol = self._convert_symbol(self.symbol)
            
            # 기존 스탑 주문 취소
            try:
                open_orders = self.ccxt_exchange.fetch_open_orders(symbol)
                for order in open_orders:
                    if order.get('type') in ['stop_market', 'stop']:
                        if isinstance(order, dict) and order.get('id'):
                            self.ccxt_exchange.cancel_order(order['id'], symbol)
            except Exception as e:
                logging.debug(f"Order cancel ignored: {e}")
            
            # 새 스탑 주문 생성
            if self.position:
                sl_side = 'sell' if self.position.side == 'Long' else 'buy'
                self.ccxt_exchange.create_order(
                    symbol=symbol,
                    type='stop_market',
                    side=sl_side,
                    amount=self.position.size,
                    params={
                        'stopPrice': new_sl,
                        'reduceOnly': True
                    }
                )
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
            
            symbol = self._convert_symbol(self.symbol)
            close_side = 'sell' if self.position.side == 'Long' else 'buy'
            
            order = self.ccxt_exchange.create_order(
                symbol=symbol,
                type='market',
                side=close_side,
                amount=self.position.size,
                params={'reduceOnly': True}
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

    def add_position(self, side: str, size: float) -> bool:
        """포지션 추가 진입 (불타기)"""
        try:
            if not self.position:
                return False
            
            # 방향 검증
            if side != self.position.side:
                return False
            
            symbol = self._convert_symbol(self.symbol)
            order_side = 'buy' if side == 'Long' else 'sell'
            
            # 시장가 주문
            order = self.ccxt_exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=size
            )
            
            if order:
                price = self.get_current_price()
                
                order_id = str(order.get('id', ''))
                # 평단가 재계산
                total_size = self.position.size + size
                avg_price = (self.position.entry_price * self.position.size + price * size) / total_size
                
                self.position.size = total_size
                self.position.entry_price = avg_price
                self.position.order_id = order_id
                
                logging.info(f"Added position: {side} {size} @ {price} (ID: {order_id})")
                return order_id
            
            return False
            
        except Exception as e:
            logging.error(f"Add position error: {e}")
            return False
    
    def set_leverage(self, leverage: int) -> bool:
        """레버리지 설정 (CCXT 범용)"""
        try:
            symbol = self._convert_symbol(self.symbol)
            
            # CCXT의 set_leverage 사용 (거래소 지원 여부에 따라)
            if hasattr(self.ccxt_exchange, 'set_leverage'):
                self.ccxt_exchange.set_leverage(leverage, symbol)
                self.leverage = leverage
                logging.info(f"[{self.name}] Leverage set to {leverage}x")
                return True
            else:
                logging.warning(f"[{self.name}] set_leverage not supported")
                self.leverage = leverage  # 로컬만 저장
                return True
                
        except Exception as e:
            # 이미 동일한 레버리지면 성공 처리
            if "leverage not modified" in str(e).lower():
                self.leverage = leverage
                return True
            logging.error(f"[{self.name}] Leverage error: {e}")
            return False
    
    def fetch_balance(self) -> dict:
        """전체 잔고 조회 (CCXT 원본)"""
        try:
            return self.ccxt_exchange.fetch_balance()
        except Exception as e:
            logging.error(f"Fetch balance error: {e}")
            return {}

    def get_balance(self) -> float:
        """잔고 조회"""
        try:
            balance = self.ccxt_exchange.fetch_balance()
            # USDT가 없으면 KRW 확인 (국내 거래소)
            usdt_bal = float(balance.get('USDT', {}).get('free', 0))
            if usdt_bal == 0:
                return float(balance.get('KRW', {}).get('free', 0))
            return usdt_bal
        except Exception as e:
            logging.error(f"Balance error: {e}")
            return 0
    
    # ========== [NEW] API 기반 매매 히스토리 ==========
    
    def get_trade_history(self, limit: int = 50) -> list:
        """CCXT API로 매매 히스토리 조회 (모든 거래소 지원)"""
        try:
            if self.ccxt_exchange is None:
                return super().get_trade_history(limit)
            
            symbol = self._convert_symbol(self.symbol)
            
            # CCXT의 fetch_my_trades 사용 (모든 거래소 호환)
            try:
                raw_trades = self.ccxt_exchange.fetch_my_trades(symbol, limit=limit)
            except Exception:
                # 지원 안 되면 로컬 파일에서 로드
                return super().get_trade_history(limit)
            
            trades = []
            for t in raw_trades:
                trades.append({
                    'symbol': t.get('symbol', self.symbol),
                    'side': t.get('side', 'buy').capitalize(),
                    'qty': float(t.get('amount', 0)),
                    'price': float(t.get('price', 0)),
                    'pnl': float(t.get('info', {}).get('realizedPnl', 0) or 0),  # 거래소마다 다름
                    'fee': float(t.get('fee', {}).get('cost', 0) or 0),
                    'created_time': t.get('datetime', ''),
                    'timestamp': t.get('timestamp', 0),
                    'order_id': t.get('order', '')
                })
            
            logging.info(f"Trade history loaded via CCXT: {len(trades)} trades from {self.name}")
            
            # 로컬에도 저장
            if trades:
                self.save_trade_history_to_log(trades)
            
            return trades
            
        except Exception as e:
            logging.error(f"CCXT trade history error: {e}")
            return super().get_trade_history(limit)


def get_supported_exchanges() -> list:
    """지원 거래소 목록 반환"""
    return list(SUPPORTED_EXCHANGES.keys())


def create_ccxt_exchange(exchange_id: str, config: dict) -> CCXTExchange:
    """CCXT 거래소 어댑터 생성"""
    return CCXTExchange(exchange_id, config)
