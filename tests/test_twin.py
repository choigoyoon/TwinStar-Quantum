"""
tests/test_twin.py
twin/ — 미래데이터 금지와 그림 JSON v2 계약 테스트
"""

import numpy as np
import pandas as pd
import pytest



def _ohlcv(n: int = 3000, freq: str = '4h', seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 30000 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.004, n)) * close
    idx = pd.date_range('2020-01-01', periods=n, freq=freq, name='timestamp')
    return pd.DataFrame({'open': open_, 'high': np.maximum(open_, close) + spread,
                         'low': np.minimum(open_, close) - spread, 'close': close,
                         'volume': rng.uniform(10, 100, n)}, index=idx)


from twin import data as rd


def test_zc_windows_geometry():
    from twin.zc import find_windows
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


def test_zc_atlas_vector_uses_only_bars_up_to_zc2():
    from twin.groups import atlas, SEG
    df5 = _ohlcv(n=12 * 1200, freq='5min', seed=3)
    A = atlas(df5)
    assert len(A) > 20 and all(len(v) == 4 * SEG for v in A['vec'])
    for j in range(3, len(A), max(1, len(A) // 6)):
        z2 = A.iloc[j]['zc2']
        cut = df5[df5.index < z2 + pd.Timedelta(hours=1)]       # ZC2 1시간봉 마감까지만 남김
        Ac = atlas(cut)
        k = int(np.where(Ac['zc2'].to_numpy() == z2)[0][0])
        np.testing.assert_allclose(Ac.iloc[k]['vec'], A.iloc[j]['vec'])


def test_zc_picture_classes_follow_fixed_cuts():
    from twin.groups import atlas, classify, CUTS, SEG
    A = classify(atlas(_ohlcv(n=12 * 1200, freq='5min', seed=3)))
    assert A['pic'].between(1, 27).all()
    X = np.vstack(A['vec'].to_numpy())
    lv = np.digitize(X[:, 3 * SEG - 1], CUTS['b'])
    assert ((A['pic'].to_numpy() - 1) // 3 % 3 == lv).all()     # 같은 B 깊이 → 같은 행


def test_zc_shape_v2_state_ignores_future_and_skeleton_order():
    import copy
    from twin.shape import raw_events, state, current_arrays, member_arrays, Memory, skeleton, CHANNELS
    legs = skeleton(np.array([0, 1, 2, 3, 2.2, 2.5, 4, 5, 3.5]), 0.5)
    assert ''.join(g['dir'] for g in legs) == 'UDUD'                       # 상승 → 눌림 → 재상승 → 꺾임
    df5 = _ohlcv(n=12 * 1500, freq='5min', seed=9)
    E = raw_events(df5)
    e = next(x for x in E if x['N'] - x['M'] > 60)
    q = e['M'] + 40
    a = current_arrays(state(e, q))
    e2 = copy.deepcopy(e)
    for k in ('o', 'hi', 'lo', 'c', 'v', 'm5', 'm15', 'm1h'):
        e2[k][q:] = e2[k][q:] * 3 + 7                                      # q 뒤 값을 바꿔도
    b = current_arrays(state(e2, q))
    for k in a:
        np.testing.assert_allclose(a[k], b[k])                             # 현재 그림은 그대로
    full = [state(x, x['N']) for x in E[:40]]
    mem = Memory([member_arrays(s) for s in full], ['G%d' % (i % 2) for i in range(40)])
    mem.fit_self([current_arrays(s) for s in full])
    sc = mem.score(mem.group_dist(mem.channel_dist(a)))
    assert set(sc['shape']) == {'G0', 'G1'} and sc[list(CHANNELS)].stack().between(0, 1).all()




def test_resample_labels_left_and_drops_incomplete():
    df5 = _ohlcv(n=12 * 5 + 7, freq='5min', seed=2)
    h = rd.resample(df5, '1h')
    assert (h.index == df5.index[:60:12]).all() and len(h) == 5                  # 덜 찬 마지막 시간봉은 버림
    np.testing.assert_allclose(h['close'].to_numpy(), df5['close'].to_numpy()[11:60:12])


def test_pipeline_library_replay_export_and_live(tmp_path, monkeypatch):
    from twin import pipeline as pl
    monkeypatch.setattr('twin.shape.MIN_GROUP', 1)                         # 작은 합성 데이터라 희귀 기준을 낮춤
    from twin.shape import state
    df5 = _ohlcv(n=12 * 1500, freq='5min', seed=10)
    lib = pl.Library(df5)
    assert len(lib.events) > 20 and set(lib.groups) <= {'P%02d' % k for k in range(1, 28)}
    R = lib.replay(5)
    assert R['deadline'].sum() == 1 and (R['rank'] >= 1).all()
    f = lib.form_similarity(5)
    assert -1 <= f['corr'] <= 1
    counts = lib.export(str(tmp_path))
    g = next(iter(counts))
    gj = __import__('json').loads((tmp_path / g / f'{g}.json').read_text())
    assert gj['n_events'] == counts[g] and len(gj['members']) == counts[g] and 'self_fit' in gj
    # 진행 중 구간: 어떤 시각 t까지만 잘라 만든 그림은 t 뒤 데이터와 무관
    t = df5.index[len(df5) * 3 // 4]
    ev = pl.live_event(df5[df5.index < t])
    if ev is not None and state(ev, ev['N']) is not None:
        df_mod = df5.copy()
        df_mod.loc[df_mod.index >= t, ['open', 'high', 'low', 'close']] *= 1.5
        ev2 = pl.live_event(df_mod[df_mod.index < t])
        a, b = state(ev, ev['N']), state(ev2, ev2['N'])
        np.testing.assert_allclose(a['skel'], b['skel'])


def test_rare_groups_are_not_ranked():
    from twin.shape import raw_events, state, member_arrays, current_arrays, Memory
    df5 = _ohlcv(n=12 * 1500, freq='5min', seed=9)
    full = [s for s in (state(x, x['N']) for x in raw_events(df5)[:45]) if s is not None]
    groups = ['BIG'] * (len(full) - 3) + ['TINY'] * 3
    mem = Memory([member_arrays(s) for s in full], groups)
    mem.fit_self([current_arrays(s) for s in full])
    sc = mem.score(mem.group_dist(mem.channel_dist(current_arrays(full[0]))))
    assert 'TINY' in mem.rare and list(sc['shape']) == ['BIG']               # 사건 몇 개뿐인 그룹이 1등을 차지하지 못함


def test_pct_wave_ignores_time_stretch_and_uses_percent():
    from twin.shape import stretch, PCT_G
    y = np.array([0.0, 1.0, 2.5, 1.2, 1.8, 3.0, 0.5])                    # 등하락 %
    slow = np.interp(np.linspace(0, 6, 37), np.arange(7), y)              # 같은 모양, 시간만 6배 (봉 수 6배)
    d = np.sqrt(np.mean((stretch(y) - stretch(slow)) ** 2))
    assert len(stretch(y)) == PCT_G and d < 0.05                          # 시간이 달라도 같은 그림으로 겹침
    assert np.sqrt(np.mean((stretch(y) - stretch(y * 3)) ** 2)) > 1.0       # 등하락 %가 다르면 다름 (값 정규화 없음)


def test_lh_samples_use_only_past_bars():
    from twin.lh import samples, FEATURES
    df5 = _ohlcv(n=12 * 1200, freq='5min', seed=11)
    S = samples(df5, step=3)
    assert len(S) > 100 and S['y'].isin([0, 1]).all()
    assert (S.loc[S['rel_lh'] >= 0, 'y'] == 1).all()                      # L/H 뒤는 언제나 정답 1
    cut = S['zc2_close'].iloc[len(S) // 2]
    Sc = samples(df5[df5.index < cut], step=3)
    a = S[S['zc2_close'] < cut].set_index(['eid', 'bar'])[FEATURES]
    b = Sc.set_index(['eid', 'bar'])[FEATURES].reindex(a.index)
    pd.testing.assert_frame_equal(a, b)                                    # 뒤 데이터를 지워도 단서 같음


def test_entry_eval_success_needs_after_lh_and_within_pct():
    from twin.lh import entry_eval
    S = pd.DataFrame({'ev': 0, 'eid': 'e', 't': pd.Timestamp('2024-01-01'), 'bar': [0, 1, 2, 3, 4],
                      'rel_lh': [-2, -1, 0, 1, 2], 'run_low': [105.0, 103.0, 100.0, 100.0, 100.0],
                      'p_idx': [1, 2, 3, 4, 5], 'd': 1.0})
    o = np.array([0, 106, 104, 100.5, 100.8, 102.0])                   # 봉3 선언 → 봉4 시가 100.8 (바닥 +0.8%)
    p = pd.Series([0.9, 0.1, 0.1, 0.9, 0.9])
    R = entry_eval(S, p, o, tau=0.8)                                   # 봉0 선언 → 바닥 깨짐(실패 1회) → 봉3 선언
    assert R['res'].iloc[0] == '성공' and R['fails'].iloc[0] == 1 and R['rel_lh'].iloc[0] == 1
    R2 = entry_eval(S, p, o, tau=0.8, retry=False)
    assert R2['res'].iloc[0] == '헛짚음'


def test_shuffled_days_keeps_bars_valid_and_breaks_order():
    df5 = _ohlcv(n=288 * 20, freq='5min', seed=12)
    f = rd.shuffled_days(df5)
    assert len(f) == len(df5) and (f['high'] >= f[['open', 'close']].max(axis=1)).all()
    assert (f['low'] <= f[['open', 'close']].min(axis=1)).all()
    r0, r1 = np.log(df5['close']).diff().dropna(), np.log(f['close']).diff().dropna()
    assert abs(r0.std() - r1.std()) / r0.std() < 0.1                     # 변동성 크기는 비슷
    assert not np.allclose(df5['close'].to_numpy(), f['close'].to_numpy())  # 순서는 바뀜


def test_lh_other_timeframe_events_and_multi_training():
    from twin.lh import samples, walk_forward
    df5 = _ohlcv(n=12 * 24 * 420, freq='5min', seed=13)                  # 2020~2021 (해를 넘겨야 연도별 학습)
    S1 = samples(df5, step=6)
    S15 = samples(df5, step=2, rule='15min')
    assert S15['ev'].nunique() > S1['ev'].nunique() and (S15['tf'] == '15min').all()
    yrs = sorted(S1['t'].dt.year.unique())[1:]
    p = walk_forward(S1, yrs, extra=[S15])
    assert p.notna().any() and p.dropna().between(0, 1).all()
