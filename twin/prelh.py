"""
PRE_LH 모듈 — L/H가 만들어질 그림 (ZC0 → … → L/H)

같은 계산식 하나로:
  - 역사 사건: 실제 L/H 봉에서 자른 구간 [ZC0, L/H]  (L/H는 '자르는 위치'로만 씀)
  - 실시간:    지금 q까지 구간 [ZC0, q]
를 JSON으로 만든다. 계산에 쓰는 값은 그 구간 안의 봉뿐이고, 기준값도 "지금까지"의 값(지금까지 최대 히스토그램,
지금까지 평균 거래량, 지금까지 바닥)만 쓴다. 최종 L/H 가격·최종 길이·ZC2는 계산에 들어가지 않는다.
ZC2 이후(POST_LH)는 이 모듈에 없다.

채널
  price_path         ZC0 종가 대비 등하락 % (숏은 뒤집음), 길이 G로 늘림
  relative_moves     꺾이는 점(다리) 목록: 방향, 직전 다리 대비 크기·시간 (마지막 6개를 고정 길이로)
  relative_times     구간 진행 시간 ÷ (ZC0→지금 최고점까지 시간), 바닥 뒤 시간 ÷ 전체 진행 시간
  candidate_progress 지금까지 바닥이 새로 깊어진 위치들 (진행 비율)과 깊이 (ZC0 대비 %) — 마지막 6개
  candle_path        몸통·위꼬리·아래꼬리 ÷ 봉 길이, 구간을 8칸으로 나눈 평균
  macd_path          5m·15m·1h 히스토그램 ÷ 지금까지 |최대|, 길이 G/8로 늘림
  volume_path        거래량 ÷ 지금까지 평균, 길이 G/8로 늘림
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from twin.shape import raw_events, zigzag

G = 256
GS = G // 8
N_LEG = 6
ZZ_PCT = 0.25            # 다리를 끊는 되돌림 크기: 지금까지 등하락 폭의 25% (상대값)


def _st(y: np.ndarray, n: int) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if len(y) == 0:
        return np.zeros(n)
    if len(y) == 1:
        return np.repeat(y[0], n)
    return np.interp(np.linspace(0, len(y) - 1, n), np.arange(len(y)), np.nan_to_num(y))


def pre_lh(ev: Dict, q: int) -> Optional[Dict]:
    """[ZC0, q) 구간 JSON. q는 사건 시작(ZC0 전 파동 시작) 기준 위치. 역사 사건은 q = L/H 봉 + 1"""
    A0 = ev['A0']
    if q - A0 < 6:
        return None
    o, hi, lo, c, v = (ev[k][A0:q] for k in ('o', 'hi', 'lo', 'c', 'v'))
    pct = (c / c[0] - 1.0) * 100.0 * ev['d']
    span = max(pct.max() - pct.min(), 1e-9)
    piv = zigzag(pct, ZZ_PCT * span)
    legs = []
    for (i0, v0), (i1, v1) in zip(piv[:-1], piv[1:]):
        if i1 > i0:
            legs.append((np.sign(v1 - v0), abs(v1 - v0), i1 - i0))
    lv = np.zeros(3 * N_LEG)
    for k, (dr, sz, tm) in enumerate(legs[-N_LEG:]):
        j = len(legs) - min(len(legs), N_LEG) + k
        prev = legs[j - 1] if j >= 1 else None
        lv[3 * k:3 * k + 3] = [dr, np.log(sz / prev[1]) if prev and prev[1] > 0 else 0.0,
                               np.log(tm / prev[2]) if prev and prev[2] > 0 else 0.0]
    n = len(pct)
    top = int(np.argmax(pct))
    low = int(np.argmin(pct[top:])) + top if top < n - 1 else n - 1
    times = [n / max(top + 1, 1), (n - 1 - low) / n, top / n]
    run = np.minimum.accumulate(pct)
    new = [k for k in range(1, n) if run[k] < run[k - 1] - 0.1 * span]
    cand = np.zeros(2 * N_LEG)
    for k, idx in enumerate(new[-N_LEG:]):
        cand[2 * k:2 * k + 2] = [idx / n, pct[idx]]
    rng = np.maximum(hi - lo, 1e-12)
    body, uw, lw = np.abs(c - o) / rng, (hi - np.maximum(o, c)) / rng, (np.minimum(o, c) - lo) / rng
    cuts = np.linspace(0, n, 9).astype(int)
    candle = np.array([[x[a:b].mean() if b > a else 0.0 for x in (body, uw, lw)] for a, b in zip(cuts[:-1], cuts[1:])]).ravel()
    macd = []
    for k in ('m5', 'm15', 'm1h'):
        x = np.nan_to_num(ev[k][A0:q])
        macd.append(_st(x / max(np.abs(x).max(), 1e-12), GS))
    vol = v / max(v.mean(), 1e-12)
    return {'n_bars': n, 'price_path': _st(pct, G), 'relative_moves': lv, 'relative_times': np.array(times),
            'candidate_progress': cand, 'candle_path': candle, 'macd_path': np.concatenate(macd),
            'volume_path': _st(vol, GS)}


CHANNELS = ('price_path', 'relative_moves', 'relative_times', 'candidate_progress', 'candle_path', 'macd_path',
            'volume_path')
WEIGHT = {'price_path': 3.0, 'relative_moves': 1.0, 'relative_times': 1.0, 'candidate_progress': 1.0,
          'candle_path': 0.5, 'macd_path': 1.0, 'volume_path': 0.5}


def to_json(js: Dict, meta: Dict) -> Dict:
    return {**meta, 'module': 'PRE_LH', **{k: np.round(np.asarray(js[k], dtype=float), 4).tolist() for k in CHANNELS},
            'n_bars': int(js['n_bars'])}


def vector(js: Dict, scale: Dict[str, float]) -> np.ndarray:
    """채널마다 표준 크기로 나누고 무게를 곱해 한 줄로 (거리 = 유클리드)"""
    return np.nan_to_num(np.concatenate([np.sqrt(WEIGHT[k]) * np.asarray(js[k], dtype=float) / scale[k] / np.sqrt(len(js[k]))
                                         for k in CHANNELS]))


def channel_scale(J: List[Dict]) -> Dict[str, float]:
    return {k: float(np.nanstd(np.vstack([np.nan_to_num(j[k]) for j in J]))) + 1e-9 for k in CHANNELS}


def history(df5: pd.DataFrame, rule: str = '1h') -> pd.DataFrame:
    """역사 사건마다 실제 L/H에서 자른 PRE_LH JSON (L/H는 자르는 위치로만)"""
    rows = []
    for n, e in enumerate(raw_events(df5, rule)):
        M, N = e['M'], e['N']
        lh = M + int(np.argmin(e['lo'][M:N]))
        js = pre_lh(e, lh + 1)
        if js is None:
            continue
        rows.append({'ev': n, 'eid': e['zc2'].strftime('%Y-%m-%dT%H%M'), 'zc2': e['zc2'], 'zc2_close': e['zc2_close'],
                     'lh_bar': lh, 'js': js})
    return pd.DataFrame(rows)
