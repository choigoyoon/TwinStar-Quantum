"""
ZC0→ZC2 매매 그림 묶기

'비슷하다'의 정의
1. 그림 맞추기 (정규화)
   - 가로(시간): 구간 A(ZC0→ZC1)와 구간 B(ZC1→ZC2)를 각각 POINTS개 점으로 늘이거나 줄임
     → 길이가 달라도 ZC0·ZC1·ZC2가 같은 가로 위치에 오게 맞춤
   - 세로(가격): (종가 - ZC0 종가) ÷ ATR(ZC2 시점)  → 가격 수준·변동성과 무관한 'ATR 몇 배' 단위
   - 방향: 숏 건(구간 A가 음)은 위아래를 뒤집음 → 모든 그림이 '구간 A 상승 → 구간 B 되돌림' 모양으로 정렬
2. 거리 = 겹친 두 그림의 점별 차이 제곱합(유클리드) + 속도 차이
   - 속도 = log(구간 A 봉 수), log(구간 B 봉 수)  (늘이고 줄이며 잃은 '얼마나 빨리' 정보)
   - 두 부분을 표준화해 같은 비중으로 합침 (tempo_weight로 조절)
3. 묶기 = k-평균. k는 실루엣 점수로 고름 (데이터를 보고 고르는 유일한 값)

인과성: 묶음의 중심은 학습 기간(fit_end 이전에 끝난 건)으로만 만들고,
        그 뒤의 건은 가장 가까운 중심에 '배정'만 한다 → 배정은 ZC2 시점 정보만 사용.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import find_windows

POINTS = 16


def _resample(y: np.ndarray, n: int) -> np.ndarray:
    if len(y) == 1:
        return np.repeat(y, n)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)


def pictures(h: pd.DataFrame, w: pd.DataFrame, points: int = POINTS) -> Tuple[np.ndarray, np.ndarray]:
    """범위마다 (그림 벡터 2*points, 속도 벡터 2). ZC2 봉까지의 데이터만 사용."""
    c = h['close'].to_numpy()
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    pics, tempo = [], []
    for _, r in w.iterrows():
        z0, z1, z2 = int(r['zc0']), int(r['zc1']), int(r['zc2'])
        d, at = float(r['dir']), atr[z2]
        a = (c[z0:z1 + 1] - c[z0]) / at * d          # ZC0..ZC1 (ZC1 포함)
        b = (c[z1:z2 + 1] - c[z0]) / at * d          # ZC1..ZC2
        pics.append(np.r_[_resample(a, points), _resample(b, points)])
        tempo.append([np.log(z1 - z0), np.log(z2 - z1)])
    return np.array(pics), np.array(tempo)


def build(data15: Dict[str, pd.DataFrame], ledger: pd.DataFrame, tf: str = '1h') -> pd.DataFrame:
    """장부(zc_trades.run 결과)에 그림·속도 벡터를 붙임"""
    out = []
    for sym, df in data15.items():
        h = rd.resample(df, tf)
        w = find_windows(h)
        P, T = pictures(h, w)
        key = pd.DataFrame({'symbol': sym, 'zc2': h.index[w['zc2'].to_numpy()]})
        key['pic'] = list(P)
        key['tempo'] = list(T)
        out.append(key)
    K = pd.concat(out, ignore_index=True)
    return ledger.merge(K, on=['symbol', 'zc2'], how='inner')


def _matrix(L: pd.DataFrame, tempo_weight: float, scale: Optional[Tuple] = None):
    P = np.vstack(L['pic'].to_numpy())
    T = np.vstack(L['tempo'].to_numpy())
    if scale is None:
        scale = (P.std(), T.mean(axis=0), T.std(axis=0))
    ps, tm, ts = scale
    # 그림 32점 전체가 한 덩어리, 속도 2개가 한 덩어리 → 차원 수로 나눠 비중을 맞춤
    X = np.hstack([P / ps / np.sqrt(P.shape[1]), (T - tm) / ts / np.sqrt(T.shape[1]) * tempo_weight])
    return X, scale


def cluster(L: pd.DataFrame, fit_end: pd.Timestamp, k: Optional[int] = None, k_range=range(4, 11),
            tempo_weight: float = 1.0, seed: int = 0) -> Tuple[pd.DataFrame, Dict]:
    """fit_end 이전 건으로 묶음을 만들고 전체 건을 배정. k=None이면 학습 건의 실루엣으로 선택."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    train = L[L['exit_time'] < fit_end]
    Xtr, scale = _matrix(train, tempo_weight)
    sil = {}
    if k is None:
        for kk in k_range:
            km = KMeans(kk, n_init=10, random_state=seed).fit(Xtr)
            sil[kk] = float(silhouette_score(Xtr, km.labels_, sample_size=min(3000, len(Xtr)), random_state=seed))
        k = max(sil, key=lambda x: sil[x])
    km = KMeans(k, n_init=20, random_state=seed).fit(Xtr)
    # 묶음 번호를 '구간 B 끝(ZC2) 높이' 순으로 다시 매김 → 읽기 쉽게
    order = np.argsort(km.cluster_centers_[:, 2 * POINTS - 1])
    remap = {old: new for new, old in enumerate(order)}
    X, _ = _matrix(L, tempo_weight, scale)
    L = L.copy()
    L['cluster'] = [remap[c] for c in km.predict(X)]
    L['dist'] = np.min(np.linalg.norm(X[:, None, :] - km.cluster_centers_[None, :, :], axis=2), axis=1)
    L['period'] = np.where(L['exit_time'] < fit_end, '학습', '검증')
    return L, {'k': k, 'silhouette': sil, 'scale': scale}


def summarize(L: pd.DataFrame, cost: float = 0.00115) -> pd.DataFrame:
    """묶음별 모양(평균 그림 요약)과 결과(학습/검증 기간 따로)"""
    rows = []
    for c, g in L.groupby('cluster'):
        P = np.vstack(g['pic'].to_numpy())
        m = P.mean(axis=0)
        T = np.exp(np.vstack(g['tempo'].to_numpy()))
        row = {'묶음': int(c), '건수': len(g),
               'A끝(ZC1)': round(float(m[POINTS - 1]), 2), 'A최고': round(float(m[:POINTS].max()), 2),
               'B최저': round(float(m[POINTS:].min()), 2), 'B끝(ZC2)': round(float(m[-1]), 2),
               'A봉수': round(float(np.median(T[:, 0])), 1), 'B봉수': round(float(np.median(T[:, 1])), 1),
               '롱비율': round(float((g['side'] > 0).mean()), 2)}
        for per in ('학습', '검증'):
            s = g[g['period'] == per]
            gross = s['r_stop_eb'] + 2 * cost
            row[f'{per}_건수'] = len(s)
            row[f'{per}_비용전%'] = round(float(gross.mean() * 100), 3) if len(s) else np.nan
            row[f'{per}_t'] = round(float(gross.mean() / gross.std() * np.sqrt(len(s))), 2) if len(s) > 2 else np.nan
            row[f'{per}_승률'] = round(float((s['r_stop_eb'] > 0).mean()), 2) if len(s) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
