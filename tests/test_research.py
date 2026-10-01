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


def test_knn_memory_is_causal_and_pooled():
    from research.memory import knn_scores
    data = {'AAA': _ohlcv(n=2500), 'BBB': _ohlcv(n=2500, seed=2)}
    st = REGISTRY['knn_memory']
    rv.check_causal(data, st, {'k': 25, 'horizon': 6, 'threshold': 0.55}, n_cuts=3)

    scores = knn_scores(data, k=25, horizon=6, min_memory=300)
    s = scores['AAA']
    assert s['p_up'].notna().sum() > 1000
    # 두 심볼의 장면을 함께 기억 → 기억 크기가 한 심볼 길이보다 커짐
    assert s['n_memory'].max() > len(data['AAA'])


def test_knn_memory_learns_a_real_pattern():
    """다음 봉 방향이 특징(mom_1 부호)으로 정해지는 데이터에서는 기억이 그 규칙을 찾아야 한다"""
    from research.memory import knn_memory
    rng = np.random.default_rng(5)
    n = 4000
    r = np.zeros(n)
    for i in range(1, n):
        r[i] = 0.6 * r[i - 1] + rng.normal(0, 0.01)        # 강한 모멘텀(자기상관)
    close = 100 * np.exp(np.cumsum(r))
    idx = pd.date_range('2020-01-01', periods=n, freq='4h')
    df = pd.DataFrame({'open': np.r_[close[0], close[:-1]], 'close': close, 'volume': rng.uniform(10, 100, n)}, index=idx)
    df['high'] = df[['open', 'close']].max(axis=1) * 1.001
    df['low'] = df[['open', 'close']].min(axis=1) * 0.999
    sig = knn_memory({'X': df}, k=50, horizon=1, threshold=0.55, min_memory=500)['X']
    res = bt.run(df, sig, cost_per_side=0.0)
    assert bt.metrics(res).sharpe > 1.0


def test_knn_memory_never_uses_unfinished_outcomes():
    """봉마다 기억을 갱신할 때, 잘린 데이터와 전체 데이터의 기억 크기·판단값이 모든 컷에서 같아야 한다"""
    from research.memory import knn_scores
    data = {'AAA': _ohlcv(n=1500)}
    full = knn_scores(data, k=25, horizon=6, refresh='4h', min_memory=200)['AAA']
    idx = data['AAA'].index
    for k in range(1100, 1500, 37):
        cut = idx[k]
        part = knn_scores({'AAA': data['AAA'][idx < cut]}, k=25, horizon=6, refresh='4h', min_memory=200)['AAA']
        f = full[full.index < cut]
        assert (f['n_memory'].to_numpy() == part['n_memory'].to_numpy()).all()
        np.testing.assert_allclose(f['mean_ret'].to_numpy(), part['mean_ret'].to_numpy(), equal_nan=True)


def test_meta_filter_is_causal_on_data_edge():
    """신호 공간 기준으로 거래를 나눠야 데이터 끝에서 진입/건너뜀 판단이 바뀌지 않는다"""
    data = {'AAA': _ohlcv(n=1500), 'BBB': _ohlcv(n=1500, seed=3)}
    for name in ('meta_donchian', 'meta_ema_cross'):
        st = REGISTRY[name]
        rv.check_causal(data, st, {**st.grid[0], 'threshold': 0.5}, n_cuts=10)


def test_meta_filter_skips_only_low_success_trades():
    from research.meta import meta_filter
    data = {'AAA': _ohlcv(n=3000)}
    filt, T = meta_filter(data, 'ema_cross', {'fast': 10, 'slow': 50}, threshold=0.5, min_trades=20, return_scores=True)
    skipped = T[~T['taken']]
    assert len(skipped) > 0 and (skipped['p_success'] < 0.5).all()
    assert (T.loc[T['taken'] & T['p_success'].notna(), 'p_success'] >= 0.5).all()
    # 건너뛴 거래의 시작 봉 신호는 0
    for _, r in skipped.iterrows():
        assert filt['AAA'].iloc[int(r['sig_start'])] == 0


def test_plateau_neighbors():
    grid = [{'n': n, 'lo': lo} for n in (10, 20, 30) for lo in (False, True)]
    nb = rv._neighbors(grid)
    key = tuple(sorted({'n': 20, 'lo': False}.items()))
    assert sorted(dict(k)['n'] for k in nb[key] if dict(k)['lo'] is False) == [10, 30]
    assert any(dict(k) == {'n': 20, 'lo': True} for k in nb[key])
    assert len(nb[key]) == 3


def test_random_baseline_detects_skill():
    """미래를 아는 전략은 무작위보다 확실히 좋아야(p 작음) 하고, 무작위 전략은 p가 크게 나와야 한다"""
    df = _ohlcv(n=1500)
    data = {'AAA': df}
    future = np.sign(df['open'].shift(-2) / df['open'].shift(-1) - 1).fillna(0.0)   # 일부러 미래 사용
    good = {'AAA': bt.run(df, future, 0.0)}
    assert rv.random_baseline(good, data, n=100, cost=0.0)['p_value'] < 0.05
    noise = pd.Series(np.random.default_rng(9).choice([-1.0, 1.0], len(df)), index=df.index)
    bad = {'AAA': bt.run(df, noise, 0.0)}
    assert rv.random_baseline(bad, data, n=100, cost=0.0)['p_value'] > 0.05


def test_failure_report_runs():
    from research.diagnose import failure_report, trade_table
    df = _ohlcv(n=3000)
    parts = {'AAA': bt.run(df, REGISTRY['ema_cross'].fn(df, fast=10, slow=50))}
    rep = failure_report(trade_table(parts, {'AAA': df}))
    assert {'거래', '승률', '평균', '합계'} <= set(rep.columns)
    assert any(i.startswith('mom_24=') for i in rep.index)


def test_zc_windows_geometry():
    from research.zc_pattern import find_windows
    df = _ohlcv(n=1500, freq='1h')
    w = find_windows(df)
    assert len(w) > 20
    for _, r in w.sample(10, random_state=0).iterrows():
        a = df.iloc[int(r['zc0']):int(r['zc1'])]
        b = df.iloc[int(r['zc1']):int(r['zc2'])]
        if r['dir'] > 0:      # 구간 A 양 → A 고점, B 저점
            assert r['ea'] == a['high'].max() and r['eb'] == b['low'].min()
        else:
            assert r['ea'] == a['low'].min() and r['eb'] == b['high'].max()


def test_zc_learning_uses_only_finished_patterns():
    from research.zc_pattern import learn
    data = {'AAA': _ohlcv(n=2500, freq='1h'), 'BBB': _ohlcv(n=2500, freq='1h', seed=4)}
    W = learn(data, k=20, min_memory=30)
    bar = pd.Timedelta(hours=1)
    for i in W.index[W['p_success'].notna()][::25]:
        dt = W.at[i, 'decide_time'] + bar
        expected = int(((W['known_time'] <= dt) & W['known_time'].notna()).sum())
        assert W.at[i, 'n_memory'] <= expected     # 결과 확정 전 패턴은 기억에 없음
    st = REGISTRY['zc_memory']
    for p in st.grid[:2] + [{'k': 20, 'threshold': 0.5, 'exit': 12}]:
        rv.check_causal(data, st, p, n_cuts=6)


def test_zc_trade_simulation_stop_before_target():
    from research.zc_trades import _simulate
    hi = np.array([101.0, 103.0, 110.0])
    lo = np.array([99.0, 95.0, 100.0])
    op = np.array([100.0, 101.0, 102.0])
    # 둘째 봉에서 손절(96)과 목표(103)가 함께 닿음 → 손절 먼저
    ret, why, j = _simulate(1.0, 100.0, 96.0, 103.0, hi, lo, op, exit_open=108.0, cost=0.0)
    assert why == '손절' and j == 1 and ret == pytest.approx(-0.04)
    ret, why, _ = _simulate(1.0, 100.0, None, None, hi, lo, op, exit_open=108.0, cost=0.001)
    assert why == 'ZC3' and ret == pytest.approx(0.08 - 0.002)


def test_zc_ledger_entries_follow_zc2_close_and_rule_learning_is_causal():
    from research.zc_trades import RULES, run
    df = _ohlcv(n=8000, freq='15min')
    L = run({'AAA': df})
    assert len(L) > 20
    assert (L['entry_time'] > L['zc2']).all() and (L['exit_time'] > L['zc3']).all()
    for k in RULES:
        assert (L[f'known_{k}'] > L['entry_time']).all()
    # 학습 규칙: 각 건의 결정은 그 건 진입 시각까지 확정된 과거만 사용
    i = len(L) - 1
    t = L.at[i, 'entry_time']
    past = L[L['known_hold_zc3'] <= t]
    assert len(past) < len(L)


def test_zc_pictures_use_only_bars_up_to_zc2():
    from research.zc_cluster import pictures
    from research.zc_pattern import find_windows
    h = _ohlcv(n=1500, freq='1h')
    w = find_windows(h)
    P, T = pictures(h, w)
    assert P.shape == (len(w), 32) and T.shape == (len(w), 2)
    assert np.allclose(P[:, 0], 0.0)                         # 모든 그림은 ZC0 = 0에서 시작
    for j in range(5, len(w), max(1, len(w) // 8)):
        z2 = int(w.iloc[j]['zc2'])
        hc = h.iloc[:z2 + 1]                                 # ZC2 봉까지만 남김
        wc = find_windows(hc)
        Pc, _ = pictures(hc, wc)
        k = int(np.where(wc['zc2'].to_numpy() == z2)[0][0])
        np.testing.assert_allclose(Pc[k], P[j])


def test_zc_early_trigger_is_before_or_at_zc2_and_causal():
    from research.zc_early import _trigger
    from research.zc_pattern import _macd_hist, find_windows
    h = _ohlcv(n=1500, freq='1h')
    w = find_windows(h)
    hv = _macd_hist(h['close']).to_numpy()
    for _, r in w.head(40).iterrows():
        z1, z2 = int(r['zc1']), int(r['zc2'])
        for wt in (1, 3):
            j = _trigger(hv, z1, z2, wt)
            assert z1 < j <= z2 or j == z2
            if j < z2:   # 인식 봉까지만 있는 히스토그램으로도 같은 봉에서 인식
                hv_cut = _macd_hist(h['close'].iloc[:j + 1]).to_numpy()
                assert _trigger(hv_cut, z1, j + 1, wt) == j


def test_zc_policy_uses_only_known_same_group_outcomes():
    from research.zc_policy import ACTIONS, choose_actions
    t0 = pd.Timestamp('2024-01-01')
    rows = []
    for i in range(80):
        r = {'entry_time': t0 + pd.Timedelta(hours=i), 'group': i % 2}
        for a in ACTIONS:
            # 묶음 0의 stop_eb만 이익, 결과는 진입 10시간 뒤 확정
            r[f'r_{a}'] = 0.01 if (a == 'stop_eb' and i % 2 == 0) else -0.01
            r[f'known_{a}'] = r['entry_time'] + pd.Timedelta(hours=10)
        rows.append(r)
    P = choose_actions(pd.DataFrame(rows), min_n=5, shrink=0.0)
    g0, g1 = P[P['group'] == 0], P[P['group'] == 1]
    assert (g1['action'] == 'skip').all()                    # 다른 묶음의 이익은 빌려오지 않음
    first = g0.iloc[:8]                                      # 확정된 과거 5건이 쌓이기 전엔 건너뜀
    assert (first['action'] == 'skip').all()
    assert (g0.iloc[10:]['action'] == 'stop_eb').all()


def test_zc_catalog_signal_timing():
    from research.zc_catalog import BEHAVIORS, catalog
    df = _ohlcv(n=12000, freq='5min')
    C = catalog(df, settle=6)
    assert len(C) > 20 and set(C['behavior']) <= set(BEHAVIORS)
    H = pd.Timedelta(hours=1)
    assert (C['signal_time'] <= C['zc2'] + H).all()          # ZC2 마감 이전 또는 그때
    assert (C['entry_time'] >= C['signal_time']).all()       # 신호 봉 마감 뒤 시가 진입
    assert (C['exit_time'] > C['entry_time']).all()
