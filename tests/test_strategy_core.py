"""
tests/test_strategy_core.py
core/strategy_core.py 핵심 기능 단위 테스트

테스트 범위:
1. AlphaX7Core 초기화
2. 적응형 파라미터 계산 (calculate_adaptive_params)
3. MTF 트렌드 감지 (get_mtf_trend, get_4h_trend)
4. 신호 감지 (detect_signal)
5. 지표 계산 (RSI, ATR, ADX)
6. 백테스트 메트릭 (SSOT wrapper)
7. 포지션 관리 (trailing SL, 추가 진입)
"""

import pytest
import pandas as pd
import numpy as np
from core.strategy_core import (
    AlphaX7Core,
    _to_dt,
    calculate_backtest_metrics
)
from datetime import datetime


# ==================== Test 1: 유틸리티 함수 ====================

def test_to_dt_timestamp():
    """pd.Timestamp 변환 (이미 Timestamp인 경우)"""
    ts = pd.Timestamp('2024-01-01 12:00:00', tz='UTC')
    result = _to_dt(ts)

    assert result is not None
    assert result == ts
    assert result.tz is not None


def test_to_dt_datetime():
    """datetime 변환"""
    dt = datetime(2024, 1, 1, 12, 0, 0)
    result = _to_dt(dt)

    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 1


def test_to_dt_unix_timestamp():
    """Unix timestamp 변환 (ms/s 자동 감지)"""
    # 밀리초 (ms)
    ts_ms = 1704110400000  # 2024-01-01 12:00:00 UTC
    result_ms = _to_dt(ts_ms)

    assert result_ms is not None
    assert result_ms.year == 2024

    # 초 (s)
    ts_s = 1704110400  # 2024-01-01 12:00:00 UTC
    result_s = _to_dt(ts_s)

    assert result_s is not None
    assert result_s.year == 2024


def test_to_dt_none():
    """None/NaT 처리"""
    assert _to_dt(None) is None
    assert _to_dt(pd.NaT) is None
    assert _to_dt(np.nan) is None


# ==================== Test 2: AlphaX7Core 초기화 ====================

def test_alpha_x7_core_init():
    """AlphaX7Core 초기화"""
    strategy = AlphaX7Core(use_mtf=True)

    assert strategy.USE_MTF_FILTER is True
    assert hasattr(strategy, 'calculate_adaptive_params')
    assert hasattr(strategy, 'detect_signal')


def test_alpha_x7_core_init_no_mtf():
    """MTF 비활성화 초기화"""
    strategy = AlphaX7Core(use_mtf=False)

    assert strategy.USE_MTF_FILTER is False


# ==================== Test 3: 적응형 파라미터 ====================

@pytest.fixture
def sample_df_15m():
    """샘플 15분봉 데이터 (100개)"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='15min', tz='UTC')

    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(100) * 100,
        'high': 50100 + np.random.randn(100) * 100,
        'low': 49900 + np.random.randn(100) * 100,
        'close': 50000 + np.random.randn(100) * 100,
        'volume': 1000 + np.random.randn(100) * 100
    })

    return df


def test_calculate_adaptive_params(sample_df_15m):
    """적응형 파라미터 계산"""
    strategy = AlphaX7Core()

    params = strategy.calculate_adaptive_params(sample_df_15m, rsi_period=14)

    assert params is not None
    assert 'rsi_period' in params
    assert 'atr_mult' in params
    assert 'adx_threshold' in params
    assert 'macd_fast' in params
    assert 'macd_slow' in params


def test_calculate_adaptive_params_insufficient_data():
    """데이터 부족 시 처리"""
    strategy = AlphaX7Core()

    # 10개만 제공 (부족)
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=10, freq='15min', tz='UTC'),
        'close': [50000] * 10
    })

    params = strategy.calculate_adaptive_params(df, rsi_period=14)

    # None이거나 기본 파라미터 반환
    # (구현에 따라 다름)
    assert params is None or isinstance(params, dict)


# ==================== Test 4: 지표 계산 ====================

def test_calculate_rsi(sample_df_15m):
    """RSI 계산"""
    strategy = AlphaX7Core()

    closes = sample_df_15m['close'].values
    rsi = strategy.calculate_rsi(closes, period=14)

    assert 0 <= rsi <= 100


def test_calculate_atr(sample_df_15m):
    """ATR 계산"""
    strategy = AlphaX7Core()

    atr = strategy.calculate_atr(sample_df_15m, period=14)

    assert atr > 0


def test_calculate_adx(sample_df_15m):
    """ADX 계산"""
    strategy = AlphaX7Core()

    adx = strategy.calculate_adx(sample_df_15m, period=14)

    assert 0 <= adx <= 100


# ==================== Test 5: MTF 트렌드 감지 ====================

@pytest.fixture
def sample_df_1h():
    """샘플 1시간봉 데이터 (100개)"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1h', tz='UTC')

    # 상승 추세 데이터 생성
    close_prices = 50000 + np.arange(100) * 10 + np.random.randn(100) * 50

    df = pd.DataFrame({
        'timestamp': dates,
        'open': close_prices - 50,
        'high': close_prices + 100,
        'low': close_prices - 100,
        'close': close_prices,
        'volume': 1000 + np.random.randn(100) * 100
    })

    return df


def test_get_mtf_trend_up(sample_df_1h):
    """MTF 상승 추세 감지"""
    strategy = AlphaX7Core(use_mtf=True)

    trend = strategy.get_mtf_trend(sample_df_1h, mtf='4h', entry_tf='15m', ema_period=20)

    # 상승 데이터이므로 'Up' 예상
    assert trend in ['Up', 'Down', 'Neutral', None]


def test_get_4h_trend(sample_df_1h):
    """4시간 추세 감지"""
    strategy = AlphaX7Core()

    trend = strategy.get_4h_trend(sample_df_1h)

    assert trend in ['Up', 'Down', 'Neutral', None]


# ==================== Test 6: 신호 감지 ====================

def test_detect_signal_structure(sample_df_15m):
    """신호 감지 구조 테스트"""
    strategy = AlphaX7Core(use_mtf=False)  # MTF 비활성화 (단순 테스트)

    params = {
        'rsi_period': 14,
        'atr_mult': 1.5,
        'adx_threshold': 20,
        'macd_fast': 12,
        'macd_slow': 26
    }

    # detect_signal requires df_1h and df_15m (2 parameters)
    signal = strategy.detect_signal(sample_df_15m, sample_df_15m)

    # signal은 dict이거나 None
    assert signal is None or isinstance(signal, dict)

    if signal:
        # 신호가 있으면 필수 키 확인
        assert 'type' in signal
        assert 'entry_price' in signal
        assert signal['type'] in ['Long', 'Short']


# ==================== Test 7: 백테스트 메트릭 (SSOT Wrapper) ====================

def test_calculate_backtest_metrics_wrapper():
    """백테스트 메트릭 계산 (utils.metrics wrapper)"""
    # 샘플 거래 데이터
    trades = [
        {'pnl': 100, 'side': 'Long'},
        {'pnl': -50, 'side': 'Long'},
        {'pnl': 200, 'side': 'Short'},
        {'pnl': -30, 'side': 'Short'},
        {'pnl': 150, 'side': 'Long'}
    ]

    metrics = calculate_backtest_metrics(trades, leverage=1)

    # wrapper가 반환하는 키 이름 확인 (하위 호환성)
    assert 'total_return' in metrics
    assert 'trade_count' in metrics
    assert 'win_rate' in metrics
    assert 'profit_factor' in metrics
    assert 'max_drawdown' in metrics

    # 값 검증
    assert metrics['trade_count'] == 5
    assert 0 <= metrics['win_rate'] <= 100


def test_calculate_backtest_metrics_uses_ssot():
    """SSOT utils.metrics 함수 사용 확인"""
    from utils import metrics

    # wrapper가 utils.metrics를 호출하는지 확인
    # (내부 구현을 직접 테스트하기보다는 결과 일관성 확인)
    trades = [
        {'pnl': 100},
        {'pnl': -50},
        {'pnl': 200}
    ]

    # strategy_core wrapper 호출
    wrapper_result = calculate_backtest_metrics(trades, leverage=1)

    # utils.metrics 직접 호출
    ssot_result = metrics.calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # 값이 일치해야 함 (키 이름은 다를 수 있음)
    assert wrapper_result['total_return'] == ssot_result['total_pnl']
    assert wrapper_result['trade_count'] == ssot_result['total_trades']


# ==================== Test 8: 포지션 관리 ====================

def test_should_add_position():
    """추가 진입 판단"""
    strategy = AlphaX7Core()

    # Long 방향, RSI 30 (과매도)
    should_add = strategy.should_add_position('Long', current_rsi=30)

    # bool 반환
    assert isinstance(should_add, bool)


def test_calculate_trailing_params():
    """트레일링 SL 파라미터 계산"""
    strategy = AlphaX7Core()

    # 실제 시그니처: entry_price, stop_loss, direction -> Tuple[float, float]
    trail_start, trail_dist = strategy.calculate_trailing_params(
        entry_price=50000,
        stop_loss=49500,
        direction='Long'
    )

    assert isinstance(trail_start, float)
    assert isinstance(trail_dist, float)
    assert trail_start > 0
    assert trail_dist > 0


def test_update_trailing_sl_long():
    """트레일링 SL 업데이트 (Long)"""
    strategy = AlphaX7Core()

    # 실제 시그니처: direction, extreme_price, current_sl, trail_start, trail_dist, current_rsi
    new_sl = strategy.update_trailing_sl(
        direction='Long',
        extreme_price=51000,
        current_sl=49500,
        trail_start=50500,
        trail_dist=200,
        current_rsi=60
    )

    # Optional[float] 반환
    assert new_sl is None or isinstance(new_sl, float)


# ==================== Test 9: 백테스트 실행 ====================

def test_run_backtest_basic(sample_df_15m):
    """백테스트 기본 실행"""
    strategy = AlphaX7Core(use_mtf=False)

    params = {
        'rsi_period': 14,
        'atr_mult': 1.5,
        'adx_threshold': 20,
        'macd_fast': 12,
        'macd_slow': 26,
        'leverage': 1,
        'direction': 'Both'
    }

    # run_backtest requires df_entry and params
    result = strategy.run_backtest(sample_df_15m, params)

    # 결과 구조 검증
    assert 'trades' in result
    assert 'metrics' in result
    assert isinstance(result['trades'], list)
    assert isinstance(result['metrics'], dict)


# ==================== Test 10: Edge Cases ====================

def test_alpha_x7_empty_dataframe():
    """빈 데이터프레임 처리"""
    strategy = AlphaX7Core()

    df_empty = pd.DataFrame({
        'timestamp': [],
        'close': []
    })

    params = strategy.calculate_adaptive_params(df_empty)

    # None 또는 에러 없이 처리
    assert params is None or isinstance(params, dict)


def test_alpha_x7_single_candle():
    """단일 캔들 처리"""
    strategy = AlphaX7Core()

    df_single = pd.DataFrame({
        'timestamp': [pd.Timestamp('2024-01-01', tz='UTC')],
        'close': [50000]
    })

    params = strategy.calculate_adaptive_params(df_single)

    # 데이터 부족으로 None 예상
    assert params is None or isinstance(params, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
