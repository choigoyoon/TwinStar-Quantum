"""
tests/test_multi_symbol_signals.py
MultiSymbolBacktest 신호 변환: 방향/진입가/손절가가 실제 값으로 채워져야 한다
"""

import numpy as np
import pandas as pd

from core.multi_symbol_backtest import MultiSymbolBacktest


def _candles(n: int = 3000) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    close = 50000 * np.exp(np.cumsum(rng.normal(0, 0.006, n)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.003, n)) * close
    return pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='4h'),
        'open': open_, 'high': np.maximum(open_, close) + spread,
        'low': np.minimum(open_, close) - spread, 'close': close,
        'volume': rng.uniform(10, 100, n),
    })


def test_signals_have_prices_and_both_directions():
    bt = MultiSymbolBacktest(symbols=['BTCUSDT'], timeframes=['4h'])
    df = _candles()
    bt.all_candles['BTCUSDT_4h'] = df
    bt._volume_map = {'BTCUSDT': 1.0}

    signals = bt.extract_signals_from_symbol('BTCUSDT', '4h')
    assert len(signals) > 5
    assert {s.direction for s in signals} == {'Long', 'Short'}
    for s in signals:
        assert s.entry_price > 0 and s.atr > 0
        assert (s.sl_price < s.entry_price) if s.direction == 'Long' else (s.sl_price > s.entry_price)
        # 진입가는 신호 시각(확정 봉 마감 = 다음 봉 시작)에 열린 봉의 시가
        row = df[df['timestamp'] == pd.Timestamp(s.timestamp).tz_localize(None)]
        assert len(row) == 1 and row['open'].iloc[0] == s.entry_price
