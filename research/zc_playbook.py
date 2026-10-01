"""
상황별 매매법 고르기 (플레이북)

그림이 여러 개인 것처럼 매매법도 여러 개. ZC2 마감 순간의 그림(상황)마다 과거에 가장 잘 맞았던 매매법을 골라 씀.

매매법 = 들어가기 4가지 × 나가기 4가지 (+ 쉬기)
  들어가기 (모두 ZC2 마감 뒤, ZC3 마감 전까지만)
    follow : ZC2 마감 다음 5분봉 시가에 새 파동 방향       손절 = 둘째 극점(EB) - 0.1 ATR
    fade   : ZC2 마감 다음 5분봉 시가에 반대 방향           손절 = 진입가 + 1 ATR (반대쪽)
    pull   : 5분봉 종가가 ZC2 종가보다 0.5 ATR 되밀리면 새 파동 방향   손절 = EB - 0.1 ATR
    brk    : 5분봉 종가가 첫 극점(EA)을 넘으면 새 파동 방향           손절 = 진입가 - 1 ATR
  나가기: zc3 / tp1 / tp2 / trail1 (research.zc_lh_exit._exit 와 같음)
고르기 (해마다): 그해 전에 ZC3까지 끝난 사건만 보고, 상황마다 (수익 합 ÷ (건수 + shrink))가
가장 큰 매매법. 그 값이 0 이하이거나 건수가 min_n 미만이면 쉼.
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from research import data as rd
from research.backtest import DEFAULT_COST_PER_SIDE
from research.zc_lh_exit import EXITS, _exit
from research.zc_pattern import find_windows

ENTRIES = ('follow', 'fade', 'pull', 'brk')
METHODS: List[str] = [f'{e}_{x}' for e in ENTRIES for x in EXITS]
WORDS = {'follow': 'ZC2에서 따라가기', 'fade': 'ZC2에서 반대로', 'pull': '되돌림 뒤 따라가기', 'brk': '첫 극점 돌파 따라가기',
         'zc3': 'ZC3까지', 'tp1': '1ATR 익절', 'tp2': '2ATR 익절', 'trail1': '따라가는 손절'}


def method_returns(df5: pd.DataFrame, cost: float = DEFAULT_COST_PER_SIDE) -> pd.DataFrame:
    """ZC3까지 끝난 사건마다 16가지 매매법의 비용 뒤 수익 (진입이 안 생기면 NaN = 매매 없음)"""
    h = rd.resample(df5, '1h')
    H = pd.Timedelta(hours=1)
    w = find_windows(h)
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr1 = tr.rolling(14).mean().to_numpy()
    t5 = df5.index
    o5, h5, l5, c5 = (df5[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    rows = []
    for _, r in w.iterrows():
        z1, z2, z3 = int(r['zc1']), int(r['zc2']), int(r['zc3'])
        if z3 < 0:
            continue
        d, at = float(r['dir']), atr1[z2]
        if not np.isfinite(at) or at <= 0:
            continue
        m = t5.searchsorted(h.index[z1])
        b = t5.searchsorted(h.index[z2] + H)                  # ZC2 마감 다음 5분봉
        e = t5.searchsorted(h.index[z3] + H)                  # ZC3 마감 다음 5분봉 = 강제 청산
        if e >= len(t5) or not (m < b < e):
            continue
        eb = l5[m:b].min() if d > 0 else h5[m:b].max()
        ea = float(r['ea'])
        p2 = c5[b - 1]
        row = {'zc2': h.index[z2], 'zc3_time': h.index[z3] + H, 'd': d}
        x = (c5[b:e] - p2) * d / at                            # ZC2 뒤 종가 움직임 (새 파동 쪽 +)
        k_pull = np.nonzero(x <= -0.5)[0]
        k_brk = np.nonzero((c5[b:e] - ea) * d > 0)[0]
        plans = {
            'follow': (b, d, eb - 0.1 * at * d),
            'fade': (b, -d, o5[b] + at * d),
            'pull': (b + k_pull[0] + 1, d, eb - 0.1 * at * d) if len(k_pull) else None,
            'brk': (b + k_brk[0] + 1, d, None) if len(k_brk) else None,
        }
        for en, plan in plans.items():
            for ex in EXITS:
                key = f'{en}_{ex}'
                if plan is None or plan[0] >= e:
                    row[key] = np.nan
                    continue
                i0, dd, stop = plan
                if stop is None:
                    stop = o5[i0] - at * dd
                if (o5[i0] - stop) * dd <= 0:                  # 이미 손절선 밖에서 시작 → 매매 안 함
                    row[key] = np.nan
                    continue
                px, _ = _exit(o5, h5, l5, i0, e, dd, stop, at, ex)
                row[key] = (px / o5[i0] - 1) * dd - 2 * cost
        rows.append(row)
    return pd.DataFrame(rows)


def choose(hist: pd.DataFrame, key: str, shrink: float = 20.0, min_n: int = 20) -> Dict:
    """상황(key 열)마다 고른 매매법. hist = 결과를 이미 아는 사건들"""
    out = {}
    for s, g in hist.groupby(key):
        best = (0.0, None, 0)
        for mth in METHODS:
            v = g[mth].dropna()
            if len(v) < min_n:
                continue
            score = v.sum() / (len(v) + shrink)
            if score > best[0]:
                best = (score, mth, len(v))
        out[s] = best[1]
    return out


def run(P: pd.DataFrame, key: str, years: List[int], **kw) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """해마다 고르고 적용. (매매표, 고른 표) 반환. P = method_returns + 상황 열"""
    trades, picks = [], []
    for y in years:
        y1, y2 = pd.Timestamp(f'{y}-01-01'), pd.Timestamp(f'{y + 1}-01-01')
        plan = choose(P[P['zc3_time'] < y1], key, **kw)
        T = P[(P['zc2'] >= y1) & (P['zc2'] < y2)]
        for s, mth in plan.items():
            picks.append({'year': y, key: s, 'method': mth})
        for _, r in T.iterrows():
            mth = plan.get(r[key])
            if mth is None or not np.isfinite(r[mth]):
                continue
            trades.append({'year': y, 'zc2': r['zc2'], key: r[key], 'method': mth, 'ret': r[mth]})
    return pd.DataFrame(trades), pd.DataFrame(picks)


CONTEXT = ['h4', 'd1', 'ema50', 'atr_pct', 'side', 'bars5']


def context(df5: pd.DataFrame, P: pd.DataFrame, A: pd.DataFrame) -> pd.DataFrame:
    """ZC2 마감 시각까지 마감된 봉으로 만든 상황 특징 + 아틀라스 그림 48점 (모두 ZC2 마감까지)"""
    from research.zc_lh import _closed_tf
    from research.zc_pattern import _macd_hist
    t = P['zc2'] + pd.Timedelta(hours=1)
    d = P['d'].to_numpy()

    def last(g, col):
        k = g['close_time'].searchsorted(t, side='right') - 1
        return np.where(k >= 0, col.to_numpy()[np.clip(k, 0, None)], np.nan)

    h1 = _closed_tf(df5, '1h')
    tr = pd.concat([h1['high'] - h1['low'], (h1['high'] - h1['close'].shift()).abs(),
                    (h1['low'] - h1['close'].shift()).abs()], axis=1).max(axis=1).rolling(14).mean()
    at = last(h1, tr)
    m4, dd = _closed_tf(df5, '4h'), _closed_tf(df5, '24h')
    X = pd.DataFrame(index=P.index)
    X['h4'] = last(m4, _macd_hist(m4['close'])) * d / at
    X['d1'] = last(dd, dd['close'] - dd['close'].ewm(span=20, adjust=False).mean()) * d / at
    X['ema50'] = (last(h1, h1['close']) - last(h1, h1['close'].ewm(span=50, adjust=False).mean())) * d / at
    X['atr_pct'] = at / last(h1, h1['close'])
    X['side'] = d
    V = A.set_index('zc2').reindex(P['zc2'])
    X['bars5'] = np.log(V['bars5'].to_numpy(dtype=float))
    vec = np.vstack(V['vec'].to_numpy())
    for k in range(vec.shape[1]):
        X[f'v{k}'] = vec[:, k]
    return X


def run_model(P: pd.DataFrame, X: pd.DataFrame, years: List[int], margin: float = 0.0,
              seed: int = 0) -> pd.DataFrame:
    """매매법마다 기대수익을 배우고(그해 전에 끝난 사건만), 가장 큰 매매법이 margin보다 크면 그것으로 매매"""
    from sklearn.ensemble import HistGradientBoostingRegressor
    out = []
    for y in years:
        y1, y2 = pd.Timestamp(f'{y}-01-01'), pd.Timestamp(f'{y + 1}-01-01')
        tr = (P['zc3_time'] < y1).to_numpy()
        te = ((P['zc2'] >= y1) & (P['zc2'] < y2)).to_numpy()
        if tr.sum() < 300 or not te.any():
            continue
        pred = {}
        for mth in METHODS:
            ok = tr & P[mth].notna().to_numpy()
            yv = P.loc[ok, mth]
            lo, hi = yv.quantile([0.01, 0.99])
            mdl = HistGradientBoostingRegressor(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                                min_samples_leaf=40, l2_regularization=1.0, random_state=seed)
            mdl.fit(X[ok], yv.clip(lo, hi))
            pred[mth] = mdl.predict(X[te])
        Pm = pd.DataFrame(pred, index=P.index[te])
        best = Pm.idxmax(axis=1)
        for i, mth in best.items():
            if Pm.at[i, mth] <= margin or not np.isfinite(P.at[i, mth]):
                continue
            out.append({'year': y, 'zc2': P.at[i, 'zc2'], 'method': mth, 'pred': Pm.at[i, mth], 'ret': P.at[i, mth]})
    return pd.DataFrame(out)
