"""
TwinStar Quantum - Async Scanner
aiohttp를 이용한 대량 심볼 동시 데이터 수집 및 스캔
"""
import asyncio
import aiohttp
import pandas as pd
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AsyncScanner:
    """
    비동기 마켓 스캐너
    - Bybit/Binance API 비동기 호출
    - 50개 이상의 심볼 동시 데이터 수집
    - 병렬 지표 계산
    """
    
    def __init__(self, exchange: str = 'bybit'):
        self.exchange = exchange.lower()
        self.base_url = self._get_base_url()
        
    def _get_base_url(self) -> str:
        if self.exchange == 'bybit':
            return "https://api.bybit.com/v5/market/kline"
        elif self.exchange == 'binance':
            return "https://fapi.binance.com/fapi/v1/klines"
        return ""

    async def fetch_kline(self, session: aiohttp.ClientSession, symbol: str, timeframe: str, limit: int = 200) -> Optional[Dict]:
        """단일 심볼 캔들 데이터 비동기 수집"""
        params = self._get_params(symbol, timeframe, limit)
        try:
            async with session.get(self.base_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return {'symbol': symbol, 'data': data}
                else:
                    logger.debug(f"[ASYNC] Failed {symbol}: Status {response.status}")
                    return None
        except Exception as e:
            logger.debug(f"[ASYNC] Error {symbol}: {e}")
            return None

    def _get_params(self, symbol: str, timeframe: str, limit: int) -> Dict:
        if self.exchange == 'bybit':
            # Bybit v5 mapping
            tf_map = {'1m': '1', '5m': '5', '15m': '15', '1h': '60', '4h': '240', '1d': 'D'}
            return {
                'category': 'linear',
                'symbol': symbol,
                'interval': tf_map.get(timeframe, '15'),
                'limit': limit
            }
        elif self.exchange == 'binance':
            return {
                'symbol': symbol,
                'interval': timeframe,
                'limit': limit
            }
        return {}

    async def scan_symbols(self, symbols: List[str], timeframe: str) -> List[Dict]:
        """여러 심볼 동시 스캔"""
        start_time = time.time()
        logger.info(f"[ASYNC] Scanning {len(symbols)} symbols on {timeframe}...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_kline(session, symbol, timeframe) for symbol in symbols]
            results = await asyncio.gather(*tasks)
            
        valid_results = [r for r in results if r is not None]
        
        elapsed = time.time() - start_time
        logger.info(f"[ASYNC] Scan completed in {elapsed:.2f}s (Success: {len(valid_results)}/{len(symbols)})")
        
        return valid_results

    def run_sync_scan(self, symbols: List[str], timeframe: str) -> List[Dict]:
        """동기 인터페이스 (GUI 라이브러리 등에서 호출용)"""
        return asyncio.run(self.scan_symbols(symbols, timeframe))

if __name__ == "__main__":
    # 테스트
    scanner = AsyncScanner('bybit')


    test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT'] * 10 # 50개 테스트
    
    # Windows 에러 방지
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    results = scanner.run_sync_scan(test_symbols, '15m')
    logger.info(f"Total results: {len(results)}")

