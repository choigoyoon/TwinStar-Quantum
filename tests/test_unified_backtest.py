"""
tests/test_unified_backtest.py
UnifiedBacktest: 과거 전체 구간의 거래가 생성되고, 단일 포지션 규칙으로 겹치지 않아야 한다
"""

import numpy as np
import pandas as pd

import core.unified_backtest as ub_mod
from core.unified_backtest import UnifiedBacktest


def _candles(seed: int, n: int = 6000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 50000 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.002, n)) * close
    ts = pd.date_range('2025-01-01', periods=n, freq='15min', tz='UTC')
    return pd.DataFrame({'open': open_, 'high': np.maximum(open_, close) + spread,
                         'low': np.minimum(open_, close) - spread, 'close': close,
                         'volume': rng.uniform(10, 100, n)}, index=pd.Index(ts, name='timestamp'))


def test_unified_backtest_generates_non_overlapping_trades(monkeypatch):
    data = {'AAAUSDT': _candles(1), 'BBBUSDT': _candles(2)}
    monkeypatch.setattr(ub_mod.MultiSymbolBacktest, 'load_candle_data',
                        lambda self, symbol, tf: data[symbol])
    ub = UnifiedBacktest()
    monkeypatch.setattr(ub, '_load_verified_presets', lambda: [
        {'symbol': s, 'exchange': 'bybit', 'params': {'atr_mult': 1.5}} for s in data])

    result = ub.run()
    assert result is not None and result.total_trades > 10
    log = result.trade_log
    assert {t['symbol'] for t in log} == set(data)
    for prev, cur in zip(log, log[1:]):
        assert cur['entry_time'] >= prev['exit_time']
