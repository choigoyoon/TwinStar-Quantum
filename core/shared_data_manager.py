"""
TwinStar-Quantum Shared Data Manager

싱글/멀티 매매 시스템 간 데이터 공유를 위한 중앙 관리 모듈.

아키텍처:
    SharedDataManager
        ├─ BotDataManager (BTCUSDT)
        ├─ BotDataManager (ETHUSDT)
        └─ BotDataManager (50+ symbols)

책임:
    1. 심볼별 BotDataManager 인스턴스 관리
    2. WebSocket 멀티플렉싱 데이터 분배
    3. 배치 Parquet 저장 (I/O 효율)
    4. 스레드 안전한 데이터 접근

Author: Claude Opus 4.5
Date: 2026-01-15
"""

import threading
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class SharedDataManager:
    """싱글/멀티 매매 시스템 간 데이터 공유 관리자"""

    def __init__(
        self,
        exchange_name: str,
        cache_dir: str = 'data/cache',
        max_memory_candles: int = 1000
    ):
        """
        Args:
            exchange_name: 거래소 이름 (bybit, binance, etc.)
            cache_dir: Parquet 캐시 디렉토리
            max_memory_candles: 메모리에 유지할 최대 캔들 수
        """
        self.exchange_name = exchange_name.lower()
        self.cache_dir = Path(cache_dir)
        self.max_memory_candles = max_memory_candles

        # 심볼별 BotDataManager 인스턴스
        self.symbol_managers: Dict[str, BotDataManager] = {}

        # 스레드 안전성
        self._lock = threading.RLock()

        # 통계
        self.stats = {
            'symbols_loaded': 0,
            'total_candles_managed': 0,
            'last_batch_save': None
        }

        logger.info(
            f"SharedDataManager 초기화: {exchange_name}, "
            f"cache={cache_dir}, max_memory={max_memory_candles}"
        )

    def get_manager(self, symbol: str) -> BotDataManager:
        """
        심볼별 BotDataManager 반환 (없으면 생성)

        Args:
            symbol: 거래 심볼 (BTCUSDT, ETHUSDT 등)

        Returns:
            BotDataManager 인스턴스 (스레드 안전)
        """
        with self._lock:
            if symbol not in self.symbol_managers:
                logger.info(f"새 BotDataManager 생성: {symbol}")
                manager = BotDataManager(
                    exchange_name=self.exchange_name,
                    symbol=symbol
                )
                self.symbol_managers[symbol] = manager
                self.stats['symbols_loaded'] += 1

            return self.symbol_managers[symbol]

    def append_candle_batch(
        self,
        candles: Dict[str, dict],
        save_immediately: bool = False
    ) -> None:
        """
        여러 심볼의 캔들을 배치로 추가 (WebSocket 멀티플렉싱용)

        Args:
            candles: {symbol: candle_dict} 형식
            save_immediately: True이면 즉시 Parquet 저장

        Example:
            >>> candles = {
            ...     'BTCUSDT': {'timestamp': ..., 'open': 50000, ...},
            ...     'ETHUSDT': {'timestamp': ..., 'open': 3000, ...}
            ... }
            >>> manager.append_candle_batch(candles)
        """
        for symbol, candle in candles.items():
            manager = self.get_manager(symbol)
            # save=False로 메모리에만 추가
            manager.append_candle(candle, save=False)

        self.stats['total_candles_managed'] += len(candles)

        # 배치 저장 (효율적)
        if save_immediately:
            self.batch_save_parquet()

    def batch_save_parquet(self) -> int:
        """
        모든 심볼의 데이터를 배치로 Parquet 저장

        Returns:
            저장된 심볼 수

        Notes:
            - 개별 저장 대비 I/O 효율 향상
            - 15분마다 호출 권장
        """
        saved_count = 0

        with self._lock:
            for symbol, manager in self.symbol_managers.items():
                try:
                    manager.save_parquet()
                    saved_count += 1
                except Exception as e:
                    logger.error(f"{symbol} Parquet 저장 실패: {e}")

        self.stats['last_batch_save'] = datetime.now()
        logger.info(f"배치 Parquet 저장 완료: {saved_count}개 심볼")

        return saved_count

    def load_historical_batch(
        self,
        symbols: List[str]
    ) -> Dict[str, bool]:
        """
        여러 심볼의 히스토리 데이터를 배치로 로드

        Args:
            symbols: 로드할 심볼 리스트

        Returns:
            {symbol: success} 딕셔너리
        """
        results: Dict[str, bool] = {}

        for symbol in symbols:
            manager = self.get_manager(symbol)
            try:
                # BotDataManager.load_historical() 호출
                success = manager.load_historical()
                results[symbol] = success
                if success:
                    logger.info(f"{symbol} 히스토리 로드 성공")
                else:
                    logger.warning(f"{symbol} 히스토리 로드 실패")
            except Exception as e:
                results[symbol] = False
                logger.error(f"{symbol} 히스토리 로드 실패: {e}")

        return results

    def get_memory_usage(self) -> Dict[str, int]:
        """
        심볼별 메모리 사용량 조회 (캔들 개수)

        Returns:
            {symbol: candle_count} 딕셔너리
        """
        usage = {}
        with self._lock:
            for symbol, manager in self.symbol_managers.items():
                if hasattr(manager, 'df_entry_full') and manager.df_entry_full is not None:
                    usage[symbol] = len(manager.df_entry_full)
                else:
                    usage[symbol] = 0

        return usage

    def cleanup_old_symbols(self, max_symbols: int = 100) -> int:
        """
        사용하지 않는 오래된 심볼 메모리 정리

        Args:
            max_symbols: 유지할 최대 심볼 수

        Returns:
            정리된 심볼 수
        """
        with self._lock:
            if len(self.symbol_managers) <= max_symbols:
                return 0

            # Parquet 저장 후 메모리에서 제거
            symbols = list(self.symbol_managers.keys())
            to_remove = symbols[:len(symbols) - max_symbols]

            for symbol in to_remove:
                manager = self.symbol_managers[symbol]
                manager.save_parquet()
                del self.symbol_managers[symbol]

            logger.info(f"{len(to_remove)}개 심볼 메모리 정리 완료")
            return len(to_remove)

    def get_stats(self) -> dict:
        """통계 정보 반환"""
        with self._lock:
            memory_usage = self.get_memory_usage()
            return {
                **self.stats,
                'active_symbols': len(self.symbol_managers),
                'total_memory_candles': sum(memory_usage.values()),
                'memory_per_symbol': memory_usage
            }

    def __repr__(self) -> str:
        return (
            f"SharedDataManager(exchange={self.exchange_name}, "
            f"symbols={len(self.symbol_managers)}, "
            f"total_candles={self.stats['total_candles_managed']})"
        )
