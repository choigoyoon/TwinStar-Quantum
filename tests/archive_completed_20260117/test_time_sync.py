"""
tests/test_time_sync.py
TimeSyncManager 단위 테스트 (Phase C-5)

Test Coverage:
    - 시간 동기화 정확도
    - 네트워크 지연(RTT) 보정
    - 레이턴시 이동 평균
    - 거래소별 서버 시간 추출
"""

import pytest
import time
from core.time_sync import TimeSyncManager


class TestTimeSyncManager:
    """TimeSyncManager 단위 테스트"""

    def test_init(self):
        """초기화 테스트"""
        manager = TimeSyncManager('bybit')

        assert manager.exchange_name == 'bybit'
        assert manager.offset != 0.0  # 초기 동기화 완료
        assert len(manager.latency_history) > 0
        assert manager.last_sync_time > 0

    def test_sync_accuracy(self):
        """시간 동기화 정확도 테스트"""
        manager = TimeSyncManager('bybit')

        # 5초 대기 후 재동기화
        time.sleep(5)

        # 오프셋이 ±100ms 범위인지 확인
        offset = manager.get_offset()
        assert abs(offset) < 0.1, f"Offset too large: {offset}s"

    def test_latency_tracking(self):
        """레이턴시 추적 테스트"""
        manager = TimeSyncManager('bybit')

        # 10회 동기화
        for _ in range(10):
            manager._sync_now(force=True)
            time.sleep(0.1)

        # 평균 레이턴시가 50-500ms 범위인지 확인
        avg_latency = manager.get_avg_latency()
        assert 50 <= avg_latency <= 500, f"Abnormal latency: {avg_latency}ms"

    def test_server_time(self):
        """서버 시간 반환 테스트"""
        manager = TimeSyncManager('bybit')

        server_time = manager.get_server_time()

        # 서버 시간이 현재 시간과 ±1초 범위인지 확인
        local_time = time.time()
        assert abs(server_time - local_time) < 1.0, \
            f"Server time deviation: {abs(server_time - local_time):.3f}s"

    def test_get_stats(self):
        """통계 반환 테스트"""
        import time
        manager = TimeSyncManager('bybit')

        # 여러 번 동기화 수행 (min/max 레이턴시 변화 유도)
        for _ in range(5):
            manager._sync_now(force=True)  # 강제 동기화
            time.sleep(0.1)  # 레이턴시 변화 유도

        stats = manager.get_stats()

        assert 'offset' in stats
        assert 'avg_latency' in stats
        assert 'min_latency' in stats
        assert 'max_latency' in stats
        assert 'last_sync_time' in stats

        assert stats['avg_latency'] > 0
        assert stats['min_latency'] > 0
        assert stats['max_latency'] >= stats['min_latency']  # >= 로 변경 (동일한 경우도 허용)

    def test_multiple_exchanges(self):
        """여러 거래소 동기화 테스트"""
        exchanges = ['bybit', 'binance', 'okx']

        for exchange in exchanges:
            manager = TimeSyncManager(exchange)
            offset = manager.get_offset()
            assert abs(offset) < 1.0, f"{exchange} offset too large: {offset}s"

    def test_unsupported_exchange(self):
        """지원하지 않는 거래소 테스트"""
        manager = TimeSyncManager('unknown_exchange')

        # 초기 동기화 실패 (offset은 0으로 유지)
        assert manager.offset == 0.0


if __name__ == '__main__':
    # 개별 테스트 실행
    import logging
    logging.basicConfig(level=logging.DEBUG)

    test = TestTimeSyncManager()

    print("=" * 80)
    print("TimeSyncManager 단위 테스트 시작")
    print("=" * 80)

    print("\n[1/7] 초기화 테스트...")
    test.test_init()
    print("✅ 통과")

    print("\n[2/7] 시간 동기화 정확도 테스트...")
    test.test_sync_accuracy()
    print("✅ 통과")

    print("\n[3/7] 레이턴시 추적 테스트...")
    test.test_latency_tracking()
    print("✅ 통과")

    print("\n[4/7] 서버 시간 반환 테스트...")
    test.test_server_time()
    print("✅ 통과")

    print("\n[5/7] 통계 반환 테스트...")
    test.test_get_stats()
    print("✅ 통과")

    print("\n[6/7] 여러 거래소 동기화 테스트...")
    test.test_multiple_exchanges()
    print("✅ 통과")

    print("\n[7/7] 지원하지 않는 거래소 테스트...")
    test.test_unsupported_exchange()
    print("✅ 통과")

    print("\n" + "=" * 80)
    print("✅ 모든 테스트 통과!")
    print("=" * 80)
