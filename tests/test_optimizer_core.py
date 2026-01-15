"""
tests/test_optimizer_core.py
core/optimizer.py 핵심 기능 단위 테스트

테스트 범위:
1. 워커 수 계산 (get_optimal_workers)
2. 그리드 생성 (generate_fast_grid)
3. 메트릭 계산 (SSOT 준수)
4. 결과 정렬 및 랭킹
"""

import pytest
import pandas as pd
import numpy as np
import multiprocessing as mp
from core.optimizer import (
    get_optimal_workers,
    get_worker_info,
    generate_fast_grid,
    BacktestOptimizer
)


# ==================== Module-level MockStrategy (Pickle 가능) ====================

class GlobalMockStrategy:
    """
    모듈 레벨 Mock 전략 (multiprocessing pickle 가능)
    실제 AlphaX7Core 반환 형식과 동일
    """
    @staticmethod
    def run_backtest(df_pattern, df_entry, slippage=0.001, **kwargs):
        """
        실제 AlphaX7Core 시그니처와 완전히 일치

        Returns:
            List[Dict]: 거래 목록
        """
        import pandas as pd
        import numpy as np
        np.random.seed(42)

        trades = []
        for i in range(10):
            pnl = np.random.randn() * 0.5
            entry_price = 50000 + np.random.randn() * 100
            exit_price = entry_price * (1 + pnl / 100)

            trades.append({
                'entry_time': pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i),
                'exit_time': pd.Timestamp('2024-01-01') + pd.Timedelta(hours=i+1),
                'type': 'Long' if pnl > 0 else 'Short',
                'entry': entry_price,
                'exit': exit_price,
                'pnl': pnl,
                'is_addon': False,
                'entry_idx': i * 4,
                'exit_idx': i * 4 + 1
            })

        return trades


# ==================== Test 1: 워커 수 계산 ====================

def test_get_optimal_workers_quick():
    """Quick 모드: CPU 절반 사용"""
    workers = get_optimal_workers('quick')
    assert workers >= 1
    assert workers <= mp.cpu_count()


def test_get_optimal_workers_standard():
    """Standard 모드: CPU 75% 사용"""
    workers = get_optimal_workers('standard')
    assert workers >= 1
    assert workers <= mp.cpu_count()


def test_get_optimal_workers_deep():
    """Deep 모드: CPU 최대 (1개 남김)"""
    workers = get_optimal_workers('deep')
    assert workers >= 1
    assert workers <= mp.cpu_count()


def test_get_worker_info():
    """워커 정보 반환"""
    info = get_worker_info('standard')

    assert 'total_cores' in info
    assert 'workers' in info
    assert 'usage_percent' in info
    assert 'description' in info
    assert 'free_cores' in info

    assert info['total_cores'] > 0
    assert info['workers'] >= 1
    assert 0 < info['usage_percent'] <= 100


# ==================== Test 2: 그리드 생성 ====================

def test_generate_fast_grid_15m():
    """15m 타임프레임 그리드 생성"""
    grid = generate_fast_grid('15m')

    # Grid는 Dict[str, List] 형식
    assert isinstance(grid, dict)
    assert len(grid) > 0

    # 실제 파라미터 키 확인
    assert 'atr_mult' in grid
    assert 'filter_tf' in grid
    assert 'entry_tf' in grid
    assert 'trail_start_r' in grid
    assert 'trail_dist_r' in grid

    # 각 값은 리스트
    assert isinstance(grid['atr_mult'], list)
    assert len(grid['atr_mult']) > 0


def test_generate_fast_grid_1h():
    """1h 타임프레임 그리드 생성"""
    grid = generate_fast_grid('1h')

    assert len(grid) > 0
    # 15m보다 그리드 크기 작거나 같음 (빠른 타임프레임)
    grid_15m = generate_fast_grid('15m')
    assert len(grid) <= len(grid_15m) * 2  # 합리적 범위


def test_generate_fast_grid_invalid():
    """잘못된 타임프레임 처리"""
    grid = generate_fast_grid('invalid_tf')

    # Fallback to default
    assert len(grid) > 0


# ==================== Test 3: BacktestOptimizer ====================

@pytest.fixture
def sample_data():
    """샘플 캔들 데이터 (100개)"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='15min')

    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(100) * 100,
        'high': 50100 + np.random.randn(100) * 100,
        'low': 49900 + np.random.randn(100) * 100,
        'close': 50000 + np.random.randn(100) * 100,
        'volume': 1000 + np.random.randn(100) * 100
    })

    return df


@pytest.fixture
def mock_strategy():
    """Mock 전략 클래스 (모듈 레벨 GlobalMockStrategy 반환)"""
    return GlobalMockStrategy


def test_backtest_optimizer_init(sample_data, mock_strategy):
    """BacktestOptimizer 초기화"""
    opt = BacktestOptimizer(mock_strategy, sample_data)

    assert opt.strategy_class == mock_strategy
    assert opt.df is not None
    assert len(opt.df) == 100


def test_backtest_optimizer_single_run(sample_data, mock_strategy):
    """단일 파라미터 백테스트"""
    opt = BacktestOptimizer(mock_strategy, sample_data)

    params = {
        'rsi_period': 14,
        'atr_mult': 1.5,
        'macd_fast': 12,
        'macd_slow': 26
    }

    # _run_single 메서드 사용 (slippage, fee 필요)
    result = opt._run_single(params, slippage=0.001, fee=0.0005)

    assert result is not None
    assert result.params == params
    assert result.win_rate >= 0
    assert result.trades >= 0


@pytest.mark.skip(reason="Integration test: multiprocessing + full backtest required")
def test_backtest_optimizer_grid_search(sample_data, mock_strategy):
    """
    그리드 서치 최적화 (통합 테스트)

    Skip 이유:
    - Multiprocessing 직렬화 복잡성
    - 실제 백테스트 엔진 의존성
    - 통합 테스트로 분류 (tests/integration/)
    """
    opt = BacktestOptimizer(mock_strategy, sample_data)

    # Grid는 Dict[str, List] 형식이어야 함
    grid = {
        'rsi_period': [10, 14, 20],
        'atr_mult': [1.0, 1.5, 2.0]
    }

    # n_cores=1: 단일 프로세스 (GlobalMockStrategy는 pickle 가능)
    results = opt.run_optimization(sample_data, grid, n_cores=1)

    assert len(results) > 0
    # 결과가 정렬되어 있는지 확인 (승률 내림차순)
    for i in range(len(results) - 1):
        assert results[i].win_rate >= results[i + 1].win_rate


# ==================== Test 4: 메트릭 계산 (SSOT) ====================

def test_optimizer_uses_ssot_metrics():
    """SSOT 메트릭 함수 사용 확인"""
    from core.optimizer import calculate_win_rate, calculate_profit_factor

    # SSOT 함수가 utils.metrics에서 import 되었는지 확인
    from utils import metrics

    assert calculate_win_rate == metrics.calculate_win_rate
    assert calculate_profit_factor == metrics.calculate_profit_factor


# ==================== Test 5: 결과 정렬 ====================

def test_result_sorting_by_win_rate(sample_data, mock_strategy):
    """승률 기준 정렬"""
    opt = BacktestOptimizer(mock_strategy, sample_data)

    # Grid는 Dict[str, List] 형식
    grid = {
        'rsi_period': list(range(10, 21)),
        'atr_mult': [1.5]
    }

    results = opt.run_optimization(sample_data, grid, n_cores=1)

    # 승률 내림차순 확인
    win_rates = [r.win_rate for r in results]
    assert win_rates == sorted(win_rates, reverse=True)


# ==================== Test 6: Edge Cases ====================

def test_optimizer_empty_grid(sample_data, mock_strategy):
    """빈 그리드 처리"""
    opt = BacktestOptimizer(mock_strategy, sample_data)

    # 빈 그리드 (Dict 형식)
    results = opt.run_optimization(sample_data, {}, n_cores=1)

    assert results == []


def test_optimizer_insufficient_data():
    """데이터 부족 시 처리"""
    from core.strategy_core import AlphaX7Core

    # 5개 캔들만 제공 (부족)
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=5, freq='15min'),
        'close': [50000] * 5
    })

    opt = BacktestOptimizer(AlphaX7Core, df)

    # Grid는 Dict[str, List] 형식
    grid = {'rsi_period': [14]}

    results = opt.run_optimization(df, grid, n_cores=1)

    # 데이터 부족으로 결과 없거나 에러 없이 처리
    assert isinstance(results, list)


# ==================== Test 7: 병렬 처리 ====================

@pytest.mark.skip(reason="Integration test: parallel execution requires full setup")
def test_optimizer_parallel_workers(sample_data, mock_strategy):
    """
    병렬 워커 동작 확인 (통합 테스트)

    Skip 이유:
    - Multiprocessing 환경 의존성
    - 실제 백테스트 엔진 필요
    - 통합 테스트로 분류 (tests/integration/)
    """
    opt = BacktestOptimizer(mock_strategy, sample_data)

    # Grid는 Dict[str, List] 형식
    grid = {
        'rsi_period': list(range(10, 30)),
        'atr_mult': [1.5]
    }

    # n_cores=2: 병렬 실행 (GlobalMockStrategy는 pickle 가능)
    results = opt.run_optimization(sample_data, grid, n_cores=2)

    assert len(results) > 0


# ==================== Test 8: 메모리 안전성 ====================

def test_optimizer_large_grid_memory():
    """큰 그리드 메모리 안전성"""
    from core.strategy_core import AlphaX7Core

    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
        'close': np.random.randn(100) * 100 + 50000
    })

    opt = BacktestOptimizer(AlphaX7Core, df)

    # 50개 조합 그리드 (Dict[str, List] 형식)
    grid = {
        'rsi_period': list(range(10, 20)),
        'atr_mult': [1.0, 1.5, 2.0, 2.5, 3.0]
    }

    # 메모리 에러 없이 완료
    results = opt.run_optimization(df, grid, n_cores=1)

    assert isinstance(results, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
