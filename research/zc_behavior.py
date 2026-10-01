"""
ZC2 다음 행동 분류 (그림 상자 안에서 "그다음에 어떻게 움직였나")

ZC2 마감 가격에서 ZC3 마감까지의 5분봉 움직임을 아틀라스와 같은 잣대(두 파동 범위 = 1, 숏은 반전)로 재고
다섯 가지 행동 중 하나로 나눔. 행동은 ZC3까지 봐야 정해지는 사후 이름표이며, 그림 상자(ZC2까지의 정보)와
짝지어 "이 그림 다음엔 주로 무슨 일이 있었나"를 세는 데 씀.

    1 크게감   : B 극점을 안 깨고, 최고로 0.5 이상 감
    2 조금감   : B 극점을 안 깨고, 0.2 ~ 0.5 감
    3 제자리   : B 극점을 안 깨고, 0.2 미만
    4 깨고복귀 : B 극점을 깼지만 ZC3 때 ZC2 가격 위로 돌아옴
    5 깨고하락 : B 극점을 깨고 ZC3 때도 ZC2 가격 아래
"""

from typing import Dict

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import find_windows

MOVES = ('크게감', '조금감', '제자리', '깨고복귀', '깨고하락')
BIG, SMALL = 0.5, 0.2


def after_moves(df5: pd.DataFrame) -> pd.DataFrame:
    """ZC3가 끝난 사건마다 ZC2 이후 행동. zc2 열로 아틀라스 표와 연결."""
    h = rd.resample(df5, '1h')
    H = pd.Timedelta(hours=1)
    w = find_windows(h)
    t5 = df5.index
    c5, h5, l5, o5 = (df5[k].to_numpy() for k in ('close', 'high', 'low', 'open'))
    rows = []
    for _, r in w.iterrows():
        z0, z1, z2, z3 = int(r['zc0']), int(r['zc1']), int(r['zc2']), int(r['zc3'])
        if z3 < 0:
            continue
        d = float(r['dir'])
        a = t5.searchsorted(h.index[z0])
        m = t5.searchsorted(h.index[z1])
        b = t5.searchsorted(h.index[z2] + H)          # ZC2 마감 다음 5분봉
        e = t5.searchsorted(h.index[z3] + H)          # ZC3 마감 다음 5분봉
        if e > len(t5) or not (a < m < b < e):
            continue
        rng = h5[a:b].max() - l5[a:b].min()
        if rng <= 0:
            continue
        p0 = c5[b - 1]                                 # ZC2 마감 가격
        eb = l5[m:b].min() if d > 0 else h5[m:b].max()
        hi, lo = h5[b:e], l5[b:e]
        up = ((hi.max() - p0) if d > 0 else (p0 - lo.min())) / rng
        broke = bool(lo.min() < eb) if d > 0 else bool(hi.max() > eb)
        end = (c5[e - 1] - p0) / rng * d
        if broke:
            mv = 3 if end > 0 else 4
        else:
            mv = 0 if up >= BIG else (1 if up >= SMALL else 2)
        rows.append({'zc2': h.index[z2], 'zc3': h.index[z3], 'move': MOVES[mv],
                     'up': round(up, 3), 'end': round(end, 3), 'broke': broke})
    return pd.DataFrame(rows)


def box_table(P: pd.DataFrame, split: pd.Timestamp, prior: float = 20.0) -> Dict:
    """
    P = classify() 결과 + move 열.
    상자별 행동 비율(앞 기간/뒤 기간)과, 앞 기간 상자 비율이 뒤 기간 행동을 전체 비율보다 잘 맞히는지(평균 로그손실).
    prior: 상자 비율을 전체 비율 쪽으로 당기는 가상 건수 (작은 상자의 우연을 줄임)
    """
    early, late = P[P['zc2'] < split], P[P['zc2'] >= split]
    allp = early['move'].value_counts(normalize=True).reindex(MOVES).fillna(0).to_numpy() + 1e-9
    rows, ll_box, ll_all = [], [], []
    for pic, g in P.groupby('pic'):
        ge, gl = early[early['pic'] == pic], late[late['pic'] == pic]
        ce = ge['move'].value_counts().reindex(MOVES).fillna(0).to_numpy()
        cl = gl['move'].value_counts().reindex(MOVES).fillna(0).to_numpy()
        pb = (ce + prior * allp) / (ce.sum() + prior)
        if cl.sum():
            ll_box.append(-(cl * np.log(pb)).sum())
            ll_all.append(-(cl * np.log(allp)).sum())
        rows.append({'pic': int(pic), 'name': g['name'].iloc[0], 'n_early': int(ce.sum()), 'n_late': int(cl.sum()),
                     **{f'e_{k}': round(v / max(ce.sum(), 1), 3) for k, v in zip(MOVES, ce)},
                     **{f'l_{k}': round(v / max(cl.sum(), 1), 3) for k, v in zip(MOVES, cl)}})
    n_late = len(late)
    return {'table': pd.DataFrame(rows), 'overall': dict(zip(MOVES, allp.round(3))),
            'logloss_box': sum(ll_box) / n_late, 'logloss_all': sum(ll_all) / n_late}


def families(T: pd.DataFrame, overall: Dict, lift: float = 1.4, min_n: int = 30) -> pd.Series:
    """두 기간 모두 어떤 행동이 전체 비율의 lift배 이상인 상자에 그 행동 이름을 붙임 (없으면 '섞임', 작으면 '건수부족')"""
    out = {}
    for _, r in T.iterrows():
        if r['n_early'] < min_n or r['n_late'] < min_n:
            out[r['pic']] = '건수부족'
            continue
        best = [(min(r[f'e_{m}'], r[f'l_{m}']) / overall[m], m) for m in MOVES if overall[m] > 0.05]
        s, m = max(best)
        out[r['pic']] = m if s >= lift else '섞임'
    return pd.Series(out, name='family')
