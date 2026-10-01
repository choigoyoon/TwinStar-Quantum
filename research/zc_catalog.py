"""
ZC 사건 그림·행동 분류 (진입 시점까지의 정보만 사용)

사건 = ZC0-ZC1-ZC2 범위 하나. 구간 B(ZC1 이후)에서 극값을 기다렸다가 '행동' 신호가 처음 나올 때 진입.

행동(진입 신호) — 구간 B의 진행 중 극값(RE)이 정해진 뒤, 5분봉 마감마다 먼저 맞는 것
  5M전환   : 5분봉 MACD 히스토그램이 새 방향으로 부호 전환
  15M전환  : 15분봉 MACD 히스토그램 부호 전환 (15분봉 마감 기준)
  가격선돌파: 5분봉 종가가 RE 직전 3개 5분봉의 반대쪽 끝(롱이면 고가)을 넘음
  1H전환   : 위 신호가 없으면 ZC2(1시간봉 히스토그램 0선 교차) 마감
  관망 조건 : RE가 2개 5분봉 이상 갱신되지 않아야 신호로 인정 ('너무 빠르지 않게')

그림(진입 시점에 판정)
  극점형태  : 급쏠림꼬리(RE 1시간봉 범위 ≥1.5ATR, 꼬리 ≥50%) > 여러번시험(RE 0.25ATR 안에 3번+) >
              재시험(2번) > 단일극점
  되돌림    : 구간 A에서 간 만큼 이상 되돌렸으면 '깊은', 아니면 '얕은'
  A강도     : 구간 A 이동이 2ATR 이상이면 '강한A', 아니면 '약한A'

체결: 신호 5분봉 마감 직후 시가 진입 · 손절 = 진입 시점 RE · 청산 = ZC3 마감 직후 시가
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import _macd_hist, find_windows
from research.zc_trades import _simulate

BEHAVIORS: List[str] = ['5M전환', '15M전환', '가격선돌파', '1H전환']


def _flip_bars(hist: pd.Series, d: float) -> pd.Series:
    """히스토그램이 d 방향으로 부호가 바뀐 봉 = True"""
    s = np.sign(hist)
    return (s == d) & (s.shift() != d)


def catalog(df5: pd.DataFrame, cost: float = 0.00115, settle: int = 2) -> pd.DataFrame:
    h = rd.resample(df5, '1h')
    m15 = rd.resample(df5, '15min')
    H, M15, M5 = pd.Timedelta(hours=1), pd.Timedelta(minutes=15), pd.Timedelta(minutes=5)
    w = find_windows(h)
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    hc, hh, hl, ho = h['close'].to_numpy(), h['high'].to_numpy(), h['low'].to_numpy(), h['open'].to_numpy()
    t5 = df5.index
    o5, h5, l5, c5 = (df5[k].to_numpy() for k in ('open', 'high', 'low', 'close'))
    hist5 = _macd_hist(df5['close'])
    hist15 = _macd_hist(m15['close'])
    flips = {}
    for d in (1.0, -1.0):
        f5 = _flip_bars(hist5, d).to_numpy()
        f15 = _flip_bars(hist15, d)
        # 15분봉 신호는 그 15분봉이 끝난 시각(= 그 안의 마지막 5분봉 마감)에 안다
        f15_close = pd.Series(False, index=t5)
        known = f15[f15].index + M15 - M5
        f15_close[known.intersection(t5)] = True
        flips[d] = (f5, f15_close.to_numpy())

    rows = []
    for _, r in w.iterrows():
        z0, z1, z2, z3 = int(r['zc0']), int(r['zc1']), int(r['zc2']), int(r['zc3'])
        if z3 < 0 or z3 + 1 >= len(h):
            continue
        d, at = float(r['dir']), atr[z2]
        if not np.isfinite(at) or at <= 0:
            continue
        a5, b5 = t5.searchsorted(h.index[z1]), t5.searchsorted(h.index[z2] + H)   # 구간 B의 5분봉 [a5, b5)
        x5 = t5.searchsorted(h.index[z3] + H)
        if b5 >= len(t5) or x5 >= len(t5):
            continue
        f5, f15 = flips[d]
        # ZC1은 그 1시간봉 마감에야 확정 → 신호 탐색은 그 뒤부터. 극값은 ZC1 봉 안의 값도 포함(이미 지난 값)
        k5 = t5.searchsorted(h.index[z1] + H)
        if k5 >= b5:
            continue
        pre = slice(a5, k5)
        ext_i = a5 + int(np.argmin(l5[pre]) if d > 0 else np.argmax(h5[pre]))
        ext_v, beh, j_sig = (l5[ext_i] if d > 0 else h5[ext_i]), None, None
        for j in range(k5, b5):
            v = l5[j] if d > 0 else h5[j]
            if (d > 0 and v < ext_v) or (d < 0 and v > ext_v):
                ext_i, ext_v = j, v
                continue
            if j - ext_i < settle:
                continue
            line = (h5[max(a5, ext_i - 2):ext_i + 1].max() if d > 0 else l5[max(a5, ext_i - 2):ext_i + 1].min())
            if f5[j]:
                beh = '5M전환'
            elif f15[j]:
                beh = '15M전환'
            elif (c5[j] > line) if d > 0 else (c5[j] < line):
                beh = '가격선돌파'
            if beh:
                j_sig = j
                break
        if beh is None:
            beh, j_sig = '1H전환', b5 - 1
            seg = slice(a5, b5)
            ext_v = l5[seg].min() if d > 0 else h5[seg].max()
        e = j_sig + 1
        if e >= x5:
            continue
        entry = o5[e]
        stop = ext_v if (d > 0 and ext_v < entry) or (d < 0 and ext_v > entry) else None
        ret, why, _ = _simulate(d, entry, stop, None, h5[e:x5], l5[e:x5], o5[e:x5], o5[x5], cost)

        # 그림 (신호 시각까지의 1시간봉만: 신호가 속한 1시간봉은 아직 미완성이므로 그 전 봉까지)
        hk = max(z1, h.index.searchsorted(t5[j_sig] + M5, side='right') - 1)   # 마감된 마지막 1h봉 + 1
        bh = slice(z1, max(hk, z1 + 1))
        lowB = hl[bh] if d > 0 else hh[bh]
        ib = int(np.argmin(lowB) if d > 0 else np.argmax(lowB)) + z1
        near = np.where(np.abs((hl[bh] if d > 0 else hh[bh]) - ext_v) <= 0.25 * at)[0]
        tests = 0 if len(near) == 0 else 1 + int((np.diff(near) >= 2).sum())
        rng = hh[ib] - hl[ib]
        wick = (min(ho[ib], hc[ib]) - hl[ib]) if d > 0 else (hh[ib] - max(ho[ib], hc[ib]))
        if rng >= 1.5 * at and wick >= 0.5 * rng:
            shape = '급쏠림꼬리'
        elif tests >= 3:
            shape = '여러번시험'
        elif tests == 2:
            shape = '재시험'
        else:
            shape = '단일극점'
        ea = float(r['ea'])
        a_move = (ea - hc[z0]) * d / at
        retr = (ea - ext_v) * d / max((ea - hc[z0]) * d, 1e-9)
        depth = '깊은' if retr >= 1.0 else '얕은'
        strength = '강한A' if a_move >= 2.0 else '약한A'
        rows.append({
            'zc2': h.index[z2], 'signal_time': t5[j_sig] + M5, 'entry_time': t5[e], 'exit_time': t5[x5],
            'side': '롱' if d > 0 else '숏', 'behavior': beh, 'form': shape, 'depth': depth, 'strength': strength,
            'picture': f'{shape}·{depth}·{strength}',
            'early_vs_zc2_h': round((h.index[z2] + H - (t5[j_sig] + M5)) / H, 2),
            'stop_atr': round(abs(entry - ext_v) / at, 2), 'ret': ret, 'why': why,
            'gross': ret + 2 * cost, 'entry': entry, 'stop': ext_v,
        })
    return pd.DataFrame(rows)


def table(C: pd.DataFrame, by: List[str], fit_end: pd.Timestamp) -> pd.DataFrame:
    out = []
    for k, g in C.groupby(by):
        k = k if isinstance(k, tuple) else (k,)
        tr, te = g[g['entry_time'] < fit_end], g[g['entry_time'] >= fit_end]
        row = dict(zip(by, k))
        row.update({'건수': len(g), '롱비율': round(float((g['side'] == '롱').mean()), 2),
                    '손절률': round(float((g['why'] == '손절').mean()), 2),
                    '학습_건': len(tr), '학습_비용전%': round(float(tr['gross'].mean() * 100), 3) if len(tr) else np.nan,
                    '검증_건': len(te), '검증_비용전%': round(float(te['gross'].mean() * 100), 3) if len(te) else np.nan,
                    '검증_비용후%': round(float(te['ret'].mean() * 100), 3) if len(te) else np.nan,
                    '검증_승률': round(float((te['ret'] > 0).mean()), 2) if len(te) else np.nan})
        out.append(row)
    return pd.DataFrame(out)


def paths(df5: pd.DataFrame, C: pd.DataFrame) -> Dict[pd.Timestamp, list]:
    """사건별 1시간봉 종가 경로 ZC0→ZC3 (ZC0 종가 기준, ATR 배수, 숏은 뒤집음) — 표시용(사후 그림 포함)"""
    h = rd.resample(df5, '1h')
    w = find_windows(h)
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    c = h['close'].to_numpy()
    want = set(C['zc2'])
    out = {}
    for _, r in w.iterrows():
        z0, z1, z2, z3 = int(r['zc0']), int(r['zc1']), int(r['zc2']), int(r['zc3'])
        t = h.index[z2]
        if t not in want or z3 < 0:
            continue
        d, at = float(r['dir']), atr[z2]
        y = ((c[z0:z3 + 1] - c[z0]) / at * d).round(2).tolist()
        out[t] = [y, z1 - z0, z2 - z0]
    return out
