"""
상대값 기억 학습기 (k-최근접 장면)

1. 매 봉마다 상대값 특징(features.make_features)으로 '장면'을 기록한다.
2. 장면의 결과(horizon봉 뒤 수익)는 결과가 확정된 뒤에만 기억에 넣는다.
     장면 j의 결과(봉 j+1 시가→봉 j+1+horizon 시가)는 봉 j+1+horizon 마감 이후 판단에서만 사용
3. 새 장면이 오면 기억에서 가장 비슷한 k개를 찾고, 그중 오른 비율로 판단한다.
4. 기억은 refresh 주기마다 갱신되고(그 사이엔 고정), 특징 표준화도 기억 안의 값으로만 한다.
5. 여러 심볼은 한 기억을 공유한다 (상대값이므로 비교 가능).
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from research.features import FEATURES, forward_return, make_features


def _bar(index: pd.DatetimeIndex) -> pd.Timedelta:
    return index.to_series().diff().mode().iloc[0]


def knn_scores(data: Dict[str, pd.DataFrame], k: int = 50, horizon: int = 6,
               refresh: str = '1D', min_memory: int = 500,
               max_memory: Optional[int] = None) -> Dict[str, pd.DataFrame]:
    """
    심볼별 DataFrame [p_up, mean_ret, n_memory] 반환. 봉 i 행 = 봉 i 마감 시점의 판단 근거.
    max_memory: 최근 N개 장면만 기억 (None이면 전부)
    """
    scenes_x, scenes_y, scenes_known = [], [], []
    queries = []   # (symbol, decision_time ndarray, X ndarray)
    for sym, df in data.items():
        bar = _bar(df.index)
        X = make_features(df)
        y = forward_return(df, horizon)
        decision = df.index + bar                                   # 봉 마감 시각
        # 결과 확정 시각: 결과에 봉 j+1+horizon 시가가 필요 → 그 봉까지 마감된 시점부터 사용 (엄격하게)
        known = pd.Series(decision, index=df.index).shift(-(horizon + 1))
        ok = X.notna().all(axis=1) & y.notna() & known.notna()
        scenes_x.append(X[ok].to_numpy())
        scenes_y.append(y[ok].to_numpy())
        scenes_known.append(known[ok].to_numpy(dtype='datetime64[ns]'))
        qok = X.notna().all(axis=1)
        queries.append((sym, df.index, decision[qok.to_numpy()].to_numpy(dtype='datetime64[ns]'),
                        X[qok].to_numpy(), qok))

    mx = np.concatenate(scenes_x) if scenes_x else np.empty((0, len(FEATURES)))
    my = np.concatenate(scenes_y) if scenes_y else np.empty(0)
    mk = np.concatenate(scenes_known) if scenes_known else np.empty(0, dtype='datetime64[ns]')
    order = np.argsort(mk, kind='stable')
    mx, my, mk = mx[order], my[order], mk[order]

    out: Dict[str, pd.DataFrame] = {}
    step = np.timedelta64(pd.Timedelta(refresh))
    for sym, index, dtimes, qx, qok in queries:
        p_up = np.full(len(dtimes), np.nan)
        mean_ret = np.full(len(dtimes), np.nan)
        n_mem = np.zeros(len(dtimes), dtype=int)
        if len(dtimes):
            # 갱신 블록: 블록 시작 시각까지 확정된 장면만 기억으로 사용
            block_start = dtimes.astype('datetime64[ns]') - ((dtimes - dtimes[0]) % step)
            for bs in np.unique(block_start):
                rows = np.where(block_start == bs)[0]
                m = int(np.searchsorted(mk, bs, side='right'))
                lo = 0 if max_memory is None else max(0, m - max_memory)
                if m - lo < min_memory:
                    continue
                Mx, My = mx[lo:m], my[lo:m]
                mu, sd = Mx.mean(axis=0), Mx.std(axis=0)
                sd[sd == 0] = 1.0
                Z = (Mx - mu) / sd
                Q = (qx[rows] - mu) / sd
                d = ((Q[:, None, :] - Z[None, :, :]) ** 2).sum(axis=2)
                kk = min(k, m - lo)
                nn = np.argpartition(d, kk - 1, axis=1)[:, :kk]
                ny = My[nn]
                p_up[rows] = (ny > 0).mean(axis=1)
                mean_ret[rows] = ny.mean(axis=1)
                n_mem[rows] = m - lo
        frame = pd.DataFrame({'p_up': np.nan, 'mean_ret': np.nan, 'n_memory': 0}, index=index)
        frame.loc[qok.to_numpy(), 'p_up'] = p_up
        frame.loc[qok.to_numpy(), 'mean_ret'] = mean_ret
        frame.loc[qok.to_numpy(), 'n_memory'] = n_mem
        out[sym] = frame
    return out


def knn_memory(data: Dict[str, pd.DataFrame], k: int = 50, horizon: int = 6, threshold: float = 0.55,
               long_only: bool = False, refresh: str = '1D', min_memory: int = 500,
               max_memory: Optional[int] = None) -> Dict[str, pd.Series]:
    """
    비슷한 장면 중 오른 비율 ≥ threshold 이고 평균 수익 > 0 이면 롱,
    ≤ 1-threshold 이고 평균 수익 < 0 이면 숏(long_only면 현금), 그 외 현금.
    진입 후 최소 horizon봉 유지 (_hold).
    """
    scores = knn_scores(data, k=k, horizon=horizon, refresh=refresh,
                        min_memory=min_memory, max_memory=max_memory)
    out = {}
    for sym, s in scores.items():
        long_ = ((s['p_up'] >= threshold) & (s['mean_ret'] > 0)).to_numpy()
        short = ((s['p_up'] <= 1 - threshold) & (s['mean_ret'] < 0)).to_numpy() & (not long_only)
        raw = np.where(long_, 1.0, np.where(short, -1.0, 0.0))
        out[sym] = pd.Series(_hold(raw, horizon), index=s.index)
    return out


def _hold(raw: np.ndarray, horizon: int) -> np.ndarray:
    """
    예측은 'horizon봉 뒤' 결과이므로, 진입하면 horizon봉 동안 유지한다 (매 봉 뒤집으면 비용만 커짐).
    유지 중 반대 신호가 나오면 그때 전환. 과거 값만 보므로 인과성 유지.
    """
    pos = np.zeros(len(raw))
    cur, left = 0.0, 0
    for i, r in enumerate(raw):
        if r != 0 and r != cur:
            cur, left = r, horizon
        elif r != 0:
            left = horizon
        elif left > 0:
            left -= 1
        else:
            cur = 0.0
        pos[i] = cur
    return pos
