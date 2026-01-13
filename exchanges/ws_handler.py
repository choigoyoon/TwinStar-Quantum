# exchanges/ws_handler.py
"""
웹소켓 핸들러 - 통합 거래소 실시간 캔들 스트림
- 지원: Bybit, Binance, Upbit, Bithumb, OKX, Bitget, BingX
- 봉 마감 감지 → 콜백 호출
- 자동 재연결 및 상태 모니터링
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Dict
from datetime import datetime
import time

try:
    import websockets
except ImportError:
    websockets = None
    logging.warning("websockets not installed. Run: pip install websockets")


class WebSocketHandler:
    """통합 거래소 웹소켓 핸들러"""
    
    # 거래소별 엔드포인트
    WS_ENDPOINTS = {
        'bybit': 'wss://stream.bybit.com/v5/public/linear',
        'binance': 'wss://fstream.binance.com/ws',  # Futures
        'upbit': 'wss://api.upbit.com/websocket/v1',
        'bithumb': 'wss://pubwss.bithumb.com/pub/ws',
        'okx': 'wss://ws.okx.com:8443/ws/v5/public',
        'bitget': 'wss://ws.bitget.com/mix/v1/stream',
        'bingx': 'wss://open-api-swap.bingx.com/swap-market',
    }
    
    # Interval 변환 맵 (거래소별 포맷)
    INTERVAL_MAP = {
        'bybit': {'1m': '1', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '4h': '240', '1d': 'D'},
        'binance': {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d'},
        'upbit': {'1m': '1', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '4h': '240', '1d': 'D'}, # Upbit uses minutes
        'bithumb': {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d'}, # Generic
        'okx': {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'},
        'bitget': {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1H', '4h': '4H', '1d': '1D'},
        'bingx': {'1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', '4h': '4h', '1d': '1d'},
    }
    
    def __init__(self, exchange: str, symbol: str, interval: str = '15m'):
        """
        Args:
            exchange: 거래소 ID ('bybit', 'binance', 'upbit', ...)
            symbol: 심볼 ('BTCUSDT', 'KRW-BTC' 등)
            interval: 타임프레임 ('15m', '1h' 등)
        """
        self.exchange = exchange.lower()
        self.symbol = symbol.upper()
        self.interval = interval
        
        self.ws = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnects = 20
        self.reconnect_delay = 3
        self.max_reconnect_delay = 60
        self.backoff_factor = 1.5
        
        # 콜백 함수
        self.on_candle_close: Optional[Callable[[Dict], None]] = None
        self.on_price_update: Optional[Callable[[float], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 상태
        self.last_candle: Optional[Dict] = None
        self.is_connected = False
        self.last_message_time: Optional[datetime] = None
        self._last_candle_ts: Optional[int] = None
    
    def _get_reconnect_delay(self) -> float:
        delay = self.reconnect_delay * (self.backoff_factor ** self.reconnect_attempts)
        return min(delay, self.max_reconnect_delay)
    
    def is_healthy(self, timeout_seconds: int = 30) -> bool:
        if not self.is_connected:
            return False
        if self.last_message_time is None:
            return False
        elapsed = (datetime.now() - self.last_message_time).total_seconds()
        return elapsed < timeout_seconds
        
    def get_ws_url(self) -> str:
        url = self.WS_ENDPOINTS.get(self.exchange)
        if not url:
            # Fallback for manual URLs if needed
            if 'wss://' in self.exchange:
                 return self.exchange
            raise ValueError(f"Unsupported exchange: {self.exchange}")
        return url
    
    def get_subscribe_message(self) -> dict:
        """거래소별 구독 메시지 생성"""
        
        if self.exchange.lower() == 'bybit':
            iv = self.INTERVAL_MAP['bybit'].get(self.interval, '15')
            return {"op": "subscribe", "args": [f"kline.{iv}.{self.symbol}"]}
            
        elif self.exchange.lower() == 'binance':
            symbol_lower = self.symbol.lower()
            return {
                "method": "SUBSCRIBE",
                "params": [f"{symbol_lower}@kline_{self.interval}"],
                "id": int(time.time())
            }
            
        elif self.exchange.lower() == 'upbit':
            # Upbit Request: [{"ticket":"UNIQUE_TICKET"}, {"type":"ticker","codes":["KRW-BTC"]}]
            # Note: Upbit WS doesn't support kline directly mostly, usually use ticker/trade for price
            # But we can emulate or use their undocumented candle types if available, 
            # generally we use 'ticker' for realtime price and strict polling for close, 
            # OR we try to detect high/low/close from trade stream. 
            # For simplicity & reliability, we subscribe to 'ticker' for Price updates 
            # and we might simulate local candle close or rely on REST for candle structure if WS is limited.
            # HOWEVER, verifying standard implementation: mostly we use ticker for live price.
            return [
                {"ticket": f"twin_{int(time.time())}"},
                {"type": "ticker", "codes": [self.symbol]}
            ]
            
        elif self.exchange.lower() == 'bithumb':
            # {"type":"ticker", "symbols": ["BTC_KRW"], "tickTypes": ["30M"]}
            # Bithumb WS symbols are like "BTC_KRW"
            sym = self.symbol.replace('-', '_').replace('/', '_')
            return {
                "type": "ticker", 
                "symbols": [sym], 
                "tickTypes": [self.interval.upper()] # 30M, 1H, 12H, 24H, MID
            }
            
        elif self.exchange.lower() == 'okx':
            # Channel: candle15m
            iv = self.INTERVAL_MAP['okx'].get(self.interval, '15m')
            inst_id = self.symbol.replace('/', '-').replace('USDT', '-USDT-SWAP') # Futures convention
            # Check if spot? Assume Swap for verified implementation
            if '-' not in inst_id: inst_id = f"{inst_id}-SWAP"
            
            return {
                "op": "subscribe",
                "args": [{"channel": f"candle{iv}", "instId": inst_id}]
            }
            
        elif self.exchange.lower() == 'bitget':
            iv = self.INTERVAL_MAP['bitget'].get(self.interval, '15m')
            return {
                "op": "subscribe",
                "args": [{
                    "instType": "MC", # MC=Futures, SP=Spot
                    "channel": f"candle{iv}",
                    "instId": self.symbol
                }]
            }
            
        elif self.exchange.lower() == 'bingx':
            # {"id":"id1","reqType":"sub","dataType":"BTC-USDT@kline_15m"}
            return {
                "id": str(int(time.time())),
                "reqType": "sub",
                "dataType": f"{self.symbol}@kline_{self.interval}"
            }
            
        else:
            return {}

    async def connect(self):
        """웹소켓 연결 및 유지"""
        if websockets is None:
            raise ImportError("websockets library not installed")
        
        self.running = True
        self.reconnect_attempts = 0
        
        while self.running:
            if self.reconnect_attempts >= self.max_reconnects:
                logging.warning("[WS] ⚠️ Max reconnects reached, waiting 5min...")
                self.reconnect_attempts = 0
                await asyncio.sleep(300)
                continue
            
            try:
                url = self.get_ws_url()
                logging.info(f"[WS] Connecting to {self.exchange} ({url})...")
                
                async with websockets.connect(url, ping_interval=20, ping_timeout=10, close_timeout=5) as ws:
                    self.ws = ws
                    self.is_connected = True
                    self.reconnect_attempts = 0
                    self.last_message_time = datetime.now()
                    
                    logging.info(f"[WS] ✅ Connected to {self.exchange}")
                    if self.on_connect: self.on_connect()
                    
                    # Send Subscribe
                    msg = self.get_subscribe_message()
                    if self.exchange.lower() == 'upbit':
                        await ws.send(json.dumps(msg)) # Upbit expects list
                    else:
                        await ws.send(json.dumps(msg))
                        
                    logging.debug(f"[WS] Subscribed: {msg}")
                    
                    async for message in ws:
                        if not self.running: break
                        await self._handle_message(message)
                        
            except Exception as e:
                self.is_connected = False
                self.reconnect_attempts += 1
                logging.warning(f"[WS] Connection lost ({self.exchange}): {e}")
                if self.on_disconnect: self.on_disconnect(str(e))
                
                await asyncio.sleep(self._get_reconnect_delay())

    async def _handle_message(self, message):
        """메시지 라우팅"""
        try:
            data = json.loads(message)
            self.last_message_time = datetime.now()
            
            # Auth check
            if isinstance(data, dict):
                if '401' in str(data.get('code', '')) or 'Unauthorized' in str(data.get('msg', '')):
                     if self.on_error: self.on_error("401 Unauthorized")
            
            if self.exchange.lower() == 'bybit': await self._parse_bybit(data)
            elif self.exchange.lower() == 'binance': await self._parse_binance(data)
            elif self.exchange.lower() == 'upbit': await self._parse_upbit(data)
            elif self.exchange.lower() == 'bithumb': await self._parse_bithumb(data)
            elif self.exchange.lower() == 'okx': await self._parse_okx(data)
            elif self.exchange.lower() == 'bitget': await self._parse_bitget(data)
            elif self.exchange.lower() == 'bingx': await self._parse_bingx(data)
            
        except Exception as e:
            logging.error(f"[WS] Parse error ({self.exchange}): {e}")
            logging.debug(f"[WS] Raw msg: {message[:100]}...")

    # ================= Parsing Logic =================
    
    async def _parse_bybit(self, data: dict):
        if 'topic' not in data or 'kline' not in data.get('topic', ''): return
        k = data.get('data', [])[0]
        candle = {
            'timestamp': int(k.get('start', 0)),
            'open': float(k.get('open', 0)),
            'high': float(k.get('high', 0)),
            'low': float(k.get('low', 0)),
            'close': float(k.get('close', 0)),
            'volume': float(k.get('volume', 0)),
            'confirm': k.get('confirm', False)
        }
        if self.on_price_update: self.on_price_update(candle['close'])
        if candle['confirm'] and self.on_candle_close: self.on_candle_close(candle)

    async def _parse_binance(self, data: dict):
        # {"e":"kline", "k": {"t":..., "o":..., "c":..., "x":True}}
        if data.get('e') != 'kline': return
        k = data.get('k', {})
        is_closed = k.get('x', False)
        candle = {
            'timestamp': int(k.get('t', 0)), # ms
            'open': float(k.get('o', 0)),
            'high': float(k.get('h', 0)),
            'low': float(k.get('l', 0)),
            'close': float(k.get('c', 0)),
            'volume': float(k.get('v', 0)),
            'confirm': is_closed
        }
        if self.on_price_update: self.on_price_update(candle['close'])
        if is_closed and self.on_candle_close: self.on_candle_close(candle)

    async def _parse_upbit(self, data: dict):
        # Upbit Ticker: {"type":"ticker", "code":"KRW-BTC", "trade_price":..., "timestamp":...}
        # Upbit doesn't push Candle Closed event reliably. 
        # We rely on price updates. Real candle close logic must be handled by 
        # the bot checking time boundaries if using Upbit WS for OHLCV.
        # Here we just push price updates.
        if data.get('type') == 'ticker':
            price = float(data.get('trade_price', 0))
            if self.on_price_update: self.on_price_update(price)

    async def _parse_bithumb(self, data: dict):
        # {"type":"ticker", "content": {"tickType":"30M", "date":..., "closePrice":...}}
        if data.get('type') == 'ticker':
            content = data.get('content', {})
            price = float(content.get('closePrice', 0))
            if self.on_price_update: self.on_price_update(price)
            # Bithumb ticker stream is tricky for precise candle close. 
            # Treating as price stream primarily.

    async def _parse_okx(self, data: dict):
        # {"arg":{...}, "data": [ {"c":..., "confirm":"1"} ]}
        data_list = data.get('data', [])
        if not isinstance(data_list, list): return
        for k in data_list:
            is_closed = (k.get('confirm') == '1')
            candle = {
                'timestamp': int(k.get('ts', 0)),
                'open': float(k.get('o', 0)),
                'high': float(k.get('h', 0)),
                'low': float(k.get('l', 0)),
                'close': float(k.get('c', 0)),
                'volume': float(k.get('vol', 0)),
                'confirm': is_closed
            }
            if self.on_price_update: self.on_price_update(candle['close'])
            if is_closed and self.on_candle_close: self.on_candle_close(candle)
            
    async def _parse_bitget(self, data: dict):
        # {"action":"snapshot", "arg":{...}, "data":[ {"open":..., "close":..., "ts":...} ]}
        # Bitget doesn't have 'confirm' flag in all streams. 
        # Assuming we just update price.
        data_list = data.get('data', [])
        if not isinstance(data_list, list): return
        for k in data_list:
            price = float(k.get('close', 0))
            if self.on_price_update: self.on_price_update(price)
            
    async def _parse_bingx(self, data: dict):
        # {"code":0, "data": {"T":..., "o":..., "c":...}, "dataType":"...kline..."}
        if 'data' not in data: return
        k = data['data']
        # BingX format requires validation
        if isinstance(k, dict):
             price = float(k.get('c', 0))
             if self.on_price_update: self.on_price_update(price)
             # BingX WS doc check: confirm flag usually missing in swap market ticker
             # We rely on price update.

    def disconnect(self):
        """연결 종료 (동기/비동기 모두 지원)"""
        self.running = False
        self.is_connected = False
        
        if self.ws is None:
            return
        
        try:
            # 방법 1: 실행 중인 루프가 있으면 태스크로 실행
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.ws.close())
            else:
                loop.run_until_complete(self.ws.close())
        except Exception:
            # 방법 2: 루프가 없거나 문제 발생 시 새 스레드에서 강제 종료
            try:
                import threading
                def _force_close():
                    try:
                        new_loop = asyncio.new_event_loop()
                        new_loop.run_until_complete(self.ws.close())
                        new_loop.close()
                    except Exception:

                        pass
                t = threading.Thread(target=_force_close, daemon=True)
                t.start()
                t.join(timeout=1)
            except Exception:

                pass
        
        self.ws = None

    def run_sync(self):
        """동기 실행 (스레드용)"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.connect())
        except Exception as e:
            logger.error(f"[WS-SYNC] Fatal Error: {e}")
        finally:
            self.disconnect()

