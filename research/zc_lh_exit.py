"""
L / H 학습기 2단계: 가격 모양 그대로 + 나가는 방법까지 배우기 (외부 자료 없이 5분봉만)

- RAW 특징: 최근 24개 5분봉 움직임, 최근 12개 마감된 1시간 히스토그램 (반등 쪽 +, ATR·극값으로 나눔)
- 나가는 방법 4가지: zc3(ZC3 마감), tp1/tp2(진입 ± 1·2 ATR 익절), trail1(최고점 - 1 ATR 따라가는 손절)
  모두 처음 손절은 '인식한 극점 - 0.1 ATR'. 한 봉 안에서 손절과 익절이 같이 닿으면 손절로 침 (보수적)
- nested(): 시험 해 Y마다
    1) Y-1년 전에 끝난 구간으로 나가는 방법별 기대수익을 배우고
    2) Y-1년에서 (나가는 방법, 문턱)을 고르고        ← Y년은 안 봄
    3) Y년 전에 끝난 구간 전부로 다시 배워 Y년에 그대로 적용
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from research.backtest import DEFAULT_COST_PER_SIDE
from research.zc_lh import FEATURES, MORE, STOP_ATR, _closed_tf, first_claims
from research.zc_pattern import _macd_hist

EXITS: Tuple[str, ...] = ('zc3', 'tp1', 'tp2', 'trail1')
RAW: List[str] = [f'r5_{k}' for k in range(24)] + [f'hh_{k}' for k in range(12)]
QUANTS = (0.90, 0.95, 0.98)


def _exit(o5, h5, l5, i0: int, end: int, d: float, stop: float, atr: float, how: str):
    """진입 o5[i0], 실제 가격 기준 stop. (청산가, 이유) 반환. end = 강제 청산 봉 (그 봉 시가)"""
    entry = o5[i0]
    if d > 0:
        hi, lo = h5[i0:end], l5[i0:end]
    else:                                                     # 숏은 뒤집어 롱처럼
        hi, lo, entry, stop = -l5[i0:end], -h5[i0:end], -entry, -stop
    op = o5[i0:end] * d
    n = len(lo)
    if how == 'trail1':
        prev_best = np.maximum.accumulate(np.r_[entry, hi[:-1]])     # 그 봉 전까지의 최고
        s = np.maximum(stop, prev_best - atr)
    else:
        s = np.full(n, stop)
    hs = np.nonzero(lo <= s)[0]
    k_s = hs[0] if len(hs) else n
    k_t = n
    if how in ('tp1', 'tp2'):
        tp = entry + (1.0 if how == 'tp1' else 2.0) * atr
        ht = np.nonzero(hi >= tp)[0]
        k_t = ht[0] if len(ht) else n
    if k_s < n and k_s <= k_t:
        return min(op[k_s], s[k_s]) * d, 'stop'
    if k_t < n:
        return max(op[k_t], tp) * d, 'tp'
    return o5[end], 'end'


def exit_labels(df5: pd.DataFrame, S: pd.DataFrame, cost: float = DEFAULT_COST_PER_SIDE,
                stop_atr: float = STOP_ATR) -> pd.DataFrame:
    """표본마다 나가는 방법별 '지금 들어갔다면' 비용 뒤 수익 (학습 정답용, ZC3까지의 미래 사용)"""
    o5, h5, l5 = (df5[k].to_numpy() for k in ('open', 'high', 'low'))
    out = {e: np.full(len(S), np.nan) for e in EXITS}
    for n, (i, e3, L, d, at) in enumerate(S[['i', 'e3', 'L', 'd', 'atr']].itertuples(index=False)):
        i0, e3 = int(i) + 1, int(e3)
        if i0 >= e3 or e3 >= len(o5):
            continue
        stop = (L - stop_atr * at) * d
        for e in EXITS:
            px, _ = _exit(o5, h5, l5, i0, e3, d, stop, at, e)
            out[e][n] = (px / o5[i0] - 1) * d - 2 * cost
    return pd.DataFrame({f'r_{e}': v for e, v in out.items()}, index=S.index)


def raw_features(df5: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    """최근 5분봉 24개 움직임과 마감된 1시간 히스토그램 12개 (표본 시각까지)"""
    c5 = df5['close'].to_numpy()
    i, d, at = S['i'].to_numpy(), S['d'].to_numpy(), S['atr'].to_numpy()
    out = {}
    for k in range(24):
        a, b = np.maximum(i - k - 1, 0), np.maximum(i - k, 0)
        out[f'r5_{k}'] = (c5[b] - c5[a]) * d / at
    h1 = _closed_tf(df5, '1h')
    hist = _macd_hist(h1['close']).to_numpy()
    kh = h1['close_time'].searchsorted(S['t'], side='right') - 1
    scale = np.array([np.abs(hist[max(x - 11, 0):x + 1]).max() if x >= 0 else np.nan for x in kh])
    for k in range(12):
        x = kh - k
        out[f'hh_{k}'] = np.where(x >= 0, hist[np.clip(x, 0, None)] * d, np.nan) / scale
    return pd.DataFrame(out, index=S.index)


def simulate(df5: pd.DataFrame, claims: pd.DataFrame, how: str, cost: float = DEFAULT_COST_PER_SIDE,
             stop_atr: float = STOP_ATR) -> pd.DataFrame:
    """인식 순서대로 한 포지션 매매. 다음 인식이 오면 그 전에 청산."""
    o5, h5, l5 = (df5[k].to_numpy() for k in ('open', 'high', 'low'))
    c = claims.sort_values('t').reset_index(drop=True)
    nxt = np.r_[c['i'].to_numpy()[1:] + 1, np.iinfo(np.int64).max]
    rows = []
    for j, r in c.iterrows():
        i0, d = int(r['i']) + 1, float(r['d'])
        end = int(min(r['e3'], nxt[j]))
        if i0 >= end or end >= len(o5):
            continue
        px, why = _exit(o5, h5, l5, i0, end, d, (r['L'] - stop_atr * r['atr']) * d, r['atr'], how)
        rows.append({'t': r['t'], 'side': '롱' if d > 0 else '숏', 'ret': (px / o5[i0] - 1) * d - 2 * cost,
                     'why': why, 'exit': how})
    return pd.DataFrame(rows)


def _fit(X: pd.DataFrame, y: pd.Series, seed: int = 0):
    from sklearn.ensemble import HistGradientBoostingRegressor
    lo, hi = y.quantile([0.01, 0.99])
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                         l2_regularization=1.0, random_state=seed).fit(X, y.clip(lo, hi))


def nested(df5: pd.DataFrame, S: pd.DataFrame, years: List[int], features: List[str],
           min_trades: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """시험 해마다 직전 해에서 (나가는 방법, 문턱)을 고르고 그해에 적용. (매매표, 고른 기록) 반환"""
    trades_all, picks = [], []
    for y in years:
        y0, y1, y2 = (pd.Timestamp(f'{v}-01-01') for v in (y - 1, y, y + 1))
        inner = S['e3_time'] < y0
        val = (S['t'] >= y0) & (S['t'] < y1) & (S['e3_time'] < y1)
        full = S['e3_time'] < y1
        test = (S['t'] >= y1) & (S['t'] < y2)
        best = None
        for e in EXITS:
            m = _fit(S.loc[inner, features], S.loc[inner, f'r_{e}'])
            pv = pd.Series(m.predict(S.loc[val, features]), index=S.index[val])
            ref = m.predict(S.loc[inner, features])
            for q in QUANTS:
                th = float(np.quantile(ref, q))
                V = S.loc[val]
                R = simulate(df5, first_claims(V, pv, th), e)
                if len(R) >= min_trades and (best is None or R['ret'].mean() > best[0]):
                    best = (R['ret'].mean(), e, q, len(R))
        if best is None:
            continue
        _, e, q, nv = best
        m = _fit(S.loc[full, features], S.loc[full, f'r_{e}'])
        th = float(np.quantile(m.predict(S.loc[full, features]), q))
        T = S.loc[test]
        pt = pd.Series(m.predict(T[features]), index=T.index)
        R = simulate(df5, first_claims(T, pt, th), e)
        R['year'] = y
        trades_all.append(R)
        picks.append({'year': y, 'exit': e, 'quantile': q, 'val_mean': best[0], 'val_n': nv,
                      'test_n': len(R), 'test_mean': R['ret'].mean() if len(R) else np.nan})
    return (pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame()), pd.DataFrame(picks)


ALL = FEATURES + MORE + RAW
