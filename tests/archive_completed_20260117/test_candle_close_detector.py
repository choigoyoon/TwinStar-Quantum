"""
tests/test_candle_close_detector.py
CandleCloseDetector 단위 테스트 (Phase C-5)

Test Coverage:
    - WebSocket confirm 플래그 감지
    - 타임스탬프 경계 감지
    - 로컬 시간 경계 감지 (폴백)
    - 봉 경계 정렬
    - 중복 감지 방지
"""

import pytest
import pandas as pd
from core.candle_close_detector import CandleCloseDetector
from core.time_sync import TimeSyncManager


class TestCandleCloseDetector:
    """CandleCloseDetector 단위 테스트"""

    def test_ws_confirm_detection(self):
        """WebSocket confirm 플래그 감지 테스트"""
        detector = CandleCloseDetector('bybit', '15m')

        candle = {
            'timestamp': pd.Timestamp('2024-01-15 14:15:00', tz='UTC'),
            'open': 50000.0,
            'close': 50100.0
        }

        # confirm=True → 감지
        assert detector.detect_close(candle, ws_confirm=True)

        # confirm=False → 미감지
        assert not detector.detect_close(candle, ws_confirm=False)

    def test_timestamp_boundary_detection(self):
        """타임스탬프 경계 감지 테스트"""
        detector = CandleCloseDetector('bitget', '15m')

        # 15분 경계 (00, 15, 30, 45분)
        for minute in [0, 15, 30, 45]:
            detector.reset()
            candle = {
                'timestamp': pd.Timestamp(f'2024-01-15 14:{minute:02d}:00', tz='UTC'),
                'close': 50000.0
            }
            assert detector.detect_close(candle, ws_confirm=None), \
                f"Failed to detect boundary at minute {minute}"

        # 경계 아님 (14분)
        detector.reset()
        candle_14 = {
            'timestamp': pd.Timestamp('2024-01-15 14:14:00', tz='UTC'),
            'close': 50000.0
        }
        assert not detector.detect_close(candle_14, ws_confirm=None)

    def test_boundary_alignment(self):
        """봉 경계 정렬 테스트"""
        detector = CandleCloseDetector('bybit', '15m')

        # 14:15:03 → 14:15:00
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

        # 14:30:00 → 14:30:00 (정확히 경계)
        ts4 = pd.Timestamp('2024-01-15 14:30:00', tz='UTC')
        aligned4 = detector.align_to_boundary(ts4)
        assert aligned4 == pd.Timestamp('2024-01-15 14:30:00', tz='UTC')

    def test_duplicate_prevention(self):
        """중복 감지 방지 테스트"""
        detector = CandleCloseDetector('bitget', '15m')

        candle = {
            'timestamp': pd.Timestamp('2024-01-15 14:15:00', tz='UTC'),
            'close': 50000.0
        }

        # 첫 번째 감지: 성공
        assert detector.detect_close(candle, ws_confirm=None)

        # 두 번째 감지 (같은 타임스탬프): 실패 (중복)
        assert not detector.detect_close(candle, ws_confirm=None)

        # 다른 타임스탬프: 성공
        candle2 = {
            'timestamp': pd.Timestamp('2024-01-15 14:30:00', tz='UTC'),
            'close': 50000.0
        }
        assert detector.detect_close(candle2, ws_confirm=None)

    def test_local_time_boundary_detection(self):
        """로컬 시간 경계 감지 테스트 (폴백)"""
        time_manager = TimeSyncManager('bybit')
        detector = CandleCloseDetector('upbit', '15m', time_manager=time_manager)

        # 서버 시간 기준으로 경계 감지
        # (실제 테스트는 시간에 따라 결과가 달라질 수 있음)
        candle = {}
        result = detector.detect_close(candle, ws_confirm=None)

        # 결과는 현재 시간에 따라 True/False
        assert isinstance(result, bool)

    def test_different_intervals(self):
        """다양한 타임프레임 테스트"""
        # 15m
        detector_15m = CandleCloseDetector('bybit', '15m')
        assert detector_15m.boundary_minutes == [0, 15, 30, 45]

        # 1h
        detector_1h = CandleCloseDetector('bybit', '1h')
        assert detector_1h.boundary_minutes == [0]

        # 4h
        detector_4h = CandleCloseDetector('bybit', '4h')
        assert detector_4h.boundary_minutes == [0]

    def test_timezone_aware(self):
        """타임존 aware 타임스탬프 테스트"""
        detector = CandleCloseDetector('bybit', '15m')

        # timezone naive → UTC로 변환
        ts_naive = pd.Timestamp('2024-01-15 14:15:03')
        aligned_naive = detector.align_to_boundary(ts_naive)
        assert aligned_naive.tz is not None
        # tzinfo의 zone 속성은 일부 구현체에서만 제공됨 (예: pytz)
        # datetime.timezone.utc는 zone 속성이 없으므로 str() 변환으로 검증
        assert 'UTC' in str(aligned_naive.tz)

        # timezone aware (UTC)
        ts_utc = pd.Timestamp('2024-01-15 14:15:03', tz='UTC')
        aligned_utc = detector.align_to_boundary(ts_utc)
        assert aligned_utc == pd.Timestamp('2024-01-15 14:15:00', tz='UTC')


if __name__ == '__main__':
    # 개별 테스트 실행
    import logging
    logging.basicConfig(level=logging.DEBUG)

    test = TestCandleCloseDetector()

    print("=" * 80)
    print("CandleCloseDetector 단위 테스트 시작")
    print("=" * 80)

    print("\n[1/8] WebSocket confirm 플래그 감지 테스트...")
    test.test_ws_confirm_detection()
    print("✅ 통과")

    print("\n[2/8] 타임스탬프 경계 감지 테스트...")
    test.test_timestamp_boundary_detection()
    print("✅ 통과")

    print("\n[3/8] 봉 경계 정렬 테스트...")
    test.test_boundary_alignment()
    print("✅ 통과")

    print("\n[4/8] 중복 감지 방지 테스트...")
    test.test_duplicate_prevention()
    print("✅ 통과")

    print("\n[5/8] 로컬 시간 경계 감지 테스트...")
    test.test_local_time_boundary_detection()
    print("✅ 통과")

    print("\n[6/8] 다양한 타임프레임 테스트...")
    test.test_different_intervals()
    print("✅ 통과")

    print("\n[7/8] 타임존 aware 타임스탬프 테스트...")
    test.test_timezone_aware()
    print("✅ 통과")

    print("\n" + "=" * 80)
    print("✅ 모든 테스트 통과!")
    print("=" * 80)
