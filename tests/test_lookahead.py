"""
tests/test_lookahead.py
미래 데이터 누수(look-ahead bias) 회귀 테스트

원칙: 시각 T에 내린 판단은 T까지 '마감된' 봉만으로 똑같이 재현되어야 한다.
- timestamp는 봉 시작 시각이므로, 봉이 마감된 시각은 timestamp + 봉 길이
- 합성 랜덤워크 데이터 사용 (외부 데이터 불필요)
"""

import numpy as np
import pandas as pd
import pytest

import utils.indicators as ind
from core.strategy_core import AlphaX7Core

H = pd.Timedelta(hours=1)
M15 = pd.Timedelta(minutes=15)


@pytest.fixture(scope='module')
def df_15m() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n = 6000
    ts = pd.date_range('2025-01-01', periods=n, freq='15min')
    close = 50000 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.002, n)) * close
    return pd.DataFrame({
        'timestamp': ts,
        'open': open_,
        'high': np.maximum(open_, close) + spread,
        'low': np.minimum(open_, close) - spread,
        'close': close,
        'volume': rng.uniform(10, 100, n),
    })


@pytest.fixture(scope='module')
def df_1h(df_15m: pd.DataFrame) -> pd.DataFrame:
    return (df_15m.set_index('timestamp')
            .resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
            .dropna().reset_index())


@pytest.mark.parametrize('name, fn', [
    ('rsi', lambda d: ind.calculate_rsi(d['close'], 14, return_series=True)),
    ('atr', lambda d: ind.calculate_atr(d, 14, return_series=True)),
    ('macd_hist', lambda d: ind.calculate_macd(d['close'], return_all=True)[2]),
    ('ema', lambda d: ind.calculate_ema(d['close'], 20, return_series=True)),
    ('adx', lambda d: ind.calculate_adx(d, 14, return_series=True)),
])
def test_indicator_uses_only_past(df_15m, name, fn):
    """지표 값이 뒤에 오는 데이터에 따라 바뀌면 안 된다"""
    full = np.asarray(fn(df_15m), dtype=float)
    for k in (300, 1777, 4200):
        part = np.asarray(fn(df_15m.iloc[:k]), dtype=float)
        mask = ~(np.isnan(full[:k]) | np.isnan(part))
        np.testing.assert_allclose(full[:k][mask], part[mask], rtol=1e-9, atol=1e-9, err_msg=name)


@pytest.mark.parametrize('strategy_type', ['macd', 'adx'])
def test_signal_reproducible_from_closed_bars(df_1h, strategy_type):
    """신호 시각 T에 마감된 봉만 줘도 같은 신호가 나와야 한다"""
    core = AlphaX7Core(use_mtf=True, strategy_type=strategy_type)
    signals = core._extract_all_signals(df_1h, 0.05, 12.0)
    assert len(signals) > 10

    for sig in signals[::max(1, len(signals) // 25)]:
        t = pd.Timestamp(sig['time'])
        known = df_1h[df_1h['timestamp'] + H <= t].reset_index(drop=True)
        again = core._extract_all_signals(known, 0.05, 12.0)
        assert any(pd.Timestamp(s['time']) == t and s['type'] == sig['type'] for s in again), \
            f"{sig['type']} 신호({t})가 그 시각에 마감되지 않은 봉을 필요로 함"


def test_backtest_trades_unchanged_by_future_data(df_15m, df_1h):
    """컷오프 이전에 끝난 거래는 컷오프 이후 데이터 유무와 무관해야 한다"""
    entry = df_15m.copy()
    entry['timestamp'] = (entry['timestamp'] - pd.Timestamp('1970-01-01')) // pd.Timedelta(milliseconds=1)
    core = AlphaX7Core(use_mtf=True, strategy_type='macd')
    full = core.run_backtest(df_1h.copy(), entry.copy())
    assert len(full) > 10

    def key(t):
        return (pd.Timestamp(t['entry_time']), t['side'], round(t['entry_price'], 6),
                pd.Timestamp(t['exit_time']), round(t['exit_price'], 6))

    for frac in (0.4, 0.7):
        cut = df_15m['timestamp'].iloc[int(len(df_15m) * frac)]
        part = core.run_backtest(
            df_1h[df_1h['timestamp'] + H <= cut].copy(),
            entry[pd.to_datetime(entry['timestamp'], unit='ms') + M15 <= cut].copy(),
        )
        a = {key(t) for t in full if pd.Timestamp(t['exit_time']) < cut - H}
        b = {key(t) for t in part if pd.Timestamp(t['exit_time']) < cut - H}
        assert a == b


@pytest.mark.parametrize('strategy_name', ['macd', 'adxdi'])
def test_trading_strategy_patterns_use_only_closed_bars(df_15m, strategy_name):
    """trading/ 전략: 패턴 판단 봉(idx)까지의 데이터만으로 같은 패턴·진입가가 나와야 한다"""
    from trading.core.indicators import prepare_data
    from trading.strategies import get_strategy

    df = prepare_data(df_15m.copy(), None)
    # prepare_data는 ADX/DI를 만들지 않으므로 (전략이 요구) 직접 추가
    df['plus_di'], df['minus_di'], df['adx'] = ind.calculate_adx(df, 14, return_series=True, return_di=True)
    strat = get_strategy(strategy_name)
    patterns = strat.detect_patterns(df)
    assert len(patterns) > 5

    for p in patterns[::max(1, len(patterns) // 20)]:
        again = strat.detect_patterns(df.iloc[:p['idx'] + 1])
        assert any(q['idx'] == p['idx'] and q['direction'] == p['direction']
                   and q['entry_price'] == p['entry_price'] for q in again), \
            f"{strategy_name} {p['direction']} 패턴(idx={p['idx']})이 이후 봉을 필요로 함"
