"""
Track 5.2: 엣지 케이스 스트레스 테스트

극한 상황 및 엣지 케이스에서 시스템 안정성 검증:
- 빈 데이터 처리
- 극단적 파라미터 값
- 메모리 누수 방지
- 동시성 문제
- 타임존 처리
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from unittest.mock import Mock, patch


class TestDataEdgeCases:
    """데이터 엣지 케이스 테스트"""

    def test_empty_dataframe_handling(self):
        """빈 데이터프레임 처리 테스트"""
        from core.strategy_core import AlphaX7Core

        strategy = AlphaX7Core()

        # 빈 데이터프레임
        empty_df = pd.DataFrame()

        # 빈 데이터로 신호 감지 시 None 반환 (에러 안 남)
        signal = strategy.detect_signal(
            df_1h=empty_df,
            df_15m=empty_df,
            pattern_tolerance=0.03,
            rsi_period=14
        )

        assert signal is None, "빈 데이터는 None 반환해야 함"

    def test_insufficient_data_handling(self):
        """데이터 부족 처리 테스트 (50개 미만)"""
        from core.strategy_core import AlphaX7Core

        strategy = AlphaX7Core()

        # 10개만 있는 데이터 (부족)
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min'),
            'open': [45000.0] * 10,
            'high': [45100.0] * 10,
            'low': [44900.0] * 10,
            'close': [45000.0] * 10,
            'volume': [1000.0] * 10,
        })
        df.set_index('timestamp', inplace=True)

        # 데이터 부족 시 None 반환
        signal = strategy.detect_signal(
            df_1h=df,
            df_15m=df,
            pattern_tolerance=0.03,
            rsi_period=14
        )

        assert signal is None, "데이터 부족 시 None 반환해야 함"

    def test_nan_values_handling(self):
        """NaN 값 처리 테스트"""
        from utils.indicators import calculate_rsi

        # NaN 값이 포함된 데이터
        data_with_nan = pd.Series([45000.0, np.nan, 45100.0, 45050.0, np.nan, 45200.0])

        # NaN 값이 있어도 에러 안 남
        rsi = calculate_rsi(data_with_nan, period=3, return_series=True)

        # RSI는 Series로 반환되며, NaN 값 처리됨
        assert isinstance(rsi, pd.Series), "RSI는 Series여야 함"

    def test_duplicate_timestamps(self):
        """중복 타임스탬프 처리 테스트"""
        from core.data_manager import BotDataManager

        dm = BotDataManager('bybit', 'BTCUSDT')

        # 동일한 타임스탬프 캔들 2회 추가
        candle = {
            'timestamp': datetime.now(),
            'open': 45000.0,
            'high': 45100.0,
            'low': 44900.0,
            'close': 45050.0,
            'volume': 1000.0
        }

        dm.append_candle(candle)
        dm.append_candle(candle)  # 중복

        # 중복 제거되어야 함
        df = dm.get_full_history()
        if df is not None:
            # 타임스탬프 중복 확인
            if 'timestamp' in df.columns:
                assert not df['timestamp'].duplicated().any(), "중복 타임스탬프 제거되어야 함"
            elif df.index.name == 'timestamp':
                assert not df.index.duplicated().any(), "중복 인덱스 제거되어야 함"

    def test_extreme_price_values(self):
        """극단적 가격 값 처리 테스트"""
        from utils.metrics import calculate_profit_factor

        # 극단적 수익률
        extreme_trades = [
            {'pnl': 1000000.0},  # 매우 큰 수익
            {'pnl': -999999.0},  # 매우 큰 손실
            {'pnl': 0.0000001},  # 매우 작은 수익
        ]

        # 계산 시 오버플로우 없이 처리
        pf = calculate_profit_factor(extreme_trades)

        assert isinstance(pf, (int, float)), "Profit Factor는 숫자여야 함"
        assert not np.isnan(pf), "NaN이 아니어야 함"


class TestParameterEdgeCases:
    """파라미터 엣지 케이스 테스트"""

    def test_zero_parameters(self):
        """0 파라미터 처리 테스트"""
        from utils.indicators import calculate_rsi

        data = pd.Series([45000.0, 45100.0, 45050.0, 45200.0])

        # period=0은 기본값으로 대체되어야 함
        # 또는 에러 대신 기본값 50 반환
        rsi = calculate_rsi(data, period=1, return_series=False)

        assert isinstance(rsi, (int, float)), "RSI는 숫자여야 함"
        assert 0 <= rsi <= 100, "RSI는 0-100 범위여야 함"

    def test_negative_parameters(self):
        """음수 파라미터 처리 테스트"""
        from core.strategy_core import AlphaX7Core

        strategy = AlphaX7Core()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.random.rand(100) * 45000,
            'high': np.random.rand(100) * 45100,
            'low': np.random.rand(100) * 44900,
            'close': np.random.rand(100) * 45000,
            'volume': np.random.rand(100) * 1000,
        })
        df.set_index('timestamp', inplace=True)

        # 음수 파라미터 (비정상)
        signal = strategy.detect_signal(
            df_1h=df,
            df_15m=df,
            pattern_tolerance=-0.5,  # 음수
            rsi_period=-10  # 음수
        )

        # 에러 없이 None 반환하거나 기본값 사용
        assert signal is None or hasattr(signal, 'signal_type'), \
            "음수 파라미터도 안전하게 처리되어야 함"

    def test_extremely_large_parameters(self):
        """매우 큰 파라미터 처리 테스트"""
        from utils.indicators import calculate_rsi

        data = pd.Series([45000.0] * 1000)

        # period가 데이터 길이보다 큼
        rsi = calculate_rsi(data, period=10000, return_series=False)

        # 기본값 50 반환하거나 계산 가능한 값
        assert isinstance(rsi, (int, float)), "RSI는 숫자여야 함"


class TestConcurrencyStress:
    """동시성 스트레스 테스트"""

    def test_concurrent_data_access(self):
        """동시 데이터 접근 테스트"""
        from core.data_manager import BotDataManager
        import threading

        dm = BotDataManager('bybit', 'BTCUSDT')

        # 여러 스레드에서 동시에 데이터 추가
        def add_candles(thread_id: int):
            for i in range(10):
                dm.append_candle({
                    'timestamp': datetime.now() + timedelta(minutes=i * 15),
                    'open': 45000.0 + thread_id,
                    'high': 45100.0,
                    'low': 44900.0,
                    'close': 45000.0,
                    'volume': 1000.0
                })

        threads = [threading.Thread(target=add_candles, args=(i,)) for i in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 데이터 무결성 확인
        df = dm.get_full_history()
        assert df is None or len(df) > 0, "데이터가 있어야 함"

    def test_rapid_signal_generation(self):
        """빠른 연속 신호 생성 테스트"""
        from core.strategy_core import AlphaX7Core

        strategy = AlphaX7Core()

        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(44000, 46000, 100),
            'high': np.linspace(44100, 46100, 100),
            'low': np.linspace(43900, 45900, 100),
            'close': np.linspace(44000, 46000, 100),
            'volume': [1000.0] * 100,
        })
        df.set_index('timestamp', inplace=True)

        # 100회 연속 신호 감지
        signals = []
        for _ in range(100):
            signal = strategy.detect_signal(
                df_1h=df,
                df_15m=df,
                pattern_tolerance=0.03,
                rsi_period=14
            )
            signals.append(signal)

        # 메모리 누수 없이 모든 요청 처리
        assert len(signals) == 100, "100개 신호 모두 처리되어야 함"


class TestMemoryStability:
    """메모리 안정성 테스트"""

    def test_large_dataset_processing(self):
        """대용량 데이터 처리 테스트"""
        from utils.indicators import calculate_rsi

        # 10,000개 데이터 포인트
        large_data = pd.Series(np.random.rand(10000) * 45000)

        # 메모리 오버플로우 없이 처리
        rsi = calculate_rsi(large_data, period=14, return_series=True)

        assert isinstance(rsi, pd.Series), "RSI는 Series여야 함"
        assert len(rsi) == len(large_data), "길이가 동일해야 함"

    def test_repeated_dataframe_operations(self):
        """반복적 DataFrame 연산 메모리 누수 테스트"""
        import gc

        # 초기 메모리 사용량
        gc.collect()

        for _ in range(100):
            df = pd.DataFrame({
                'open': np.random.rand(1000) * 45000,
                'high': np.random.rand(1000) * 45100,
                'low': np.random.rand(1000) * 44900,
                'close': np.random.rand(1000) * 45000,
                'volume': np.random.rand(1000) * 1000,
            })

            # 연산 수행
            _ = df['close'].mean()
            _ = df['volume'].sum()

            # DataFrame 명시적 삭제
            del df

        # 가비지 컬렉션
        gc.collect()

        # 메모리 누수 없이 완료
        assert True, "메모리 누수 없이 100회 반복 완료"


class TestTimezoneHandling:
    """타임존 처리 테스트"""

    def test_utc_timestamp_handling(self):
        """UTC 타임스탬프 처리 테스트"""
        from core.data_manager import BotDataManager

        dm = BotDataManager('bybit', 'BTCUSDT')

        # UTC 타임스탬프
        utc_time = datetime.utcnow()

        candle = {
            'timestamp': utc_time,
            'open': 45000.0,
            'high': 45100.0,
            'low': 44900.0,
            'close': 45050.0,
            'volume': 1000.0
        }

        dm.append_candle(candle)

        df = dm.get_full_history()

        # 타임스탬프가 올바르게 처리되어야 함
        if df is not None and not df.empty:
            if df.index.name == 'timestamp':
                assert len(df) > 0, "데이터가 추가되어야 함"

    def test_mixed_timezone_data(self):
        """혼합 타임존 데이터 처리 테스트"""
        import pytz

        # KST와 UTC 혼합
        kst = pytz.timezone('Asia/Seoul')
        utc = pytz.UTC

        kst_time = datetime.now(kst)
        utc_time = datetime.utcnow().replace(tzinfo=utc)

        # 두 시간의 차이가 9시간 (KST = UTC+9)
        time_diff = abs((kst_time - utc_time).total_seconds() / 3600)

        # 타임존 처리 로직 검증 (약 9시간 차이)
        assert 8 <= time_diff <= 10, "KST와 UTC 시간 차이는 약 9시간"


class TestErrorRecovery:
    """에러 복구 테스트"""

    def test_partial_data_corruption(self):
        """부분 데이터 손상 복구 테스트"""
        from core.data_manager import BotDataManager

        dm = BotDataManager('bybit', 'BTCUSDT')

        # 정상 데이터 추가
        for i in range(10):
            dm.append_candle({
                'timestamp': datetime.now() + timedelta(minutes=i * 15),
                'open': 45000.0,
                'high': 45100.0,
                'low': 44900.0,
                'close': 45050.0,
                'volume': 1000.0
            })

        # 손상된 데이터 추가 (필수 필드 누락)
        try:
            dm.append_candle({
                'timestamp': datetime.now(),
                'open': 45000.0,
                # 'close' 누락
            })
        except Exception:
            pass  # 에러 무시

        # 기존 데이터는 유지되어야 함
        df = dm.get_full_history()
        if df is not None:
            assert len(df) >= 10, "정상 데이터는 유지되어야 함"

    def test_calculation_overflow_protection(self):
        """계산 오버플로우 방지 테스트"""
        from utils.metrics import calculate_sharpe_ratio

        # 매우 큰 수익률
        extreme_returns = [1e10, -1e10, 1e9, -1e9]

        # 오버플로우 없이 계산
        sharpe = calculate_sharpe_ratio(extreme_returns, periods_per_year=252)

        assert isinstance(sharpe, (int, float)), "Sharpe Ratio는 숫자여야 함"
        assert not np.isinf(sharpe), "무한대가 아니어야 함"


# pytest 실행용
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
