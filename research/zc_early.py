"""
ZC2 전에 '느긋하게' 인식하기

ZC2(히스토그램 0선 교차)까지 기다리면 EB → ZC2 구간(중앙값 +2.2 ATR)을 놓친다.
구간 B 안에서 다음 조건이 처음 맞는 1h봉 마감에 인식·진입한다.

  인식(wait=n): 구간 B 히스토그램이 그때까지의 최저(절대값 최대)에서 n봉 연속 0 쪽으로 돌아옴
                → n이 작으면 빠르고(바닥 오인 위험), 크면 느긋함(ZC2에 가까워짐)
  아직 ZC2 전이어야 함. ZC2까지 조건이 안 맞으면 ZC2에서 인식(= 기존 방식)

체결: 인식 봉 마감 직후 하위봉(5m) 시가 진입
손절: 인식 시점까지의 B 극점(EB_so_far) — 그 뒤 B가 더 깊어지면 손절
청산: ZC2 다음 제로크로스(ZC3) 봉 마감 직후 하위봉 시가 (zc_trades와 동일)
모든 판단은 인식 봉까지의 데이터만 사용.
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import _macd_hist, find_windows
from research.zc_trades import _simulate

WAITS = (1, 2, 3, 4, 6)


def _trigger(hv: np.ndarray, z1: int, z2: int, wait: int) -> int:
    """구간 B [z1, z2)에서 히스토그램이 최저점 뒤 wait봉 연속 0 쪽으로 돌아온 첫 봉. 없으면 z2."""
    best, rise = z1, 0
    for j in range(z1 + 1, z2):
        if abs(hv[j]) > abs(hv[best]):
            best, rise = j, 0
        elif abs(hv[j]) < abs(hv[j - 1]):
            rise += 1
            if rise >= wait:
                return j
        else:
            rise = 0
    return z2


def ledger(df_sub: pd.DataFrame, tf: str = '1h', cost: float = 0.00115, waits=WAITS,
           stop_buffer_atr: float = 0.0, use_stop: bool = True) -> pd.DataFrame:
    """stop_buffer_atr: 손절선을 B 극점에서 ATR 몇 배 더 바깥에 둠. use_stop=False면 ZC3까지 보유"""
    h = rd.resample(df_sub, tf)
    bar = pd.Timedelta(pd.tseries.frequencies.to_offset(tf))
    w = find_windows(h)
    hv = _macd_hist(h['close']).to_numpy()
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    hh, hl = h['high'].to_numpy(), h['low'].to_numpy()
    ts = df_sub.index
    o, hi5, lo5 = df_sub['open'].to_numpy(), df_sub['high'].to_numpy(), df_sub['low'].to_numpy()
    rows = []
    for _, r in w.iterrows():
        z1, z2, z3 = int(r['zc1']), int(r['zc2']), int(r['zc3'])
        if z3 < 0 or z3 + 1 >= len(h):
            continue
        d = float(r['dir'])
        t_out = h.index[z3] + bar
        b = ts.searchsorted(t_out)
        if b >= len(ts):
            continue
        row = {'zc2': h.index[z2], 'side': d, 'dir': '롱' if d > 0 else '숏', 'b_bars': z2 - z1}
        for wt in (0,) + tuple(waits):                       # 0 = ZC2에서 인식 (기준)
            j = z2 if wt == 0 else _trigger(hv, z1, z2, wt)
            seg = slice(z1, j + 1)
            ext = hl[seg].min() if d > 0 else hh[seg].max()   # 인식 시점까지의 B 극점
            a = ts.searchsorted(h.index[j] + bar)
            if a >= b:
                continue
            entry = o[a]
            ext = ext - d * stop_buffer_atr * atr[j]
            stop = ext if use_stop and ((d > 0 and ext < entry) or (d < 0 and ext > entry)) else None
            ret, why, _ = _simulate(d, entry, stop, None, hi5[a:b], lo5[a:b], o[a:b], o[b], cost)
            row[f'r{wt}'] = ret
            row[f'early{wt}'] = z2 - j                        # ZC2보다 몇 봉 먼저 인식했나
            row[f'stopatr{wt}'] = abs(entry - ext) / atr[j] if atr[j] > 0 else np.nan
            row[f'why{wt}'] = why
        rows.append(row)
    return pd.DataFrame(rows)


def summarize(L: pd.DataFrame, fit_end: pd.Timestamp, cost: float = 0.00115, waits=WAITS) -> pd.DataFrame:
    out = []
    for wt in (0,) + tuple(waits):
        r = L[f'r{wt}']
        row = {'인식': 'ZC2(기존)' if wt == 0 else f'{wt}봉 반등 확인',
               'ZC2보다_빠름(봉,중앙)': float(L[f'early{wt}'].median()),
               '손절거리(ATR,중앙)': round(float(L[f'stopatr{wt}'].median()), 2),
               '손절률': round(float((L[f'why{wt}'] == '손절').mean()), 2)}
        for name, m in (('학습', L['zc2'] < fit_end), ('검증', L['zc2'] >= fit_end)):
            g = r[m] + 2 * cost
            row[f'{name}_비용전%'] = round(float(g.mean() * 100), 3)
            row[f'{name}_t'] = round(float(g.mean() / g.std() * np.sqrt(len(g))), 2)
            row[f'{name}_비용후%'] = round(float(r[m].mean() * 100), 3)
            row[f'{name}_승률'] = round(float((r[m] > 0).mean()), 2)
        out.append(row)
    return pd.DataFrame(out)
