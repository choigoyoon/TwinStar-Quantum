"""
ZC 범위 건별 루프 분석 (1h 구조 + 15m 분할 체결)

범위 하나 = 매매 한 건.
  구조(1h):   ZC0 →(1) EA →(2) ZC1 →(3) EB →(4) ZC2 →(5 매매) ZC3
  체결(15m):  진입 = ZC2 1h봉 마감 직후 15m 시가, 보유 중 손절/목표는 15m 고저로 판정
              같은 15m봉에서 손절과 목표가 모두 닿으면 손절 먼저 (보수적)

건마다 기록
  - 구조 5단계의 길이(봉)와 이동폭(ATR 배수)
  - 진입 후 최대 유리 이동(MFE)·최대 불리 이동(MAE)과 그 시각
  - 사후 최적: 그 건에서 가능했던 최선(롱/숏/건너뜀) — '정답지', 당시엔 알 수 없음
  - 청산 규칙별 결과: ZC3 보유 / 구조 손절(EB) / 구조 손절 + 목표 n×ATR / 건너뜀
  - 학습 매매: 그 시점까지 결과가 확정된 과거 건들만 보고 고른 규칙과 그 결과
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from research import data as rd
from research.zc_pattern import find_windows

TARGETS = (1.0, 1.5, 2.0, 3.0)
RULES: List[str] = ['hold_zc3', 'stop_eb'] + [f'stop_eb_tp{t:g}' for t in TARGETS]


def _simulate(side: float, entry: float, stop: Optional[float], target: Optional[float],
              hi: np.ndarray, lo: np.ndarray, op: np.ndarray, exit_open: float, cost: float) -> Tuple[float, str, int]:
    """15m 봉 배열 위에서 한 건 시뮬레이션 → (비용 후 수익, 청산 사유, 청산 15m 인덱스)"""
    for j in range(len(hi)):
        if stop is not None:
            hit = lo[j] <= stop if side > 0 else hi[j] >= stop
            if hit:
                px = min(stop, op[j]) if side > 0 else max(stop, op[j])   # 갭이면 시가 체결
                return side * (px / entry - 1) - 2 * cost, '손절', j
        if target is not None:
            hit = hi[j] >= target if side > 0 else lo[j] <= target
            if hit:
                px = max(target, op[j]) if side > 0 else min(target, op[j])
                return side * (px / entry - 1) - 2 * cost, '목표', j
    return side * (exit_open / entry - 1) - 2 * cost, 'ZC3', len(hi)


def ledger(df15: pd.DataFrame, tf: str = '1h', cost: float = 0.00115) -> pd.DataFrame:
    """심볼 하나의 건별 장부"""
    h = rd.resample(df15, tf)
    bar = pd.Timedelta(pd.tseries.frequencies.to_offset(tf))
    w = find_windows(h)
    if w.empty:
        return w
    tr = pd.concat([h['high'] - h['low'], (h['high'] - h['close'].shift()).abs(),
                    (h['low'] - h['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    hc = h['close'].to_numpy()
    t15 = df15.index
    o15, h15, l15 = df15['open'].to_numpy(), df15['high'].to_numpy(), df15['low'].to_numpy()

    rows = []
    for _, r in w.iterrows():
        z0, z1, z2, z3 = int(r['zc0']), int(r['zc1']), int(r['zc2']), int(r['zc3'])
        if z3 < 0 or z3 + 1 >= len(h):
            continue                                           # 아직 끝나지 않은 범위
        d, at = float(r['dir']), float(atr[z2])
        t_in, t_out = h.index[z2] + bar, h.index[z3] + bar    # 진입 = ZC2 마감, 청산 = ZC3 마감
        a, b = t15.searchsorted(t_in), t15.searchsorted(t_out)
        if a >= len(t15) or b >= len(t15) or b <= a:
            continue
        entry, exit_open = o15[a], o15[b]
        hi, lo, op = h15[a:b], l15[a:b], o15[a:b]
        fav = (hi.max() / entry - 1) if d > 0 else (1 - lo.min() / entry)
        adv = (1 - lo.min() / entry) if d > 0 else (hi.max() / entry - 1)
        j_fav = int(hi.argmax() if d > 0 else lo.argmin())
        eb = float(r['eb'])
        row = {
            'symbol': None, 'zc0': h.index[z0], 'zc1': h.index[z1], 'zc2': h.index[z2], 'zc3': h.index[z3],
            'entry_time': t15[a], 'exit_time': t15[b], 'dir': '롱' if d > 0 else '숏', 'side': d,
            'entry': entry, 'atr': at, 'ea': float(r['ea']), 'eb': eb,
            # 구조 5단계 (봉 수, ATR 배수; 방향 기준 + = 새 방향으로의 이동)
            'p1_bars': int(r['ea_bar']) - z0, 'p1_move': (r['ea'] - hc[z0]) / at * d,
            'p2_bars': z1 - int(r['ea_bar']), 'p2_move': (hc[z1] - r['ea']) / at * d,
            'p3_bars': int(r['eb_bar']) - z1, 'p3_move': (eb - hc[z1]) / at * d,
            'p4_bars': z2 - int(r['eb_bar']), 'p4_move': (hc[z2] - eb) / at * d,
            'p5_bars_1h': z3 - z2,
            'mfe_atr': fav * entry / at, 'mae_atr': adv * entry / at,
            'mfe_time_frac': j_fav / max(len(hi) - 1, 1),
            'stop_dist_atr': abs(entry - eb) / at,
        }
        # 청산 규칙별 결과 (기본 방향)
        stop = eb if (d > 0 and eb < entry) or (d < 0 and eb > entry) else None
        res = {}
        res['hold_zc3'] = _simulate(d, entry, None, None, hi, lo, op, exit_open, cost)
        res['stop_eb'] = _simulate(d, entry, stop, None, hi, lo, op, exit_open, cost)
        for t in TARGETS:
            res[f'stop_eb_tp{t:g}'] = _simulate(d, entry, stop, entry + d * t * at, hi, lo, op, exit_open, cost)
        for k, (ret, why, j) in res.items():
            row[f'r_{k}'] = ret
            row[f'why_{k}'] = why
            # 결과 확정 시각: 청산 체결 15m봉 마감 (ZC3 청산이면 ZC3 다음 15m봉)
            jj = min(a + j, len(t15) - 1)
            row[f'known_{k}'] = t15[jj] + pd.Timedelta(minutes=15)
        # 사후 최적 ('정답지'): 진입 후 최선의 지점에서 청산했다면
        long_best = (hi.max() / entry - 1) - 2 * cost
        short_best = (1 - lo.min() / entry) - 2 * cost
        best = max(long_best, short_best, 0.0)
        row['hind_best'] = best
        row['hind_action'] = '건너뜀' if best == 0.0 else ('롱' if long_best >= short_best else '숏')
        rows.append(row)
    return pd.DataFrame(rows)


def learn_rule(L: pd.DataFrame, lookback: Optional[int] = None, min_past: int = 30) -> pd.DataFrame:
    """
    건마다 '그 시점까지 결과가 확정된 과거 건'의 규칙별 평균 수익을 보고 가장 좋은 규칙을 고름.
    모든 규칙의 과거 평균이 0 이하면 건너뜀. lookback=N이면 최근 N건만 참고.
    """
    L = L.sort_values('entry_time').reset_index(drop=True)
    choice, result = [], []
    for i in range(len(L)):
        t = L.at[i, 'entry_time']
        means = {}
        for k in RULES:
            past = L[L[f'known_{k}'] <= t]
            if lookback:
                past = past.tail(lookback)
            if len(past) >= min_past:
                means[k] = past[f'r_{k}'].mean()
        if not means:
            choice.append('학습중')
            result.append(0.0)
            continue
        best = max(means, key=lambda k: means[k])
        if means[best] <= 0:
            choice.append('건너뜀')
            result.append(0.0)
        else:
            choice.append(best)
            result.append(L.at[i, f'r_{best}'])
    L['learned_rule'] = choice
    L['learned_ret'] = result
    return L


def run(data15: Dict[str, pd.DataFrame], tf: str = '1h', cost: float = 0.00115,
        lookback: Optional[int] = None) -> pd.DataFrame:
    parts = []
    for sym, df in data15.items():
        L = ledger(df, tf, cost)
        if not L.empty:
            L['symbol'] = sym
            parts.append(L)
    if not parts:
        return pd.DataFrame()
    return learn_rule(pd.concat(parts, ignore_index=True), lookback=lookback)


def trade_card(r: pd.Series) -> str:
    """건별 보고 한 장 (마크다운)"""
    rule = {'hold_zc3': 'ZC3까지 보유', 'stop_eb': 'EB 손절', **{f'stop_eb_tp{t:g}': f'EB 손절 + {t:g}ATR 목표' for t in TARGETS}}
    lr = r['learned_rule']
    taken = lr in rule
    return '\n'.join([
        f"### {r['symbol']} {r['zc2']:%Y-%m-%d %H:%M} {r['dir']}",
        f"- 구조: ZC0 {r['zc0']:%m-%d %H시} → EA {r['p1_bars']}봉 {r['p1_move']:+.1f}ATR → ZC1 {r['p2_bars']}봉 → "
        f"EB {r['p3_bars']}봉 {r['p3_move']:+.1f}ATR → ZC2 {r['p4_bars']}봉 {r['p4_move']:+.1f}ATR",
        f"- 진입 {r['entry_time']:%m-%d %H:%M} {r['entry']:,.1f} · 손절선(EB) {r['eb']:,.1f} ({r['stop_dist_atr']:.1f}ATR) · "
        f"보유 {r['p5_bars_1h']}시간 · 최대유리 {r['mfe_atr']:+.1f}ATR · 최대불리 {r['mae_atr']:.1f}ATR",
        f"- 규칙별: ZC3보유 {r['r_hold_zc3']:+.2%} · EB손절 {r['r_stop_eb']:+.2%} · +1.5ATR목표 {r['r_stop_eb_tp1.5']:+.2%}",
        f"- 사후 최적: {r['hind_action']} {r['hind_best']:+.2%} (당시엔 알 수 없음)",
        f"- 학습 매매(과거만 보고 결정): {rule[lr] if taken else lr} → {r['learned_ret']:+.2%}",
    ])


def main() -> None:
    """python -m research.zc_trades --data <파일|폴더> --out docs/research/zc"""
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', default='docs/research/zc')
    ap.add_argument('--cost', type=float, default=0.00115)
    ap.add_argument('--lookback', type=int, default=0, help='학습 규칙이 참고할 최근 건수 (0=전부)')
    a = ap.parse_args()
    p = Path(a.data)
    raw = rd.load_dir(p) if p.is_dir() else {p.stem.split('_')[1].upper() if '_' in p.stem else p.stem: rd.load_ohlcv(p)}
    for s, d in raw.items():
        q = rd.check_quality(d)
        if any('합성' in i for i in q.issues):
            raise SystemExit(f"{s}: 합성/테스트 데이터로 보여 중단")
    L = run(raw, cost=a.cost, lookback=a.lookback or None)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    span = f"{L['entry_time'].min():%Y-%m}_{L['entry_time'].max():%Y-%m}"
    L.drop(columns=[c for c in L.columns if c.startswith('known_')]).to_csv(out / f'ledger_{span}.csv', index=False)
    cards = [trade_card(r) for _, r in L.sort_values('entry_time').iterrows()]
    (out / f'trades_{span}.md').write_text(
        f"# ZC 범위 건별 보고 ({span}, {len(L)}건)\n\n" + '\n\n'.join(cards) + '\n', encoding='utf-8')
    print(f"{len(L)}건 → {out}/ledger_{span}.csv, trades_{span}.md")


if __name__ == '__main__':
    main()
