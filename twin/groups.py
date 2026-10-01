"""
그룹(27칸 그림) 정하기 — 아틀라스 좌표와 고정 규칙

ZC 아틀라스 좌표 (사용자 'Historical Shape Atlas'와 같은 좌표계)

x축: ZC0 → 첫 극점(EA) → ZC1 → 둘째 극점(EB) → ZC2, 네 구간을 각각 SEG개 점으로 맞춤 (5개 기준점 정렬)
y축: (5분봉 종가 - ZC1 봉 시가) ÷ (두 파동 전체 고가-저가 범위), 숏(H 극점)은 위아래 반전 → 대략 -1 ~ 1
모든 값은 ZC2 봉 마감까지의 정보 → ZC2 이후 매매 판단에 미래 데이터 없이 쓸 수 있음
"""



import numpy as np
import pandas as pd

from twin import data as rd
from twin.zc import find_windows

SEG = 12


def _rs(y: np.ndarray, n: int) -> np.ndarray:
    if len(y) == 1:
        return np.repeat(y, n)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), y)


def atlas(df5: pd.DataFrame, seg: int = SEG) -> pd.DataFrame:
    """사건별 아틀라스 벡터(4*seg) + 기준점 시각. zc2 열로 다른 장부와 연결."""
    h = rd.resample(df5, '1h')
    H = pd.Timedelta(hours=1)
    w = find_windows(h)
    t5 = df5.index
    c5, h5, l5, o5 = (df5[k].to_numpy() for k in ('close', 'high', 'low', 'open'))
    rows = []
    for _, r in w.iterrows():
        z0, z1, z2 = int(r['zc0']), int(r['zc1']), int(r['zc2'])
        d = float(r['dir'])
        a = t5.searchsorted(h.index[z0])
        m = t5.searchsorted(h.index[z1])
        b = t5.searchsorted(h.index[z2] + H)
        if b > len(t5) or m <= a or b <= m:
            continue
        # 극점은 5분봉에서 다시 찾음 (구간 A: 양이면 최고가, B: 반대)
        ea = a + int(np.argmax(h5[a:m]) if d > 0 else np.argmin(l5[a:m]))
        eb = m + int(np.argmin(l5[m:b]) if d > 0 else np.argmax(h5[m:b]))
        rng = h5[a:b].max() - l5[a:b].min()
        if rng <= 0:
            continue
        y = (c5[a:b] - o5[m]) / rng * d
        cut = [0, ea - a, m - a, eb - a, b - a - 1]
        vec = np.concatenate([_rs(y[cut[i]:cut[i + 1] + 1], seg) for i in range(4)])
        rows.append({'zc2': h.index[z2], 'side': '롱' if d > 0 else '숏', 'bars5': b - a,
                     'segs': np.diff(cut), 'vec': vec.round(3)})
    return pd.DataFrame(rows)


# ── 규칙 분류 (그림만, 성과 없음) ──────────────────────────────────────────
# 그림을 결정하는 세 기준점 높이 (ZC1 시가 = 0, 두 파동 범위 = 1, 숏은 반전)
#   시작: ZC0 위치 (idx 0)   B: 둘째 극점 깊이 (idx 3*SEG-1)   끝: ZC2 위치 (idx 4*SEG-1)
# 경계값은 2020~2026 전체 3분위를 0.05 단위로 반올림 (2023년 전/후 3분위와 차이 0.03 이내)
CUTS = {'start': (-0.30, 0.00), 'b': (-0.55, -0.30), 'end': (-0.15, 0.15)}
WORDS = {'start': ('시작낮음', '시작중간', '시작높음'),
         'b': ('B깊음', 'B중간', 'B얕음'),
         'end': ('끝낮음', '끝중간', '끝높음')}
EDGE = 0.03


def classify(A: pd.DataFrame, seg: int = SEG) -> pd.DataFrame:
    """atlas() 결과에 3×3×3 = 27개 그림 번호(pic 1~27)와 이름, 경계 여부를 붙임"""
    X = np.vstack(A['vec'].to_numpy())
    pts = {'start': X[:, 0], 'b': X[:, 3 * seg - 1], 'end': X[:, 4 * seg - 1]}
    A = A.copy()
    lv = {k: np.digitize(v, CUTS[k]) for k, v in pts.items()}
    A['pic'] = lv['start'] * 9 + lv['b'] * 3 + lv['end'] + 1
    A['name'] = [' · '.join(WORDS[k][lv[k][i]] for k in ('start', 'b', 'end')) for i in range(len(A))]
    A['edge'] = np.any([np.min(np.abs(v[:, None] - np.array(CUTS[k])[None]), axis=1) < EDGE
                        for k, v in pts.items()], axis=0)
    for k, v in pts.items():
        A[f'y_{k}'] = v
    return A
