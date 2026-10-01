"""
실패에서 배우는 필터 (메타 학습)

기본 전략이 진입하려 할 때, '과거에 비슷한 상황에서 이 전략의 거래가 성공했나'를
기억에서 찾아 성공 확률이 낮으면 이번 진입을 건너뛴다.

- 학습 재료: 기본 전략의 과거 거래 (필터 전 원래 거래 전부 — 건너뛴 거래도 결과는 기록됨)
- 거래 결과는 청산이 확정된 뒤(청산 봉 다음 봉 마감)부터만 기억에 들어간다
- 특징: 진입 결정 봉의 상대값 + 방향, 표준화는 기억 안의 값으로만
- 여러 심볼이 기억을 공유
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from research import backtest as bt
from research.features import make_features


def _base_signals(data: Dict[str, pd.DataFrame], base: str, base_params: Dict) -> Dict[str, pd.Series]:
    from research.strategies import REGISTRY
    st = REGISTRY[base]
    return st.fn(data, **base_params) if st.pooled else {s: st.fn(d, **base_params) for s, d in data.items()}


def meta_filter(data: Dict[str, pd.DataFrame], base: str, base_params: Dict, k: int = 30,
                threshold: float = 0.5, min_trades: int = 40, cost: float = bt.DEFAULT_COST_PER_SIDE,
                return_scores: bool = False):
    """
    반환: {심볼: 필터된 신호} (return_scores면 거래별 p_success 표도 함께)
    threshold: 비슷한 과거 거래 중 성공 비율이 이 값 미만이면 건너뜀
    """
    sigs = _base_signals(data, base, base_params)

    # 1) 기본 전략의 거래 목록 (심볼 통합) — '신호 공간'에서 같은 방향 신호가 이어지는 구간 = 한 거래
    #    신호 구간 [a, b] → 포지션은 봉 a+1 ~ b+1 보유, 손익은 봉 b+2 시가에 확정
    rows = []
    for sym, df in data.items():
        sig = sigs[sym].reindex(df.index).fillna(0.0)
        res = bt.run(df, sig, cost)
        idx = df.index
        n = len(idx)
        bar = idx.to_series().diff().mode().iloc[0]
        side = np.sign(sig.to_numpy())
        net = res['net'].to_numpy()
        feats = make_features(df)
        a = 0
        while a < n:
            if side[a] == 0:
                a += 1
                continue
            b = a
            while b + 1 < n and side[b + 1] == side[a]:
                b += 1
            closed = b + 2 < n and b + 1 < n
            pnl = float(np.prod(1 + net[a + 1:b + 2]) - 1)
            rows.append({'symbol': sym, 'side': int(side[a]), 'sig_start': a, 'pnl': pnl,
                         'decide_time': idx[a] + bar,
                         'known_time': idx[b + 2] + bar if closed else pd.NaT,
                         **feats.iloc[a].to_dict()})
            a = b + 1
    out = {s: sigs[s].reindex(d.index).fillna(0.0).copy() for s, d in data.items()}
    if not rows:
        return (out, pd.DataFrame()) if return_scores else out
    T = pd.DataFrame(rows)
    feat_cols = list(make_features(next(iter(data.values())).iloc[:5]).columns) + ['side']
    T = T.sort_values('decide_time').reset_index(drop=True)

    known = T['known_time'].to_numpy(dtype='datetime64[ns]')
    X = T[feat_cols].to_numpy(dtype=float)
    win = (T['pnl'] > 0).to_numpy()
    p_success = np.full(len(T), np.nan)

    # 2) 각 진입 시점에 이미 결과가 확정된 과거 거래만으로 성공 확률 추정
    for i in range(len(T)):
        dt = np.datetime64(T.at[i, 'decide_time'])
        mem = (known <= dt) & ~np.isnan(X).any(axis=1)
        if mem.sum() < min_trades or np.isnan(X[i]).any():
            continue
        M = X[mem]
        mu, sd = M.mean(axis=0), M.std(axis=0)
        sd[sd == 0] = 1.0
        d = (((M - mu) / sd - (X[i] - mu) / sd) ** 2).sum(axis=1)
        kk = min(k, len(M))
        nn = np.argpartition(d, kk - 1)[:kk]
        p_success[i] = win[mem][nn].mean()

    # 3) 성공 확률이 낮은 거래 구간의 신호를 0으로
    T['p_success'] = p_success
    T['taken'] = ~(p_success < threshold)          # 기억이 부족하면(NaN) 그대로 진입
    # 신호 공간에서 '같은 방향 신호가 이어지는 구간'을 지운다 (포지션 공간의 청산 시점은
    #  다음 봉 데이터가 있어야 보이므로, 그걸 쓰면 데이터 끝에서 결과가 달라짐)
    for _, r in T[~T['taken']].iterrows():
        s = out[r['symbol']]
        base = sigs[r['symbol']].reindex(s.index).fillna(0.0).to_numpy()
        j = max(int(r['sig_start']), 0)
        while j < len(base) and np.sign(base[j]) == r['side']:
            s.iloc[j] = 0.0
            j += 1
    return (out, T) if return_scores else out
