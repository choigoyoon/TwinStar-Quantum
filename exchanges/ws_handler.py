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
from typing import Callable, Optional, Dict, Union, List, Any
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
    
    def __init__(self, exchange: str, symbol: str, interval: str = '15m', time_manager: Optional[Any] = None):
        """
        Args:
            exchange: 거래소 ID ('bybit', 'binance', 'upbit', ...)
            symbol: 심볼 ('BTCUSDT', 'KRW-BTC' 등) - 거래소 원본 형식 유지 권장
            interval: 타임프레임 ('15m', '1h' 등)
            time_manager: 시간 동기화 매니저 (Phase C: 봉 마감 감지용)
        """
        self.exchange = exchange.lower()
        self.symbol = symbol  # 원본 유지 (거래소별 정규화는 _normalize_symbol에서 처리)
        self.interval = interval
        self.time_manager = time_manager  # ✅ Phase C: 시간 동기화 매니저

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

        # ✅ Phase C: 봉 마감 감지기 (Bitget, BingX용)
        self.close_detector: Optional[Any] = None
        if time_manager:
            try:
                from core.candle_close_detector import CandleCloseDetector
                self.close_detector = CandleCloseDetector(
                    exchange_name=exchange,
                    interval=interval,
                    time_manager=time_manager
                )
                logging.debug(f"[WS] ✅ CandleCloseDetector initialized for {exchange}")
            except Exception as e:
                logging.warning(f"[WS] CandleCloseDetector init failed: {e}")
    
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

    def _normalize_symbol(self, for_exchange: str) -> str:
        """
        거래소별 심볼 형식 정규화

        Args:
            for_exchange: 거래소 ID ('bybit', 'binance', ...)

        Returns:
            정규화된 심볼 (거래소별 형식)

        Examples:
            Bybit: 'BTCUSDT' → 'BTCUSDT'
            Binance: 'BTCUSDT' → 'btcusdt'
            Upbit: 'KRW-BTC' → 'KRW-BTC'
            Bithumb: 'BTC_KRW' → 'BTC_KRW'
            OKX: 'BTCUSDT' → 'BTC-USDT-SWAP'
            Bitget: 'BTCUSDT' → 'BTCUSDT'
            BingX: 'BTCUSDT' → 'BTC-USDT'
        """
        symbol = self.symbol.strip()

        # Bybit: 대문자, 하이픈 제거
        if for_exchange == 'bybit':
            return symbol.upper().replace('-', '').replace('/', '').replace('_', '')

        # Binance: 소문자, 하이픈 제거
        elif for_exchange == 'binance':
            return symbol.lower().replace('-', '').replace('/', '').replace('_', '')

        # Upbit: 대문자, 하이픈 유지 (KRW-BTC 형식)
        elif for_exchange == 'upbit':
            # 'BTCUSDT' → 'KRW-BTC' 변환 불가 (사용자가 올바른 형식으로 입력해야 함)
            return symbol.upper()

        # Bithumb: 언더스코어 변환 (BTC_KRW 형식)
        elif for_exchange == 'bithumb':
            return symbol.replace('-', '_').replace('/', '_').upper()

        # OKX: 하이픈 + SWAP 접미사 (BTC-USDT-SWAP 형식)
        elif for_exchange == 'okx':
            # 'BTCUSDT' → 'BTC-USDT-SWAP'
            if 'USDT' in symbol.upper() and '-' not in symbol:
                base = symbol.upper().replace('USDT', '')
                return f"{base}-USDT-SWAP"
            # 이미 하이픈 포함 ('BTC-USDT')
            elif '-' in symbol and 'SWAP' not in symbol.upper():
                return f"{symbol.upper()}-SWAP"
            # 이미 SWAP 포함
            return symbol.upper()

        # Bitget: 대문자 유지
        elif for_exchange == 'bitget':
            return symbol.upper()

        # BingX: 하이픈 변환 (BTC-USDT 형식)
        elif for_exchange == 'bingx':
            # 'BTCUSDT' → 'BTC-USDT'
            if 'USDT' in symbol.upper() and '-' not in symbol:
                base = symbol.upper().replace('USDT', '')
                return f"{base}-USDT"
            return symbol.upper()

        # 기본값: 대문자
        return symbol.upper()
    
    def get_subscribe_message(self) -> Union[dict, list]:
        """거래소별 구독 메시지 생성 (심볼 자동 정규화)"""

        # 거래소별 심볼 정규화
        normalized_symbol = self._normalize_symbol(self.exchange)

        if self.exchange == 'bybit':
            iv = self.INTERVAL_MAP['bybit'].get(self.interval, '15')
            return {"op": "subscribe", "args": [f"kline.{iv}.{normalized_symbol}"]}

        elif self.exchange == 'binance':
            return {
                "method": "SUBSCRIBE",
                "params": [f"{normalized_symbol}@kline_{self.interval}"],
                "id": int(time.time())
            }

        elif self.exchange == 'upbit':
            # Upbit Request: [{"ticket":"UNIQUE_TICKET"}, {"type":"ticker","codes":["KRW-BTC"]}]
            # Note: Upbit WS doesn't support kline directly mostly, usually use ticker/trade for price
            return [
                {"ticket": f"twin_{int(time.time())}"},
                {"type": "ticker", "codes": [normalized_symbol]}
            ]

        elif self.exchange == 'bithumb':
            # {"type":"ticker", "symbols": ["BTC_KRW"], "tickTypes": ["30M"]}
            return {
                "type": "ticker",
                "symbols": [normalized_symbol],
                "tickTypes": [self.interval.upper()] # 30M, 1H, 12H, 24H, MID
            }

        elif self.exchange == 'okx':
            # Channel: candle15m
            iv = self.INTERVAL_MAP['okx'].get(self.interval, '15m')
            return {
                "op": "subscribe",
                "args": [{"channel": f"candle{iv}", "instId": normalized_symbol}]
            }

        elif self.exchange == 'bitget':
            iv = self.INTERVAL_MAP['bitget'].get(self.interval, '15m')
            return {
                "op": "subscribe",
                "args": [{
                    "instType": "MC", # MC=Futures, SP=Spot
                    "channel": f"candle{iv}",
                    "instId": normalized_symbol
                }]
            }

        elif self.exchange == 'bingx':
            # {"id":"id1","reqType":"sub","dataType":"BTC-USDT@kline_15m"}
            return {
                "id": str(int(time.time())),
                "reqType": "sub",
                "dataType": f"{normalized_symbol}@kline_{self.interval}"
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
                logging.error("[WS] ❌ Max reconnects reached, stopping WebSocket")
                self.running = False
                break  # ✅ P0-1: 무한 루프 종료
            
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

                # ✅ P1-2: WebSocket 좀비 연결 정리
                if self.ws:
                    try:
                        await self.ws.close()
                    except Exception:
                        pass
                    self.ws = None  # 명시적 정리

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

        except json.JSONDecodeError as e:
            # ✅ P2-3: JSON 파싱 에러 상세 로깅
            logging.error(f"[WS] ❌ JSON parse error ({self.exchange}): {e}")
            logging.error(f"[WS] Error position: line {e.lineno}, col {e.colno}")
            logging.error(f"[WS] Raw message (first 200 chars): {message[:200]}")
        except Exception as e:
            # ✅ P2-3: 일반 에러 상세 로깅
            logging.error(f"[WS] Parse error ({self.exchange}): {e}")
            logging.error(f"[WS] Error type: {type(e).__name__}")
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
        # ✅ Phase C: 봉 마감 감지 추가 (타임스탬프 기반)
        data_list = data.get('data', [])
        if not isinstance(data_list, list): return
        for k in data_list:
            candle = {
                'timestamp': int(k.get('ts', 0)),
                'open': float(k.get('open', 0)),
                'high': float(k.get('high', 0)),
                'low': float(k.get('low', 0)),
                'close': float(k.get('close', 0)),
                'volume': float(k.get('vol', 0)),
            }

            # 가격 업데이트
            if self.on_price_update:
                self.on_price_update(candle['close'])

            # ✅ 봉 마감 감지 (타임스탬프 기반)
            if self.close_detector and self.on_candle_close:
                if self.close_detector.detect_close(candle, ws_confirm=None):
                    self.on_candle_close(candle)
            
    async def _parse_bingx(self, data: dict):
        # {"code":0, "data": {"T":..., "o":..., "c":...}, "dataType":"...kline..."}
        # ✅ Phase C: 봉 마감 감지 추가 (타임스탬프 기반)
        if 'data' not in data: return
        k = data['data']
        # BingX format requires validation
        if isinstance(k, dict):
            candle = {
                'timestamp': int(k.get('T', 0)),
                'open': float(k.get('o', 0)),
                'high': float(k.get('h', 0)),
                'low': float(k.get('l', 0)),
                'close': float(k.get('c', 0)),
                'volume': float(k.get('v', 0)),
            }

            # 가격 업데이트
            if self.on_price_update:
                self.on_price_update(candle['close'])

            # ✅ 봉 마감 감지 (타임스탬프 기반)
            if self.close_detector and self.on_candle_close:
                if self.close_detector.detect_close(candle, ws_confirm=None):
                    self.on_candle_close(candle)

    def stop(self):
        """WebSocket 정상 종료 (외부 호출용)"""
        logging.info("[WS] Stopping WebSocket...")
        self.running = False

        # ✅ P2-2: 콜백 정리 (메모리 누수 방지)
        self.on_candle_close = None
        self.on_price_update = None
        self.on_connect = None
        self.on_disconnect = None
        self.on_error = None

        # WebSocket 연결이 있으면 닫기
        if self.ws and hasattr(self, 'loop') and self.loop:
            try:
                if not self.loop.is_closed():
                    # 비동기 태스크로 WebSocket 종료 요청
                    asyncio.run_coroutine_threadsafe(
                        self.ws.close(),
                        self.loop
                    )
            except Exception as e:
                logging.warning(f"[WS] Graceful close failed: {e}")

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
                        if self.ws:
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
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop  # Store loop reference for graceful shutdown
            loop.run_until_complete(self.connect())
        except Exception as e:
            logging.error(f"[WS-SYNC] Fatal Error: {e}")
        finally:
            self.disconnect()
            if loop and not loop.is_closed():
                loop.close()
                logging.debug("[WS] Event loop closed")

