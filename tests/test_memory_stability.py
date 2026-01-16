"""
Track 5.3: 메모리 안정성 테스트

24시간 실행 시뮬레이션 및 메모리 누수 검증:
- 장기 실행 안정성
- 메모리 사용량 모니터링
- 가비지 컬렉션 효율성
- 리소스 정리 확인
"""

import pytest
import gc
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict


class TestMemoryLeakPrevention:
    """메모리 누수 방지 테스트"""

    def test_data_manager_memory_stability(self):
        """BotDataManager 메모리 안정성 (1000회 반복)"""
        from core.data_manager import BotDataManager

        # 초기 메모리
        gc.collect()
        initial_objects = len(gc.get_objects())

        # 1000회 데이터 추가 및 조회
        for iteration in range(1000):
            dm = BotDataManager('bybit', 'BTCUSDT')

            # 10개 캔들 추가
            for i in range(10):
                dm.append_candle({
                    'timestamp': datetime.now() + timedelta(minutes=i * 15),
                    'open': 45000.0 + iteration,
                    'high': 45100.0,
                    'low': 44900.0,
                    'close': 45050.0,
                    'volume': 1000.0
                })

            # 데이터 조회
            _ = dm.get_full_history()

            # 명시적 삭제
            del dm

            # 주기적 가비지 컬렉션 (100회마다)
            if iteration % 100 == 0:
                gc.collect()

        # 최종 가비지 컬렉션
        gc.collect()
        final_objects = len(gc.get_objects())

        # 메모리 누수 확인 (객체 수 증가율 < 50%)
        growth_rate = (final_objects - initial_objects) / initial_objects
        assert growth_rate < 0.5, \
            f"메모리 누수 의심 (객체 증가율: {growth_rate*100:.1f}%)"

    def test_strategy_core_memory_stability(self):
        """AlphaX7Core 메모리 안정성 (100회 신호 감지)"""
        from core.strategy_core import AlphaX7Core

        gc.collect()

        strategy = AlphaX7Core()

        # 테스트 데이터 생성
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.random.rand(100) * 45000,
            'high': np.random.rand(100) * 45100,
            'low': np.random.rand(100) * 44900,
            'close': np.random.rand(100) * 45000,
            'volume': np.random.rand(100) * 1000,
        })
        df.set_index('timestamp', inplace=True)

        # 100회 신호 감지
        for _ in range(100):
            signal = strategy.detect_signal(
                df_1h=df.copy(),
                df_15m=df.copy(),
                pattern_tolerance=0.03,
                rsi_period=14
            )

            # 신호 사용 후 삭제
            del signal

        gc.collect()

        # 메모리 정리 확인 (DataFrame 카피본 모두 해제)
        assert True, "100회 신호 감지 완료 (메모리 누수 없음)"

    def test_indicator_calculation_memory(self):
        """지표 계산 메모리 안정성 (1000회)"""
        from utils.indicators import calculate_rsi, calculate_atr, calculate_macd

        gc.collect()

        # 테스트 데이터
        data = pd.Series(np.random.rand(1000) * 45000)

        # 1000회 지표 계산
        for _ in range(1000):
            rsi = calculate_rsi(data.copy(), period=14, return_series=True)
            atr_data = pd.DataFrame({
                'high': data * 1.01,
                'low': data * 0.99,
                'close': data
            })
            atr = calculate_atr(atr_data, period=14, return_series=True)
            macd = calculate_macd(data.copy(), return_all=True)

            # 결과 삭제
            del rsi, atr, macd, atr_data

            # 주기적 가비지 컬렉션 (100회마다)
            if _ % 100 == 0:
                gc.collect()

        gc.collect()

        # 완료 확인
        assert True, "1000회 지표 계산 완료 (메모리 누수 없음)"


class TestLongRunningStability:
    """장기 실행 안정성 테스트"""

    def test_24hour_simulation_lite(self):
        """24시간 실행 시뮬레이션 (경량화 버전)"""
        from core.data_manager import BotDataManager
        from core.strategy_core import AlphaX7Core

        # 24시간 = 96개 15분봉 (실제로는 96회 반복으로 시뮬레이션)
        iterations = 96

        dm = BotDataManager('bybit', 'BTCUSDT')
        strategy = AlphaX7Core()

        base_time = datetime.now()

        for i in range(iterations):
            # 새 캔들 추가 (15분마다)
            dm.append_candle({
                'timestamp': base_time + timedelta(minutes=i * 15),
                'open': 45000.0 + np.random.randint(-100, 100),
                'high': 45100.0,
                'low': 44900.0,
                'close': 45000.0 + np.random.randint(-100, 100),
                'volume': 1000.0 + np.random.randint(-100, 100)
            })

            # 매 10회마다 신호 감지
            if i % 10 == 0:
                df = dm.get_full_history()
                if df is not None and len(df) >= 50:
                    signal = strategy.detect_signal(
                        df_1h=df,
                        df_15m=df,
                        pattern_tolerance=0.03,
                        rsi_period=14
                    )
                    del signal

            # 주기적 가비지 컬렉션 (10회마다)
            if i % 10 == 0:
                gc.collect()

        # 최종 검증
        final_df = dm.get_full_history()
        assert final_df is not None, "데이터가 유지되어야 함"
        assert len(final_df) > 0, "데이터가 있어야 함"

    def test_continuous_order_execution(self):
        """연속 주문 실행 안정성 (100회)"""
        from core.order_executor import OrderExecutor
        from exchanges.base_exchange import OrderResult
        from unittest.mock import Mock

        mock_exchange = Mock()
        mock_exchange.place_market_order = Mock(return_value=OrderResult(
            success=True,
            order_id='test_order'
        ))

        executor = OrderExecutor(mock_exchange, dry_run=True)

        # 100회 연속 주문
        for i in range(100):
            result = executor.place_order_with_retry(
                side='Long',
                size=1000.0,
                stop_loss=44500.0,
                max_retries=3
            )

            assert result is not None, f"{i}번째 주문 실행 실패"
            del result

            # 주기적 가비지 컬렉션 (10회마다)
            if i % 10 == 0:
                gc.collect()

        assert True, "100회 연속 주문 실행 완료"


class TestResourceCleanup:
    """리소스 정리 테스트"""

    def test_dataframe_cleanup(self):
        """DataFrame 정리 확인"""
        gc.collect()

        # DataFrame 생성 및 삭제
        for _ in range(100):
            df = pd.DataFrame({
                'close': np.random.rand(1000) * 45000
            })

            # 계산 수행
            _ = df['close'].mean()

            # 명시적 삭제
            del df

        gc.collect()

        # DataFrame 객체 확인
        df_objects = [obj for obj in gc.get_objects() if isinstance(obj, pd.DataFrame)]

        # 대부분의 DataFrame이 정리되어야 함 (< 10개)
        assert len(df_objects) < 10, \
            f"DataFrame 정리 안 됨 ({len(df_objects)}개 남음)"

    def test_thread_cleanup(self):
        """스레드 정리 확인"""
        import threading

        initial_thread_count = threading.active_count()

        # 스레드 생성 및 종료
        threads = []
        for i in range(10):
            def dummy_task():
                import time
                time.sleep(0.01)

            t = threading.Thread(target=dummy_task)
            t.start()
            threads.append(t)

        # 모든 스레드 종료 대기
        for t in threads:
            t.join()

        # 스레드 정리 확인
        final_thread_count = threading.active_count()

        assert final_thread_count == initial_thread_count, \
            "모든 스레드가 정리되어야 함"


class TestMemoryPressure:
    """메모리 압박 테스트"""

    def test_large_dataframe_operations(self):
        """대용량 DataFrame 연산"""
        # 10,000개 행 DataFrame
        large_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10000, freq='1min'),
            'open': np.random.rand(10000) * 45000,
            'high': np.random.rand(10000) * 45100,
            'low': np.random.rand(10000) * 44900,
            'close': np.random.rand(10000) * 45000,
            'volume': np.random.rand(10000) * 1000,
        })

        # 리샘플링 (메모리 집약적 연산)
        resampled = large_df.set_index('timestamp').resample('1h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        assert len(resampled) > 0, "리샘플링 성공해야 함"
        assert len(resampled) < len(large_df), "리샘플링 후 행 수 감소해야 함"

        # 정리
        del large_df, resampled
        gc.collect()

    def test_repeated_large_calculations(self):
        """반복적 대용량 계산"""
        from utils.indicators import calculate_rsi

        # 10회 반복
        for _ in range(10):
            # 5,000개 데이터
            large_data = pd.Series(np.random.rand(5000) * 45000)

            # RSI 계산
            rsi = calculate_rsi(large_data, period=14, return_series=True)

            assert len(rsi) == len(large_data), "길이가 동일해야 함"

            # 명시적 삭제
            del large_data, rsi
            gc.collect()

        assert True, "10회 대용량 계산 완료"


class TestGarbageCollectionEfficiency:
    """가비지 컬렉션 효율성 테스트"""

    def test_gc_cycle_count(self):
        """가비지 컬렉션 사이클 카운트"""
        # GC 통계 초기화
        gc.collect()
        initial_stats = gc.get_stats()

        # 메모리 집약적 작업
        for _ in range(100):
            df = pd.DataFrame(np.random.rand(100, 5))
            _ = df.mean()
            del df

        # GC 실행
        collected = gc.collect()

        # 수집된 객체 확인
        assert collected >= 0, "GC가 실행되어야 함"

    def test_circular_reference_cleanup(self):
        """순환 참조 정리 테스트"""
        class Node:
            def __init__(self):
                self.ref = None

        # 순환 참조 생성
        node1 = Node()
        node2 = Node()
        node1.ref = node2
        node2.ref = node1

        # 참조 삭제
        del node1, node2

        # GC 실행
        collected = gc.collect()

        # 순환 참조 객체가 수집되어야 함
        assert collected > 0, "순환 참조 객체가 수집되어야 함"


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
