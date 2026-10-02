"""
계단 문제: "여기가 L/H인가" 대신 "지금이 이 하락 계단의 마지막 계단인가"

- 계단 = 바닥이 A 높이 10% 이상 더 내려갈 때마다 하나 (twin.lh 표본의 n_new). 마지막 계단 안의 작은 추가 하락은 같은 계단.
- prior_steps(): ZC1 마감 그림이 닮은 과거 사건(그 해 전에 끝난 것)들의 최종 계단 수 분포
- add_step_features(): 표본에 지금 계단 k, 기대 계단 수, "k가 마지막일 확률(사전)" 붙임
- 정답 표시 y_step = 지금 계단 == 최종 계단 (학습·평가에만)
"""

from typing import List

import numpy as np
import pandas as pd

P0 = ['aH_atr', 'aT', 'h1_now', 'mom1h', 'depth', 'h15', 'h5']
KMAX = 12


def final_steps(S: pd.DataFrame) -> pd.Series:
    return S[S['rel_lh'] == 0].set_index('ev')['n_new']


def zc1_picture(S: pd.DataFrame) -> pd.DataFrame:
    f = S.sort_values('bar').groupby('ev').first()
    f['aH_atr'] = f['bounce_atr'] / f['bounce_a'].replace(0, np.nan)
    f['aT'] = np.log(1 / f['elapsed'].replace(0, np.nan))
    return f


def prior_steps(S: pd.DataFrame, years: List[int], k: int = 50) -> pd.DataFrame:
    from sklearn.neighbors import NearestNeighbors
    K = final_steps(S)
    first = zc1_picture(S)
    out = []
    for y in years:
        y1, y2 = pd.Timestamp(f'{y}-01-01'), pd.Timestamp(f'{y + 1}-01-01')
        past = first[(first['zc2_close'] < y1) & first.index.isin(K.index)].dropna(subset=P0)
        cur = first[(first['t'] >= y1) & (first['t'] < y2)].dropna(subset=P0)
        if len(past) < k or cur.empty:
            continue
        mu, sd = past[P0].mean(), past[P0].std() + 1e-9
        nn = NearestNeighbors(n_neighbors=k).fit(((past[P0] - mu) / sd).to_numpy())
        _, idx = nn.kneighbors(((cur[P0] - mu) / sd).to_numpy())
        Kp = K.reindex(past.index).to_numpy()[idx]
        for e, row in zip(cur.index, Kp):
            out.append({'ev': e, 'K_med': float(np.median(row)),
                        **{f'pK_le{j}': float((row <= j).mean()) for j in range(KMAX)}})
    return pd.DataFrame(out).set_index('ev')


def add_step_features(S: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
    S = S.join(prior, on='ev')
    S = S[S['K_med'].notna()].copy()
    S['k'] = S['n_new']
    cdf = S[[f'pK_le{j}' for j in range(KMAX)]].to_numpy()
    kk = np.clip(S['k'].to_numpy().astype(int), 0, KMAX - 1)
    le = cdf[np.arange(len(S)), kk]
    le_prev = np.where(kk >= 1, cdf[np.arange(len(S)), np.maximum(kk - 1, 0)], 0.0)
    S['p_last_prior'] = le - le_prev
    S['p_beyond'] = 1 - le
    S['k_vs_med'] = S['k'] - S['K_med']
    return S
