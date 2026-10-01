"""
tests/test_trading_engine.py
trading/ 백테스트 엔진 실행 테스트 (ADX 컬럼 누락, timeframe 무시 회귀 방지)
"""

import numpy as np
import pandas as pd
import pytest

from trading import run_backtest


@pytest.fixture(scope='module')
def df_15m() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    n = 4000
    close = 50000 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.002, n)) * close
    return pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=n, freq='15min'),
        'open': open_, 'high': np.maximum(open_, close) + spread,
        'low': np.minimum(open_, close) - spread, 'close': close,
        'volume': rng.uniform(10, 100, n),
    })


@pytest.mark.parametrize('strategy', ['macd', 'adxdi'])
def test_run_backtest_executes(df_15m, strategy):
    result = run_backtest(df_15m.copy(), strategy=strategy, timeframe='1h')
    assert result.get('error') is None
    assert result['patterns_found'] > 0


def test_timeframe_is_applied(df_15m):
    p15 = run_backtest(df_15m.copy(), strategy='macd', timeframe='15m')['patterns_found']
    p1h = run_backtest(df_15m.copy(), strategy='macd', timeframe='1h')['patterns_found']
    assert p1h < p15
