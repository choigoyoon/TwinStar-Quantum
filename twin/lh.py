"""
L/H 나오는 시점 인식 — 사건별(사례별) 장부

사건마다 ZC1 마감부터 ZC2 마감까지 5분봉 하나하나에서 묻는다:
    "지금까지 나온 바닥(숏이면 꼭지)이 이 파동의 진짜 L/H인가?"
단서는 그 5분봉 마감까지의 값과 ZC1 마감 때 아는 기준뿐. 정답(최종 L/H)은 학습 표시와 평가에만.

- samples(): 사건 × 5분봉 표본과 단서
- walk_forward(): 해마다 그 해 전에 ZC2가 끝난 사건만 배워 그 해 표본의 인식률(확률)을 냄
- ledger(): 사건마다 인식 기록 — L/H 전 최대 인식률(헛짚음), L/H 뒤 0·3·6·12봉 인식률, 처음 알아본 시점, 캔들 모양, 문턱별 결과
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from twin import data as rd
from twin.shape import raw_events

FEATURES: List[str] = [
    'bounce_atr',        # 지금 종가 - 지금까지 바닥 ÷ 1h ATR
    'bounce_a',          # 같은 거리 ÷ A 파동 높이
    'since_low',         # 바닥 뒤 지난 5분봉 수 ÷ 12 (시간)
    'since_frac',        # 바닥 뒤 시간 ÷ 구간 진행 시간
    'elapsed',           # 구간 진행 시간 ÷ A 구간 시간
    'depth',             # (A 극점 - 바닥) ÷ A 높이 (A를 얼마나 되돌렸나)
    'n_new',             # A 높이 10% 이상 더 내려간 새 바닥 횟수
    'low_body', 'low_wick_against', 'low_wick_with', 'low_vol',   # 바닥 봉 캔들: 몸통·아래꼬리·위꼬리 ÷ 봉 길이, 거래량 ÷ 구간 평균
    'cur_body', 'cur_wick_against', 'cur_dir',                    # 지금 봉 캔들: 몸통 비율, 아래꼬리 비율, 양/음
    'h5', 'h5_turned', 'h15', 'h15_turned', 'h1_now',             # 히스토그램 (반등 쪽 +), 바닥 뒤 반등 쪽으로 넘어갔나
    'mom1h', 'vol1h',    # 최근 1시간 움직임 ÷ ATR, 최근 1시간 거래량 ÷ 구간 평균
    # 지금 바닥 ↔ 직전 바닥 관계 (계단식 하락에서 진짜 바닥 가르기 — 다이버전스)
    'prev_drop_atr',     # 직전 바닥 - 지금 바닥 ÷ ATR (얼마나 더 내려왔나)
    'prev_gap_h',        # 직전 바닥과 지금 바닥 사이 시간
    'prev_rally_atr',    # 직전 바닥 뒤 반등이 최고로 간 거리 ÷ ATR (실패한 반등 크기)
    'div_m5', 'div_m15', 'div_h1',   # 지금 바닥 봉 히스토그램 ÷ 직전 바닥 봉 히스토그램 (1보다 작으면 힘 빠짐)
]
CANDLE = ('low_body', 'low_wick_against', 'low_wick_with', 'low_vol')
TAUS = (0.5, 0.6, 0.7, 0.8, 0.9)
GRACE = 12


def _atr_1h(df5: pd.DataFrame) -> pd.Series:
    h = rd.resample(df5, '1h')
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr.index = atr.index + pd.Timedelta(hours=1)                 # 마감 시각 기준
    return atr


def samples(df5: pd.DataFrame, step: int = 1) -> pd.DataFrame:
    t5 = df5.index
    atr = _atr_1h(df5)
    atr_t, atr_v = atr.index, atr.to_numpy()
    out = []
    for n, e in enumerate(raw_events(df5)):
        A0, M, N, p, d = e['A0'], e['M'], e['N'], e['p'], e['d']
        o, hi, lo, c, v = e['o'], e['hi'], e['lo'], e['c'], e['v']
        aH = hi[A0:M].max() - lo[A0:M].min()
        aT = M - A0
        if aH <= 0 or aT <= 0:
            continue
        hA1 = np.nanmax(np.abs(e['m1h'][A0:M])) or 1.0
        lh = M + int(np.argmin(lo[M:N]))
        final = lo[lh]
        run_v, run_i, n_new, last_new = np.inf, M, 0, None
        prev_i, cur_sig_i = None, None                            # 직전 의미 있는 바닥, 지금 의미 있는 바닥
        vsum = 0.0
        for i in range(M, N):
            if lo[i] < run_v:
                run_v, run_i = lo[i], i
                if last_new is None:
                    last_new, cur_sig_i = run_v, i
                elif last_new - run_v >= 0.1 * aH:               # A 높이 10% 이상 더 내려간 새 바닥
                    n_new += 1
                    last_new = run_v
                    prev_i, cur_sig_i = cur_sig_i, i
            vsum += v[i]
            if i < M + 11 or (i - M) % step:                     # ZC1 봉 마감(M+11 봉 마감) 뒤부터
                continue
            k = atr_t.searchsorted(t5[p + i] + pd.Timedelta(minutes=5), side='right') - 1
            at = atr_v[k] if k >= 0 else np.nan
            if not np.isfinite(at) or at <= 0:
                continue
            rng_l = max(hi[run_i] - lo[run_i], 1e-12)
            rng_c = max(hi[i] - lo[i], 1e-12)
            vm = vsum / (i - M + 1)
            m5s = e['m5'][run_i:i + 1]
            m15s = e['m15'][run_i:i + 1]
            def _div(x):
                a, b = x[run_i], x[prev_i] if prev_i is not None else np.nan
                return a / b if prev_i is not None and np.isfinite(a) and np.isfinite(b) and abs(b) > 1e-12 else np.nan
            rel = {'prev_drop_atr': (lo[prev_i] - run_v) / at if prev_i is not None else np.nan,
                   'prev_gap_h': (run_i - prev_i) / 12 if prev_i is not None else np.nan,
                   'prev_rally_atr': (hi[prev_i:run_i + 1].max() - lo[prev_i]) / at if prev_i is not None else np.nan,
                   'div_m5': _div(e['m5']), 'div_m15': _div(e['m15']), 'div_h1': _div(e['m1h'])}
            out.append({
                **rel,
                'ev': n, 'eid': e['zc2'].strftime('%Y-%m-%dT%H'), 'side': 'L' if d > 0 else 'H',
                't': t5[p + i] + pd.Timedelta(minutes=5), 'zc2_close': e['zc2_close'], 'bar': i, 'lh': lh,
                'rel_lh': i - lh,                                    # 0 = L/H 봉 마감
                'y': int(run_v <= final),                            # 지금 바닥이 진짜 L/H (평가·학습 표시)
                'bounce_atr': (c[i] - run_v) / at, 'bounce_a': (c[i] - run_v) / aH,
                'since_low': (i - run_i) / 12, 'since_frac': (i - run_i) / (i - M + 1), 'elapsed': (i - M + 1) / aT,
                'depth': (hi[A0:M].max() - run_v) / aH, 'n_new': n_new,
                'low_body': abs(c[run_i] - o[run_i]) / rng_l,
                'low_wick_against': (min(o[run_i], c[run_i]) - lo[run_i]) / rng_l,
                'low_wick_with': (hi[run_i] - max(o[run_i], c[run_i])) / rng_l,
                'low_vol': v[run_i] / max(vm, 1e-12),
                'cur_body': abs(c[i] - o[i]) / rng_c, 'cur_wick_against': (min(o[i], c[i]) - lo[i]) / rng_c,
                'cur_dir': float(np.sign(c[i] - o[i])),
                'h5': e['m5'][i] / at, 'h5_turned': float((m5s > 0).any()),
                'h15': e['m15'][i] / at if np.isfinite(e['m15'][i]) else np.nan,
                'h15_turned': float((m15s > 0).any()), 'h1_now': e['m1h'][i] / hA1,
                'mom1h': (c[i] - c[max(i - 12, 0)]) / at, 'vol1h': v[max(i - 11, 0):i + 1].mean() / max(vm, 1e-12),
                'atr': at, 'run_low': run_v, 'p_idx': p + i + 1, 'd': d,
            })
    return pd.DataFrame(out)


def walk_forward(S: pd.DataFrame, years: List[int], seed: int = 0) -> pd.Series:
    """해마다: 그 해 1월 1일 전에 ZC2가 끝난 사건의 표본만 배우고 그 해 표본의 인식률을 냄"""
    from sklearn.ensemble import HistGradientBoostingClassifier
    p = pd.Series(np.nan, index=S.index)
    for y in years:
        y1, y2 = pd.Timestamp(f'{y}-01-01'), pd.Timestamp(f'{y + 1}-01-01')
        tr = S['zc2_close'] < y1
        te = (S['t'] >= y1) & (S['t'] < y2)
        if tr.sum() < 5000 or not te.any():
            continue
        clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31,
                                             min_samples_leaf=100, l2_regularization=1.0, random_state=seed)
        clf.fit(S.loc[tr, FEATURES], S.loc[tr, 'y'])
        p[te] = clf.predict_proba(S.loc[te, FEATURES])[:, 1]
    return p


def ledger(S: pd.DataFrame, p: pd.Series) -> pd.DataFrame:
    """사건(사례)마다 인식 기록"""
    S = S.assign(p=p)[p.notna()]
    rows = []
    for ev, g in S.groupby('ev', sort=False):
        g = g.sort_values('bar')
        before, after = g[g['rel_lh'] < 0], g[g['rel_lh'] >= 0]
        at = lambda k: float(g.loc[g['rel_lh'] == k, 'p'].iloc[0]) if (g['rel_lh'] == k).any() else np.nan  # noqa: E731
        win = after[after['rel_lh'] <= GRACE]
        r = {'eid': g['eid'].iloc[0], 'side': g['side'].iloc[0], 'lh_time': g.loc[g['rel_lh'] >= 0, 't'].min(),
             'max_before': float(before['p'].max()) if len(before) else 0.0,
             'p_lh0': at(0), 'p_lh3': at(3), 'p_lh6': at(6), 'p_lh12': at(GRACE),
             'max_window': float(win['p'].max()) if len(win) else np.nan,
             **{k: float(after[k].iloc[0]) if len(after) else np.nan for k in CANDLE}}
        r['separable'] = bool(r['max_window'] > r['max_before']) if len(win) else False   # 이 사례만의 문턱이 존재
        for tau in TAUS:
            hit = g[g['p'] >= tau]
            first = int(hit['rel_lh'].iloc[0]) if len(hit) else None
            r[f'first_{tau}'] = first                           # 처음 알아본 시점 (L/H 기준 봉, 음수 = 헛짚음)
            r[f'ok_{tau}'] = first is not None and 0 <= first <= GRACE
        rows.append(r)
    return pd.DataFrame(rows)


CASE_KEYS = ('low_body', 'low_wick_against', 'low_wick_with', 'low_vol', 'depth', 'n_new', 'since_frac', 'elapsed')


def case_book(S: pd.DataFrame, p: pd.Series) -> pd.DataFrame:
    """
    사례 장부: 사건마다 L/H 봉 시점의 캔들 모양·맥락(CASE_KEYS)과 '이 사례에서 통했던 인식률 문턱'.
    tau_star = L/H 전 최대 인식률 바로 위 (헛짚지 않는 가장 낮은 문턱). L/H+12 안에 그 문턱을 넘었으면 usable.
    """
    S = S.assign(p=p)[p.notna()]
    at0 = S[S['rel_lh'] == 0].set_index('ev')
    rows = []
    for ev, g in S.groupby('ev', sort=False):
        if ev not in at0.index:
            continue
        before = g.loc[g['rel_lh'] < 0, 'p']
        win = g.loc[(g['rel_lh'] >= 0) & (g['rel_lh'] <= GRACE), 'p']
        tau = float(before.max()) + 1e-3 if len(before) else 0.0
        rows.append({'ev': ev, 'eid': g['eid'].iloc[0], 'zc2_close': g['zc2_close'].iloc[0], 'tau_star': tau,
                     'usable': bool(len(win) and win.max() >= tau), **{k: at0.at[ev, k] for k in CASE_KEYS}})
    return pd.DataFrame(rows)


def select_by_cases(S: pd.DataFrame, p: pd.Series, book: pd.DataFrame, years: List[int], k: int = 30) -> pd.Series:
    """
    선택형 문턱: 표본마다 '지금 바닥 봉의 캔들 모양·맥락'과 닮은 과거 사례 k개(그 해 전에 끝난 usable 사례)의
    tau_star 중앙값을 문턱으로 씀. 인식률 ≥ 문턱이면 '지금이 L/H' 선언. 돌려주는 값 = 표본별 문턱.
    """
    from sklearn.neighbors import NearestNeighbors
    th = pd.Series(np.nan, index=S.index)
    for y in years:
        y1, y2 = pd.Timestamp(f'{y}-01-01'), pd.Timestamp(f'{y + 1}-01-01')
        past = book[(book['zc2_close'] < y1) & book['usable']]
        te = (S['t'] >= y1) & (S['t'] < y2) & p.notna()
        if len(past) < k or not te.any():
            continue
        X = past[list(CASE_KEYS)].to_numpy(float)
        mu, sd = np.nanmean(X, 0), np.nanstd(X, 0) + 1e-9
        nn = NearestNeighbors(n_neighbors=k).fit(np.nan_to_num((X - mu) / sd))
        Q = np.nan_to_num((S.loc[te, list(CASE_KEYS)].to_numpy(float) - mu) / sd)
        _, idx = nn.kneighbors(Q)
        th[te] = np.median(past['tau_star'].to_numpy()[idx], axis=1)
    return th
