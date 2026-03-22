"""
core/candle_close_detector.py
봉 마감 감지 로직 (Phase C-2)

Features:
    - 3가지 감지 방식 지원
      1. WebSocket confirm 플래그 (Bybit, Binance, OKX)
      2. 타임스탬프 경계 감지 (Bitget, BingX)
      3. 로컬 시간 경계 감지 (Upbit, Bithumb - 폴백)
    - 봉 경계 자동 정렬 (14:15:03 → 14:15:00)
    - 중복 감지 방지
"""

from datetime import datetime
import pandas as pd
from typing import Optional, Dict, Any, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from core.time_sync import TimeSyncManager

logger = logging.getLogger(__name__)


class CandleCloseDetector:
    """
    봉 마감 감지 로직 (3가지 방식)

    Usage:
        ```python
        detector = CandleCloseDetector('bybit', '15m', time_manager)

        # WebSocket confirm 플래그 방식
        candle = {'timestamp': ts, 'close': 50000, 'confirm': True}
        if detector.detect_close(candle, ws_confirm=True):
            print("봉 마감!")

        # 타임스탬프 경계 방식 (Bitget, BingX)
        candle = {'timestamp': pd.Timestamp('2024-01-15 14:15:00', tz='UTC'), 'close': 50000}
        if detector.detect_close(candle, ws_confirm=None):
            print("봉 마감!")

        # 봉 경계 정렬
        ts = pd.Timestamp('2024-01-15 14:15:03', tz='UTC')
        aligned = detector.align_to_boundary(ts)  # 14:15:00
        ```

    Note:
        - 우선순위: WebSocket confirm > 타임스탬프 경계 > 로컬 시간 경계
        - 중복 감지 방지 (last_close_time 추적)
        - 타임존: UTC aware Timestamp 필수
    """

    def __init__(
        self,
        exchange_name: str,
        interval: str = '15m',
        time_manager: Optional['TimeSyncManager'] = None,
        cache_size: int = 100
    ):
        """
        Args:
            exchange_name: 거래소 ID ('bybit', 'binance', ...)
            interval: 타임프레임 ('15m', '1h', '4h', '1d')
            time_manager: 시간 동기화 매니저 (로컬 시간 경계 감지용)
            cache_size: 중복 감지 캐시 크기 (기본: 100) ✅ P2-4
        """
        self.exchange_name = exchange_name.lower()
        self.interval = interval
        self.time_manager = time_manager

        # 봉 경계 (분 단위)
        self.boundary_minutes = self._get_boundary_minutes(interval)

        # ✅ P2-4: 이전 봉 마감 시간 추적 (중복 방지, 캐시 크기 제한)
        self.last_close_time: Optional[pd.Timestamp] = None
        self.cache_size = cache_size
        self._close_cache: set[pd.Timestamp] = set()  # 최근 N개 봉 마감 시간

    def _get_boundary_minutes(self, interval: str) -> list[int]:
        """
        타임프레임별 봉 경계 분 계산

        Args:
            interval: 타임프레임 ('15m', '1h', '4h', '1d')

        Returns:
            봉 경계 분 리스트 (예: [0, 15, 30, 45])
        """
        if interval == '15m':
            return [0, 15, 30, 45]
        elif interval == '1h':
            return [0]
        elif interval == '4h':
            return [0]  # 4시간봉: 00, 04, 08, 12, 16, 20 (시 단위)
        elif interval == '1d':
            return [0]  # 일봉: 00:00 (시 단위)
        return []

    def detect_close(
        self,
        candle: Dict[str, Any],
        ws_confirm: Optional[bool] = None
    ) -> bool:
        """
        봉 마감 감지 (3가지 방식)

        Args:
            candle: 캔들 데이터 (timestamp, open, high, low, close, volume)
            ws_confirm: WebSocket confirm 플래그 (None이면 미지원)

        Returns:
            봉 마감 여부 (True/False)

        Note:
            - 우선순위: WebSocket confirm > 타임스탬프 경계 > 로컬 시간 경계
            - 중복 감지 방지 (last_close_time 추적)
        """
        # 방식 1: WebSocket confirm 플래그 (최우선)
        if ws_confirm is not None:
            if ws_confirm:
                logger.debug("[CLOSE_DETECT] WebSocket confirm: True")
                return True
            return False

        # 방식 2: 타임스탬프 경계 감지 (Bitget, BingX)
        if 'timestamp' in candle:
            ts = pd.to_datetime(candle['timestamp'])
            if ts.tz is None:
                ts = ts.tz_localize('UTC')

            # 15분봉 경계인지 확인
            if ts.minute in self.boundary_minutes and ts.second == 0:
                # ✅ P2-4: 캐시 기반 중복 방지 (최근 N개만 추적)
                if ts not in self._close_cache:
                    self.last_close_time = ts
                    self._close_cache.add(ts)

                    # 캐시 크기 제한 (FIFO)
                    if len(self._close_cache) > self.cache_size:
                        oldest = min(self._close_cache)
                        self._close_cache.remove(oldest)

                    logger.debug(f"[CLOSE_DETECT] Timestamp boundary: {ts} (cache: {len(self._close_cache)})")
                    return True

        # 방식 3: 로컬 시간 경계 감지 (Upbit, Bithumb - 폴백)
        if self.time_manager:
            server_time = self.time_manager.get_server_time()
            server_dt = pd.to_datetime(server_time, unit='s', utc=True)

            if server_dt.minute in self.boundary_minutes:
                # 초 단위 허용 범위: ±2초 (네트워크 지연 고려)
                if 0 <= server_dt.second <= 2 or 58 <= server_dt.second <= 59:
                    if self.last_close_time is None or server_dt.minute != self.last_close_time.minute:
                        self.last_close_time = server_dt
                        logger.debug(f"[CLOSE_DETECT] Local time boundary: {server_dt}")
                        return True

        return False

    def align_to_boundary(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        """
        타임스탬프를 봉 경계로 정렬

        Args:
            timestamp: 원본 타임스탬프

        Returns:
            봉 경계로 정렬된 타임스탬프

        Examples:
            ```python
            # 14:15:03 → 14:15:00 (15분봉)
            ts1 = pd.Timestamp('2024-01-15 14:15:03', tz='UTC')
            aligned1 = detector.align_to_boundary(ts1)
            assert aligned1 == pd.Timestamp('2024-01-15 14:15:00', tz='UTC')

            # 14:16:00 → 14:15:00 (이전 봉 시작)
            ts2 = pd.Timestamp('2024-01-15 14:16:00', tz='UTC')
            aligned2 = detector.align_to_boundary(ts2)
            assert aligned2 == pd.Timestamp('2024-01-15 14:15:00', tz='UTC')

            # 14:29:59 → 14:15:00 (이전 봉 시작)
            ts3 = pd.Timestamp('2024-01-15 14:29:59', tz='UTC')
            aligned3 = detector.align_to_boundary(ts3)
            assert aligned3 == pd.Timestamp('2024-01-15 14:15:00', tz='UTC')
            ```

        Note:
            - 봉 경계는 항상 이전 봉의 시작 시간
            - 15분봉: 00, 15, 30, 45분
            - 타임존: UTC aware Timestamp 유지
        """
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize('UTC')

        # 15분봉 경계 찾기
        minute = timestamp.minute
        aligned_minute = max([m for m in self.boundary_minutes if m <= minute], default=0)

        # 정렬된 타임스탬프 생성
        aligned = timestamp.replace(minute=aligned_minute, second=0, microsecond=0)
        return aligned

    def reset(self):
        """
        상태 초기화 (테스트용)
        """
        self.last_close_time = None
        self._close_cache.clear()  # ✅ P2-4: 캐시도 초기화


if __name__ == '__main__':
    # 테스트 코드
    logging.basicConfig(level=logging.DEBUG)

    detector = CandleCloseDetector('bybit', '15m')

    # 테스트 1: WebSocket confirm 플래그
    candle1 = {
        'timestamp': pd.Timestamp('2024-01-15 14:15:00', tz='UTC'),
        'close': 50000.0
    }
    assert detector.detect_close(candle1, ws_confirm=True)
    assert not detector.detect_close(candle1, ws_confirm=False)
    print("✅ Test 1 passed: WebSocket confirm")

    # 테스트 2: 타임스탬프 경계 감지
    detector.reset()
    candle2 = {
        'timestamp': pd.Timestamp('2024-01-15 14:15:00', tz='UTC'),
        'close': 50000.0
    }
    assert detector.detect_close(candle2, ws_confirm=None)
    print("✅ Test 2 passed: Timestamp boundary")

    # 테스트 3: 봉 경계 정렬
    ts1 = pd.Timestamp('2024-01-15 14:15:03', tz='UTC')
    aligned1 = detector.align_to_boundary(ts1)
    assert aligned1 == pd.Timestamp('2024-01-15 14:15:00', tz='UTC')

    ts2 = pd.Timestamp('2024-01-15 14:29:59', tz='UTC')
    aligned2 = detector.align_to_boundary(ts2)
    assert aligned2 == pd.Timestamp('2024-01-15 14:15:00', tz='UTC')
    print("✅ Test 3 passed: Boundary alignment")

    print("\n✅ All tests passed!")
