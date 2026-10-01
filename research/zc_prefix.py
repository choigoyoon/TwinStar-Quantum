"""
ZC0부터 보는 그림 매칭 (접두 경로 매칭)

지금 시각 q에서 아는 것 = ZC0부터 q까지 그려진 경로. 이것을 과거 사건들의 'ZC0부터 같은 시간만큼의 경로'와 비교.
- 경로 = ZC0 봉 마감부터 1시간마다 종가 (ZC0 종가 기준, ZC0 시점 1h ATR로 나눔, 숏은 뒤집음) + 히스토그램 부호
- 기억 = q보다 먼저 ZC2가 끝나 그림(정답)이 정해진 사건만
- 그룹마다 점수 = 가까운 k개 중 그 그룹 비율 ÷ 기억 전체에서 그 그룹 비율 (1보다 크면 '닮음')
- 시점(체크포인트): ZC0+1h, ZC1 마감, 극점2 봉 마감, 극점2+3h, ZC2 마감
  ※ 체크포인트는 결과 정리용 구분이며, 매칭 입력은 언제나 q까지의 경로뿐
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import _macd_hist, find_windows

MAXH = 72
CHECKS = ('ZC0+1h', 'ZC1', '극점2', '극점2+3h', 'ZC2')


def paths(df5: pd.DataFrame) -> pd.DataFrame:
    """사건마다 ZC0 마감부터 MAXH시간 경로와 체크포인트까지의 경과 시간(시간)"""
    h = rd.resample(df5, '1h')
    w = find_windows(h)
    c = h['close'].to_numpy()
    hist = _macd_hist(h['close']).to_numpy()
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    rows = []
    for _, r in w.iterrows():
        z0, z1, z2, ib = int(r['zc0']), int(r['zc1']), int(r['zc2']), int(r['eb_bar'])
        d, at = float(r['dir']), atr[z0]
        if not np.isfinite(at) or at <= 0 or z0 + MAXH >= len(c):
            continue
        seg = slice(z0 + 1, z0 + 1 + MAXH)                    # ZC0 마감 뒤 1, 2, ... MAXH 시간째 마감
        rows.append({'zc0': h.index[z0], 'zc1': h.index[z1], 'dir': d, 'zc2': h.index[z2], 'zc2_close': h.index[z2] + pd.Timedelta(hours=1),
                     'px': ((c[seg] - c[z0]) * d / at).astype(np.float32),
                     'hs': (np.sign(hist[seg]) * d).astype(np.float32),
                     'ck': {'ZC0+1h': 1, 'ZC1': z1 - z0, '극점2': ib - z0, '극점2+3h': ib - z0 + 3, 'ZC2': z2 - z0}})
    return pd.DataFrame(rows)


def match(P: pd.DataFrame, labels: pd.Series, k: int = 50, min_mem: int = 300,
          hs_weight: float = 0.5) -> pd.DataFrame:
    """체크포인트마다 그룹 점수. 결과: 사건 × 체크포인트별 top1, top3 적중, '닮음' 그룹 수, 정답 그룹 점수"""
    groups = np.array(sorted(labels.dropna().unique()))
    lab = labels.to_numpy()
    X = np.vstack(P['px'].to_numpy())
    S = np.vstack(P['hs'].to_numpy())
    known = P['zc2_close'].to_numpy()
    start = P['zc0'].to_numpy()
    out = []
    for ck in CHECKS:
        L = np.array([min(max(c[ck], 1), MAXH) for c in P['ck']])
        for Lv in np.unique(L):
            qi = np.nonzero(L == Lv)[0]
            A = np.hstack([X[:, :Lv], hs_weight * S[:, :Lv]])
            for i in qi:
                tq = start[i] + pd.Timedelta(hours=int(Lv) + 1)   # 지금 시각 = ZC0 마감 + Lv시간
                mem = np.nonzero(known <= tq)[0]
                mem = mem[mem != i]
                if len(mem) < min_mem:
                    continue
                dist = np.sqrt(((A[mem] - A[i]) ** 2).mean(axis=1))
                nn = mem[np.argpartition(dist, k)[:k]]
                base = pd.Series(lab[mem]).value_counts(normalize=True)
                post = pd.Series(lab[nn]).value_counts(normalize=True).reindex(groups).fillna(0)
                lift = post / base.reindex(groups).fillna(np.inf)
                order = post.sort_values(ascending=False).index
                out.append({'idx': i, 'check': ck, 'hours': int(Lv), 'true': lab[i],
                            'top1': order[0] == lab[i], 'top3': lab[i] in set(order[:3]),
                            'n_like': int((lift > 1).sum()), 'true_lift': float(lift.get(lab[i], 0)),
                            'base_true': float(base.get(lab[i], 0))})
    return pd.DataFrame(out)


def summary(M: pd.DataFrame) -> pd.DataFrame:
    g = M.groupby('check', sort=False)
    return pd.DataFrame({'사건': g.size(), '시간(중앙)': g['hours'].median(), 'top1': g['top1'].mean(),
                         'top3': g['top3'].mean(), '닮음 그룹 수': g['n_like'].mean(),
                         '정답 그룹 배율(중앙)': g['true_lift'].median(), '찍기 top1': g['base_true'].mean()}).reindex(CHECKS)


MAXS = 36
SEGN = 12


def _rs(y: np.ndarray, n: int) -> np.ndarray:
    if len(y) == 1:
        return np.repeat(y, n)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)


def anchored(df5: pd.DataFrame, P: pd.DataFrame) -> np.ndarray:
    """
    ZC1 마감 뒤 s시간(s = 0..MAXS)마다, 그때까지 그려진 그림을 아틀라스 좌표로:
    ZC0 → 첫 극점 → ZC1 → 지금까지의 극점 → 지금, 구간마다 SEGN점, 세로 = (종가 - ZC1 시가) ÷ 지금까지 범위
    결과: [사건, s, 4*SEGN]. 모두 그 시각까지의 5분봉만 사용.
    """
    t5 = df5.index
    o5, h5, l5, c5 = (df5[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    H = pd.Timedelta(hours=1)
    out = np.full((len(P), MAXS + 1, 4 * SEGN), np.nan, dtype=np.float32)
    for n, (t0, t1, d) in enumerate(P[['zc0', 'zc1', 'dir']].itertuples(index=False)):
        # ZC0·ZC1 시각과 방향은 ZC1 봉 마감에 이미 알려짐
        a, m = t5.searchsorted(t0), t5.searchsorted(t1)
        hi, lo = (h5, l5) if d > 0 else (-l5, -h5)            # 숏은 뒤집어 롱처럼 (A 극점 = 최고)
        ea = a + int(np.argmax(hi[a:m]))
        for s in range(MAXS + 1):
            q = t5.searchsorted(t1 + H + s * H)               # q 직전 5분봉까지 앎
            if q > len(t5) or q <= m + 1:
                break
            eb = m + int(np.argmin(lo[m:q]))
            rng = max(h5[a:q].max() - l5[a:q].min(), 1e-9)
            y = (c5[a:q] - o5[m]) / rng * d
            cut = [0, ea - a, m - a, eb - a, q - a - 1]
            out[n, s] = np.concatenate([_rs(y[cut[i]:cut[i + 1] + 1], SEGN) for i in range(4)])
    return out


def match_anchored(P: pd.DataFrame, V: np.ndarray, labels: pd.Series, k: int = 50, min_mem: int = 300) -> pd.DataFrame:
    """ZC1 이후 체크포인트에서, ZC1 뒤 같은 시간의 과거 그림들과 비교"""
    groups = np.array(sorted(labels.unique()))
    lab = labels.to_numpy()
    known = P['zc2_close'].to_numpy()
    out = []
    for i, ck in enumerate(P['ck']):
        for name in CHECKS[1:]:
            s = int(min(max(ck[name] - ck['ZC1'], 0), MAXS))
            tq = P['zc0'].iat[i] + pd.Timedelta(hours=ck['ZC1'] + 1 + s)
            mem = np.nonzero(known <= tq)[0]
            mem = mem[mem != i]
            A = V[mem, s]
            ok = ~np.isnan(A).any(axis=1)
            mem, A = mem[ok], A[ok]
            if len(mem) < min_mem or np.isnan(V[i, s]).any():
                continue
            dist = np.sqrt(((A - V[i, s]) ** 2).mean(axis=1))
            nn = mem[np.argpartition(dist, k)[:k]]
            base = pd.Series(lab[mem]).value_counts(normalize=True)
            post = pd.Series(lab[nn]).value_counts(normalize=True).reindex(groups).fillna(0)
            lift = post / base.reindex(groups).fillna(np.inf)
            order = post.sort_values(ascending=False).index
            out.append({'idx': i, 'check': name, 'hours': s, 'true': lab[i], 'top1': order[0] == lab[i],
                        'top3': lab[i] in set(order[:3]), 'n_like': int((lift > 1).sum()),
                        'true_lift': float(lift.get(lab[i], 0)), 'base_true': float(base.get(lab[i], 0))})
    return pd.DataFrame(out)
