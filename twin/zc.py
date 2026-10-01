"""
ZC 구간 찾기 (1h MACD(12,26,9) 히스토그램)

  ZC0 ──[구간 A: 극점 EA]── ZC1 ──[구간 B: 극점 EB]── ZC2
  - ZC: 히스토그램 부호가 바뀐 봉 (그 봉 종가로 확정)
  - 구간 A가 양(+)이면 EA=고점, B는 음(-)이므로 EB=저점 (반대도 동일)
  - find_windows()의 한 행 = ZC2 봉에서 확정된 범위 하나. 다음 교차(ZC3) 위치도 붙임(없으면 -1)
"""

from typing import List

import numpy as np
import pandas as pd

DESCRIPTORS: List[str] = [
    'dir',            # 구간 A 부호 (+1: A가 양 → 새 구간도 양 → 기본 롱)
    'len_a', 'len_b',  # 구간 길이 (log 봉 수)
    'len_ratio',      # log(B 길이 / A 길이)
    'swing',          # (EB - EA) / ATR × dir   : A 극점→B 극점 낙폭 (클수록 깊은 되돌림)
    'retrace_a',      # (EA - 종가@ZC0) / ATR × dir : A 구간에서 간 거리
    'retrace_b',      # (EB - 종가@ZC1) / ATR × dir : B 구간에서 되돌린 거리
    'from_eb',        # (종가@ZC2 - EB) / ATR × dir : B 극점에서 ZC2까지 회복 거리
    'hist_a', 'hist_b',  # 구간별 |히스토그램| 최대값 ÷ 최근 히스토그램 표준편차
    'hist_ratio',     # log(hist_b / hist_a)  : 다이버전스 정도
    'peak_pos_a', 'peak_pos_b',  # 극점이 구간의 어느 위치에서 나왔나 (0=시작, 1=끝)
    'vol_ratio',      # log(B 평균 거래량 / A 평균 거래량)
    'atr_pct',        # ATR / 종가 (변동성 수준)
]


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    m = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    return m - m.ewm(span=signal, adjust=False).mean()


def find_windows(df: pd.DataFrame, macd: tuple = (12, 26, 9), hist_norm: int = 200) -> pd.DataFrame:
    """
    모든 ZC0-ZC1-ZC2 범위와 상대값 묘사. 행 하나 = ZC2 봉에서 확정된 범위 하나.
    모든 값은 ZC2 봉까지의 데이터만 사용.
    """
    c, h, l = df['close'], df['high'], df['low']
    hist = _macd_hist(c, *macd)
    sgn = np.sign(hist.to_numpy())
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    hstd = hist.rolling(hist_norm, min_periods=hist_norm // 2).std().to_numpy()
    vol = df['volume'].to_numpy(dtype=float)
    hv, cv, hiv, lov = hist.to_numpy(), c.to_numpy(), h.to_numpy(), l.to_numpy()

    # 부호가 바뀐 봉 (0은 직전 부호 유지로 취급)
    s = pd.Series(sgn).replace(0, np.nan).ffill().to_numpy()
    zc = [i for i in range(1, len(s)) if not np.isnan(s[i - 1]) and s[i] != s[i - 1]]

    rows = []
    for j in range(2, len(zc)):
        z0, z1, z2 = zc[j - 2], zc[j - 1], zc[j]
        d = float(s[z0])                       # 구간 A 부호
        a = slice(z0, z1)
        b = slice(z1, z2)
        if d > 0:
            ia, ib = z0 + int(np.argmax(hiv[a])), z1 + int(np.argmin(lov[b]))
            ea, eb = hiv[ia], lov[ib]
        else:
            ia, ib = z0 + int(np.argmin(lov[a])), z1 + int(np.argmax(hiv[b]))
            ea, eb = lov[ia], hiv[ib]
        at = atr[z2]
        hs = hstd[z2]
        if not np.isfinite(at) or at <= 0 or not np.isfinite(hs) or hs <= 0:
            continue
        la, lb = z1 - z0, z2 - z1
        ha, hb = np.abs(hv[a]).max() / hs, np.abs(hv[b]).max() / hs
        va, vb = np.nanmean(vol[a]), np.nanmean(vol[b])
        rows.append({
            'zc0': z0, 'zc1': z1, 'zc2': z2, 'ea_bar': ia, 'eb_bar': ib, 'ea': ea, 'eb': eb,
            'dir': d,
            'len_a': np.log(la), 'len_b': np.log(lb), 'len_ratio': np.log(lb / la),
            'swing': (eb - ea) / at * d,
            'retrace_a': (ea - cv[z0]) / at * d,
            'retrace_b': (eb - cv[z1]) / at * d,
            'from_eb': (cv[z2] - eb) / at * d,
            'hist_a': ha, 'hist_b': hb, 'hist_ratio': np.log(hb / ha) if ha > 0 and hb > 0 else np.nan,
            'peak_pos_a': (ia - z0) / max(la - 1, 1), 'peak_pos_b': (ib - z1) / max(lb - 1, 1),
            'vol_ratio': np.log(vb / va) if va > 0 and vb > 0 else np.nan,
            'atr_pct': at / cv[z2],
        })
    w = pd.DataFrame(rows)
    if w.empty:
        return w
    w['decide_time'] = df.index[w['zc2'].to_numpy()]
    # 다음 제로크로스(ZC3) 위치 (청산 판단 봉). 아직 없으면 -1
    nxt = {zc[j]: zc[j + 1] for j in range(len(zc) - 1)}
    w['zc3'] = w['zc2'].map(nxt).fillna(-1).astype(int)
    return w


