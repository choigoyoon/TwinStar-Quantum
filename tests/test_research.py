"""
tests/test_research.py
research/ 분석 모듈: 체결 모델, 비용, 인과성 검사, 리샘플, 워크포워드
"""

import numpy as np
import pandas as pd
import pytest

from research import backtest as bt
from research import data as rd
from research import validate as rv
from research.strategies import REGISTRY, Strategy


def _ohlcv(n: int = 3000, freq: str = '4h', seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 30000 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.004, n)) * close
    idx = pd.date_range('2020-01-01', periods=n, freq=freq, name='timestamp')
    return pd.DataFrame({'open': open_, 'high': np.maximum(open_, close) + spread,
                         'low': np.minimum(open_, close) - spread, 'close': close,
                         'volume': rng.uniform(10, 100, n)}, index=idx)


def test_execution_is_next_bar_open_with_costs():
    idx = pd.date_range('2024-01-01', periods=4, freq='1D')
    df = pd.DataFrame({'open': [100, 110, 121, 121], 'high': 0, 'low': 0, 'close': 0, 'volume': 0}, index=idx, dtype=float)
    sig = pd.Series([1, 1, 0, 0], index=idx, dtype=float)   # 봉0 마감에 롱 결정, 봉1 마감에 유지, 봉2 마감에 청산
    r = bt.run(df, sig, cost_per_side=0.001)
    assert list(r['position']) == [0, 1, 1, 0]
    np.testing.assert_allclose(r['gross'], [0, 0.10, 0.0, 0])          # 봉1 시가 110 → 봉2 시가 121
    np.testing.assert_allclose(r['cost'], [0, 0.001, 0, 0.001])        # 진입·청산 편도 비용
    t = bt.trades(r)
    assert len(t) == 1 and t['side'].iloc[0] == 1


@pytest.mark.parametrize('name', list(REGISTRY))
def test_registered_strategies_are_causal(name):
    df = _ohlcv()
    st = REGISTRY[name]
    for p in st.grid:
        rv.check_causal(df, st, p)


def test_check_causal_catches_future_data():
    leaky = Strategy('leaky', lambda df: np.sign(df['close'].shift(-1) - df['close']).fillna(0.0), [{}])
    with pytest.raises(AssertionError):
        rv.check_causal(_ohlcv(), leaky, {})


def test_resample_labels_bar_start_and_drops_incomplete():
    df = _ohlcv(n=4 * 10 + 2, freq='15min')          # 1h봉 10개 + 미완성 15분봉 2개
    h = rd.resample(df, '1h')
    assert len(h) == 10
    assert h.index[0] == df.index[0]
    assert h['close'].iloc[0] == df['close'].iloc[3]   # 1h봉 종가 = 그 시간 마지막 15분봉 종가


def test_quality_flags_synthetic_data():
    df = _ohlcv()
    df['volume'] = 1000.0
    assert any('합성' in i for i in rd.check_quality(df).issues)
    assert not rd.check_quality(_ohlcv()).issues


def test_walk_forward_tests_only_after_training():
    df = _ohlcv(n=6 * 365 * 3)                         # 4h봉 3년
    data = {'AAA': df, 'BBB': _ohlcv(n=6 * 365 * 3, seed=2)}
    wf = rv.walk_forward(data, REGISTRY['donchian'], df.index[0], df.index[-1], train_months=12, test_months=6)
    assert len(wf.folds) >= 3
    for f in wf.folds:
        assert f.train_period[1] == f.test_period[0]
        assert f.result.index.min() >= f.test_period[0] and f.result.index.max() < f.test_period[1]
    assert wf.oos.index.is_monotonic_increasing
    assert np.isfinite(wf.metrics.sharpe)
