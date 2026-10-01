"""
L / H 실시간 인식 학습기

1h MACD 히스토그램의 한 구간(ZC1 → ZC2)이 진행되는 동안, 5분봉 마감마다 묻는다:
    "지금까지 이 구간에서 나온 최저점(롱 쪽이면 L, 숏 쪽이면 H)이 이 구간의 진짜 극점인가?"
정답 = 그 뒤 ZC2 마감까지 더 낮은 저점(H면 더 높은 고점)이 나오지 않음.

- 숏 쪽은 가격을 뒤집어 롱과 같은 식으로 계산 (모든 특징이 대칭)
- 특징은 그 5분봉 마감까지의 5분봉, 그때까지 마감된 1시간봉만 사용
- 학습은 해마다: 그해 1월 1일 전에 ZC3까지 끝난 구간만 배우고 그해를 맞힘
- 인식 = 구간 안에서 확률이 처음 문턱을 넘은 5분봉. 매매 = 그다음 5분봉 시가 진입,
  손절 = 인식한 극점 - 0.1 ATR, 청산 = ZC3 마감 (또는 다음 인식에서 뒤집기)
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from research import data as rd
from research.backtest import DEFAULT_COST_PER_SIDE
from research.zc_pattern import _macd_hist, find_windows

FEATURES: List[str] = [
    'depth',        # (A 극점 - 현재 극점) ÷ A 파동 크기 : A를 얼마나 되돌렸나 (1 넘으면 A 시작점 돌파)
    'bounce',       # (현재가 - 현재 극점) ÷ A 파동 크기 : 극점에서 얼마나 되돌아왔나
    'bounce_atr',   # 같은 거리 ÷ 1h ATR
    'since_h',      # 극점이 나온 뒤 지난 시간 (시간)
    'since_frac',   # 그 시간 ÷ 구간이 진행된 시간
    'elapsed',      # 구간 진행 시간 ÷ A 구간 길이
    'h1_now',       # 1h 히스토그램 현재값 ÷ 이번 구간 히스토그램 극값 (1 = 아직 극값, 0 = 곧 교차)
    'h1_since',     # 1h 히스토그램 극값 뒤 지난 시간
    'h1_div',       # 이번 구간 히스토그램 극값 ÷ A 구간 히스토그램 극값 (작으면 힘 빠짐)
    'h5',           # 5분 히스토그램 (반등 쪽 +) ÷ 1h ATR
    'h5_up',        # 극점 뒤 5분 히스토그램이 반등 쪽으로 넘어간 적 있나
    'mom1h',        # 최근 1시간 움직임 ÷ ATR (반등 쪽 +)
    'vol',          # 최근 1시간 거래량 ÷ 구간 평균 거래량
    'len_a',        # log(A 구간 시간)
    'atr_pct',      # ATR ÷ 가격
]
STOP_ATR = 0.1


def samples(df5: pd.DataFrame, step: int = 3) -> pd.DataFrame:
    """구간(세그먼트) × 5분봉 표본. 열: win, t(5분봉 마감 시각), FEATURES, y(정답), 매매용 값들"""
    h = rd.resample(df5, '1h')
    H, M5 = pd.Timedelta(hours=1), pd.Timedelta(minutes=5)
    w = find_windows(h)
    hist1 = _macd_hist(h['close']).to_numpy()
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr1 = tr.rolling(14).mean().to_numpy()
    t5 = df5.index
    o5, h5, l5, c5 = (df5[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    v5 = df5['volume'].to_numpy(dtype=float)
    hist5 = _macd_hist(df5['close']).to_numpy()
    hclose = h.index + H                                      # 1h 봉 마감 시각
    out = []
    for wi, r in w.iterrows():
        z0, z1, z2, z3 = int(r['zc0']), int(r['zc1']), int(r['zc2']), int(r['zc3'])
        if z3 < 0:
            continue
        d = float(r['dir'])                                   # A 부호. B는 반대 → B 극점이 d>0이면 저점(L)
        at = atr1[z1]
        if not np.isfinite(at) or at <= 0:
            continue
        a = t5.searchsorted(h.index[z0])
        m = t5.searchsorted(h.index[z1])
        s = t5.searchsorted(hclose[z1]) - 1                   # ZC1 봉 마감 = 구간 B가 알려진 첫 5분봉
        b = t5.searchsorted(hclose[z2])                       # ZC2 마감 다음 5분봉
        e3 = t5.searchsorted(hclose[z3])
        if e3 >= len(t5) or not (a < m <= s < b):
            continue
        if d > 0:
            lo, hi, cl, op = l5, h5, c5, o5
        else:
            lo, hi, cl, op = -h5, -l5, -c5, -o5
        a_hi, a_lo = hi[a:m].max(), lo[a:m].min()
        rng_a = a_hi - a_lo
        if rng_a <= 0:
            continue
        hm = -hist1 * d                                       # 구간 B 동안 양수
        hA = np.abs(hist1[z0:z1]).max()
        run = np.minimum.accumulate(lo[m:b])                  # 진행 중 극점
        final = run[-1]
        arg = np.zeros(b - m, int)                            # 극점이 나온 위치
        for k in range(1, b - m):
            arg[k] = k if lo[m + k] <= run[k - 1] else arg[k - 1]
        vm = np.cumsum(v5[m:b]) / np.arange(1, b - m + 1)
        for i in range(s, b, step):
            k = i - m
            L, jL = run[k], m + arg[k]
            kh = hclose.searchsorted(t5[i] + M5, side='right') - 1   # 마감된 마지막 1h 봉
            seg = hm[z1:kh + 1]
            hmax = seg.max() if len(seg) else np.nan
            h5s = hist5[jL:i + 1] * d
            out.append({
                'win': wi, 't': t5[i] + M5, 'zc2': h.index[z2], 'i': i,
                'depth': (a_hi - L) / rng_a,
                'bounce': (cl[i] - L) / rng_a,
                'bounce_atr': (cl[i] - L) / at,
                'since_h': (i - jL) / 12,
                'since_frac': (i - jL) / (k + 1),
                'elapsed': (k + 1) / (m - a),
                'h1_now': hm[kh] / hmax if hmax and hmax > 0 else np.nan,
                'h1_since': kh - (z1 + int(np.argmax(seg))) if len(seg) else np.nan,
                'h1_div': hmax / hA if hA > 0 else np.nan,
                'h5': hist5[i] * d / at,
                'h5_up': float((h5s > 0).any()),
                'mom1h': (cl[i] - cl[max(i - 12, 0)]) / at,
                'vol': v5[max(i - 11, 0):i + 1].mean() / vm[k] if vm[k] > 0 else np.nan,
                'len_a': np.log((m - a) / 12),
                'atr_pct': at / abs(c5[i]),
                'y': int(L <= final),
                'L': L, 'd': d, 'atr': at, 'e3': e3, 'e3_time': hclose[z3], 'final': final,
            })
    return pd.DataFrame(out)


def walk_forward(S: pd.DataFrame, years: List[int], seed: int = 0, target: str = 'y') -> pd.Series:
    """해마다: 그해 전에 ZC3까지 끝난 구간으로 배우고 그해 표본의 확률을 냄.
    target='y' → 극점 인식, target='r' → '지금 들어가면 비용 뒤 이익인가' (r > 0)"""
    from sklearn.ensemble import HistGradientBoostingClassifier
    p = pd.Series(np.nan, index=S.index)
    for y in years:
        start = pd.Timestamp(f'{y}-01-01')
        tr = S['e3_time'] < start
        te = (S['t'] >= start) & (S['t'] < pd.Timestamp(f'{y + 1}-01-01'))
        if tr.sum() < 1000 or te.sum() == 0:
            continue
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                             l2_regularization=1.0, random_state=seed)
        lab = S.loc[tr, 'y'] if target == 'y' else (S.loc[tr, target] > 0).astype(int)
        clf.fit(S.loc[tr, FEATURES], lab)
        p[te] = clf.predict_proba(S.loc[te, FEATURES])[:, 1]
    return p


def first_claims(S: pd.DataFrame, score: pd.Series, th: float) -> pd.DataFrame:
    """구간마다 점수가 처음 th 이상인 표본 (인식 시점)"""
    q = S.assign(score=score)
    q = q[q['score'] >= th]
    return q.sort_values('t').groupby('win', as_index=False).first()


def recognition(S: pd.DataFrame, claims: pd.DataFrame) -> Dict:
    """인식율(맞은 비율), 인식한 구간 비율, 진짜 극점 뒤 늦은 시간, 그때까지 되돌아온 거리"""
    n_win = S['win'].nunique()
    if claims.empty:
        return {'windows': n_win, 'claims': 0}
    return {'windows': n_win, 'claims': len(claims), 'coverage': len(claims) / n_win,
            'precision': claims['y'].mean(), 'late_h': claims['since_h'].median(),
            'bounce': claims['bounce'].median()}


def trades(df5: pd.DataFrame, claims: pd.DataFrame, cost: float = DEFAULT_COST_PER_SIDE,
           stop_atr: float = STOP_ATR) -> pd.DataFrame:
    """인식 → 다음 5분봉 시가 진입, 극점 - stop_atr·ATR 손절, ZC3 마감 청산. 다음 인식이 먼저 오면 그때 청산(한 포지션)."""
    o5, h5, l5 = (df5[k].to_numpy() for k in ('open', 'high', 'low'))
    c = claims.sort_values('t').reset_index(drop=True)
    nxt = np.r_[c['i'].to_numpy()[1:] + 1, np.iinfo(np.int64).max]
    rows = []
    for j, r in c.iterrows():
        i0, d = int(r['i']) + 1, float(r['d'])
        end = int(min(r['e3'], nxt[j]))
        if i0 >= end or end >= len(o5):
            continue
        entry = o5[i0]
        stop = (r['L'] - stop_atr * r['atr']) * d             # 실제 가격으로 되돌림
        lo, hi = l5[i0:end], h5[i0:end]
        hit = np.nonzero(lo <= stop)[0] if d > 0 else np.nonzero(hi >= stop)[0]
        if len(hit):
            k = hit[0]
            px = min(o5[i0 + k], stop) if d > 0 else max(o5[i0 + k], stop)   # 갭이면 시가
            how = 'stop'
        else:
            px, how = o5[end], 'zc3' if end == r['e3'] else 'flip'
        ret = (px / entry - 1) * d - 2 * cost
        rows.append({'t': r['t'], 'side': '롱' if d > 0 else '숏', 'y': r['y'], 'ret': ret, 'how': how,
                     'bars': (i0 + (hit[0] if len(hit) else end - i0)) - i0})
    return pd.DataFrame(rows)


def trade_labels(df5: pd.DataFrame, S: pd.DataFrame, cost: float = DEFAULT_COST_PER_SIDE,
                 stop_atr: float = STOP_ATR) -> pd.Series:
    """표본마다 '지금 인식하고 들어갔다면' 수익 (다음 5분봉 시가 진입, 극점-ATR 손절, ZC3 청산). 학습 정답용 — ZC3까지의 미래를 씀"""
    o5, h5, l5 = (df5[k].to_numpy() for k in ('open', 'high', 'low'))
    out = np.full(len(S), np.nan)
    for n, (i, e3, L, d, at) in enumerate(S[['i', 'e3', 'L', 'd', 'atr']].itertuples(index=False)):
        i0, e3 = int(i) + 1, int(e3)
        if i0 >= e3:
            continue
        entry, stop = o5[i0], (L - stop_atr * at) * d
        hit = np.nonzero(l5[i0:e3] <= stop)[0] if d > 0 else np.nonzero(h5[i0:e3] >= stop)[0]
        if len(hit):
            k = hit[0]
            px = min(o5[i0 + k], stop) if d > 0 else max(o5[i0 + k], stop)
        else:
            px = o5[e3]
        out[n] = (px / entry - 1) * d - 2 * cost
    return pd.Series(out, index=S.index, name='r')
