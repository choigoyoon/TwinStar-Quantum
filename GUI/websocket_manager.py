# C:\매매전략\gui\websocket_manager.py

import asyncio
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum
import queue

# Logging
import logging
logger = logging.getLogger(__name__)

# Windows asyncio 호환성
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@dataclass
class RealtimeCandle:
    """실시간 캔들 데이터"""
    symbol: str
    timeframe: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool  # 캔들 완성 여부

class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

class WebSocketManager:
    """
    실시간 WebSocket 데이터 관리자
    - 멀티 심볼/타임프레임 지원
    - 자동 재연결
    - 콜백 기반 데이터 전달
    """
    
    SUPPORTED_EXCHANGES = ['binance', 'bybit', 'okx', 'bingx', 'bitget']
    
    def __init__(self):
        self.streams: Dict[str, dict] = {}  # stream_id → stream info
        self.status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self.exchange = None
        self.exchange_name = ""
        
        # 콜백
        self.on_candle: Optional[Callable[[RealtimeCandle], None]] = None
        self.on_status: Optional[Callable[[ConnectionStatus], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 스레드 관리
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._data_queue = queue.Queue()
        
        # 재연결 설정
        self.reconnect_delay = 5  # 초
        self.max_reconnect_attempts = 10
    
    def _get_stream_id(self, symbol: str, timeframe: str) -> str:
        """스트림 고유 ID"""
        return f"{self.exchange_name}_{symbol}_{timeframe}"
    
    async def _connect_ccxt_pro(self, symbols: List[str], timeframe: str):
        """ccxt.pro를 이용한 WebSocket 연결"""
        try:
            import ccxt.pro as ccxtpro
            
            exchange_class = getattr(ccxtpro, self.exchange_name)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            
            # 마켓 로드 (async)
            await self.exchange.load_markets()
            
            self._update_status(ConnectionStatus.CONNECTED)
            logger.info(f"✅ WebSocket 연결 성공: {self.exchange_name}")
            
            while not self._stop_event.is_set():
                try:
                    for symbol in symbols:
                        ohlcv = await self.exchange.watch_ohlcv(symbol, timeframe)
                        
                        if ohlcv and len(ohlcv) > 0:
                            latest = ohlcv[-1]
                            candle = RealtimeCandle(
                                symbol=symbol,
                                timeframe=timeframe,
                                timestamp=latest[0],
                                open=latest[1],
                                high=latest[2],
                                low=latest[3],
                                close=latest[4],
                                volume=latest[5],
                                is_closed=False
                            )
                            self._data_queue.put(candle)
                            
                except Exception as e:
                    if not self._stop_event.is_set():
                        logger.info(f"⚠️ 스트림 에러: {e}")
                        await asyncio.sleep(1)
            
        except ImportError:
            logger.info("⚠️ ccxtpro 없음, 폴링 모드로 전환")
            await self._polling_fallback(symbols, timeframe)
        
        except Exception as e:
            self._update_status(ConnectionStatus.ERROR)
            if self.on_error:
                self.on_error(str(e))
    
    async def _polling_fallback(self, symbols: List[str], timeframe: str):
        """ccxt.pro 없을 때 폴링 방식"""
        try:
            import ccxt
            
            exchange_class = getattr(ccxt, self.exchange_name)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            self.exchange.load_markets()
            
            self._update_status(ConnectionStatus.CONNECTED)
            logger.info(f"✅ 폴링 모드 시작: {self.exchange_name}")
            
            # 타임프레임별 폴링 간격 (초)
            poll_intervals = {
                '1m': 10, '3m': 30, '5m': 60, '15m': 120,
                '30m': 180, '1h': 300, '4h': 600, '1d': 1800
            }
            interval = poll_intervals.get(timeframe, 60)
            
            while not self._stop_event.is_set():
                for symbol in symbols:
                    try:
                        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=2)
                        if ohlcv and len(ohlcv) > 0:
                            latest = ohlcv[-1]
                            candle = RealtimeCandle(
                                symbol=symbol,
                                timeframe=timeframe,
                                timestamp=latest[0],
                                open=latest[1],
                                high=latest[2],
                                low=latest[3],
                                close=latest[4],
                                volume=latest[5],
                                is_closed=len(ohlcv) > 1
                            )
                            self._data_queue.put(candle)
                    except Exception as e:
                        logger.info(f"⚠️ 폴링 에러 {symbol}: {e}")
                
                # 폴링 간격 대기
                for _ in range(interval):
                    if self._stop_event.is_set():
                        break
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self._update_status(ConnectionStatus.ERROR)
            if self.on_error:
                self.on_error(str(e))
    
    def _process_queue(self):
        """큐에서 데이터 처리 (메인 스레드 안전)"""
        while True:
            try:
                candle = self._data_queue.get_nowait()
                if self.on_candle:
                    self.on_candle(candle)
            except queue.Empty:
                break
    
    def _update_status(self, status: ConnectionStatus):
        """상태 업데이트 및 콜백"""
        self.status = status
        if self.on_status:
            self.on_status(status)
    
    def _run_async(self, symbols: List[str], timeframe: str):
        """비동기 루프 실행 (별도 스레드)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                self._connect_ccxt_pro(symbols, timeframe)
            )
        finally:
            loop.close()
    
    def start(self, exchange: str, symbols: List[str], timeframe: str = '1m'):
        """
        WebSocket 스트림 시작
        
        Args:
            exchange: 'binance', 'bybit' 등
            symbols: ['BTC/USDT:USDT', 'ETH/USDT:USDT']
            timeframe: '1m', '5m', '15m' 등
        """
        if self._thread and self._thread.is_alive():
            logger.info("⚠️ 이미 실행 중")
            return False
        
        self.exchange_name = exchange.lower()
        self._stop_event.clear()
        self._update_status(ConnectionStatus.CONNECTING)
        
        # 심볼 정규화
        normalized_symbols = []
        for sym in symbols:
            if '/' not in sym:
                sym = f"{sym[:-4]}/{sym[-4:]}:{sym[-4:]}"
            normalized_symbols.append(sym)
        
        # 스트림 등록
        for sym in normalized_symbols:
            stream_id = self._get_stream_id(sym, timeframe)
            self.streams[stream_id] = {
                'symbol': sym,
                'timeframe': timeframe,
                'started': datetime.now()
            }
        
        # 별도 스레드에서 실행
        self._thread = threading.Thread(
            target=self._run_async,
            args=(normalized_symbols, timeframe),
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"🚀 WebSocket 시작: {exchange} {normalized_symbols} {timeframe}")
        return True
    
    def stop(self):
        """모든 스트림 중지"""
        self._stop_event.set()
        
        if self.exchange:
            try:
                asyncio.run(self.exchange.close())
            except Exception:
                pass  # asyncio close 실패 무시
        
        if self._thread:
            self._thread.join(timeout=5)
        
        self.streams.clear()
        self._update_status(ConnectionStatus.DISCONNECTED)
        logger.info("🛑 WebSocket 중지")
    
    def add_stream(self, symbol: str, timeframe: str) -> bool:
        """스트림 추가 (런타임)"""
        # 현재 구현에서는 재시작 필요
        logger.info(f"⚠️ 스트림 추가는 재시작 필요: {symbol} {timeframe}")
        return False
    
    def remove_stream(self, symbol: str, timeframe: str) -> bool:
        """스트림 제거"""
        stream_id = self._get_stream_id(symbol, timeframe)
        if stream_id in self.streams:
            del self.streams[stream_id]
            return True
        return False
    
    def get_active_streams(self) -> List[dict]:
        """활성 스트림 목록"""
        return list(self.streams.values())
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.status == ConnectionStatus.CONNECTED


# GUI 연동용 래퍼 (PyQt5 시그널 호환)
class WebSocketThread:
    """PyQt5 위젯과 연동하기 위한 래퍼"""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
        self._timer = None
    
    def start_with_qt(self, widget, exchange: str, symbols: List[str], timeframe: str):
        """
        PyQt5 위젯과 함께 시작
        
        widget: update_candle(candle) 메서드 필요
        """
        from PyQt6.QtCore import QTimer
        
        def process_data():
            self.manager._process_queue()
        
        # 콜백 설정
        self.manager.on_candle = widget.update_candle if hasattr(widget, 'update_candle') else None
        self.manager.on_status = widget.update_status if hasattr(widget, 'update_status') else None
        
        # 데이터 처리 타이머 (100ms마다)
        self._timer = QTimer()
        self._timer.timeout.connect(process_data)
        self._timer.start(100)
        
        # WebSocket 시작
        self.manager.start(exchange, symbols, timeframe)
    
    def stop(self):
        if self._timer:
            self._timer.stop()
        self.manager.stop()


# 테스트
if __name__ == "__main__":
    ws = WebSocketManager()
    
    # 콜백 설정
    def on_candle(candle: RealtimeCandle):
        logger.info(f"📊 {candle.symbol} {candle.timeframe}: {candle.close:.2f} (완성: {candle.is_closed})")
    
    def on_status(status: ConnectionStatus):
        logger.info(f"📡 상태: {status.value}")
    
    ws.on_candle = on_candle
    ws.on_status = on_status
    
    # 시작
    logger.info("🚀 WebSocket 테스트 시작...")
    ws.start('bybit', ['BTCUSDT'], '1m')
    
    # 30초 실행
    try:
        for i in range(30):
            ws._process_queue()  # 콜백 처리
            time.sleep(1)
            logger.info(f"⏱️ {i+1}/30초...")
    except KeyboardInterrupt:
        pass
    finally:
        ws.stop()
        logger.info("✅ 테스트 완료")
