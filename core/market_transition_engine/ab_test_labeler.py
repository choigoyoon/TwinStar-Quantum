#!/usr/bin/env python3
"""
Labeler A/B Test - horizon × min_pct 6가지 조합
=================================================
transition_builder 는 건드리지 않는다.
동일한 candidates 에 대해 labeler 의 파라미터만 바꿔서 재라벨링한다.

출력 4개 표:
  표1) 조합별 n, precision, nothing%, decisive%, MFE, MAE
  표2) bull_to_bear / bear_to_bull / trend_weakening 분리
  표3) baseline 대비 delta
  표4) 최종 추천안
"""

import sys, os, time, logging
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.market_transition_engine.background_builder import BackgroundBuilder
from core.market_transition_engine.lh_builder import LHBuilder
from core.market_transition_engine.divergence_builder import DivergenceBuilder
from core.market_transition_engine.zone_builder import ZoneBuilder
from core.market_transition_engine.trend_builder import TrendBuilder
from core.market_transition_engine.transition_builder import TransitionBuilder
from core.market_transition_engine.types import (
    LabelVerdict, TransitionCandidate, TransitionLabel, TrendDirection,
)
from core.market_transition_engine.config import LABEL_HORIZON

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("ab_test")
logger.setLevel(logging.INFO)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Parametric labeler (no class structure change)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def label_with_params(
    close: np.ndarray,
    candidates: list[TransitionCandidate],
    horizon: int,
    min_pct: float,
) -> list[TransitionLabel]:
    """Same logic as Labeler.label() but with parametric horizon/min_pct."""
    n = len(close)
    labels = []
    for cand in candidates:
        t = cand.t
        t_h = t + horizon
        if t >= n or t_h >= n:
            continue
        p_t = close[t]
        p_h = close[t_h]
        if p_t == 0:
            continue
        pct = (p_h - p_t) / p_t

        # expected direction
        if cand.trend_before.direction == TrendDirection.BEARISH:
            expected_up = True
        elif cand.trend_before.direction == TrendDirection.BULLISH:
            expected_up = False
        else:
            expected_up = None

        if expected_up is None:
            matched = False
        elif expected_up:
            matched = pct > 0
        else:
            matched = pct < 0

        abs_pct = abs(pct)
        if abs_pct < min_pct:
            verdict = LabelVerdict.AMBIGUOUS
        elif matched:
            verdict = LabelVerdict.CONFIRMED
        else:
            verdict = LabelVerdict.DENIED

        labels.append(TransitionLabel(
            t=t, verdict=verdict, price_at_t=p_t,
            price_at_horizon=p_h, pct_change=pct,
            direction_matched=matched,
        ))
    return labels


def compute_mfe_mae(close: np.ndarray, candidates, labels, horizon):
    """MFE = best favorable excursion, MAE = worst adverse excursion in [t, t+horizon]."""
    n = len(close)
    mfe_vals, mae_vals = [], []
    for cand, lbl in zip(candidates, labels):
        t = cand.t
        t_h = min(t + horizon, n - 1)
        if t >= n or t + 1 >= n:
            continue
        window = close[t:t_h + 1]
        p_t = close[t]
        if p_t == 0:
            continue

        # expected direction
        if cand.trend_before.direction == TrendDirection.BEARISH:
            expected_up = True
        elif cand.trend_before.direction == TrendDirection.BULLISH:
            expected_up = False
        else:
            expected_up = None

        pcts = (window - p_t) / p_t
        if expected_up is True:
            mfe_vals.append(np.max(pcts))
            mae_vals.append(np.min(pcts))
        elif expected_up is False:
            mfe_vals.append(-np.min(pcts))
            mae_vals.append(-np.max(pcts))
        else:
            mfe_vals.append(np.max(np.abs(pcts)))
            mae_vals.append(-np.max(np.abs(pcts)))

    return (
        np.mean(mfe_vals) if mfe_vals else 0.0,
        np.mean(mae_vals) if mae_vals else 0.0,
    )


def analyze_directional(candidates, labels):
    """bull_to_bear / bear_to_bull / neutral breakdown."""
    groups = {"bull_to_bear": [], "bear_to_bull": [], "neutral": []}
    for c, l in zip(candidates, labels):
        d = c.trend_before.direction
        if d == TrendDirection.BULLISH:
            groups["bull_to_bear"].append(l)
        elif d == TrendDirection.BEARISH:
            groups["bear_to_bull"].append(l)
        else:
            groups["neutral"].append(l)
    result = {}
    for key, lbls in groups.items():
        n = len(lbls)
        conf = sum(1 for l in lbls if l.verdict == LabelVerdict.CONFIRMED)
        den = sum(1 for l in lbls if l.verdict == LabelVerdict.DENIED)
        amb = sum(1 for l in lbls if l.verdict == LabelVerdict.AMBIGUOUS)
        denom = conf + den
        result[key] = {
            "n": n, "confirmed": conf, "denied": den, "ambiguous": amb,
            "precision": conf / denom if denom > 0 else 0.0,
            "nothing_pct": amb / n * 100 if n > 0 else 0.0,
        }
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Main
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    # Load data
    df = pd.read_parquet("storage/bybit_btcusdt_15m.parquet")
    logger.info(f"Data: {len(df)} rows, ${df['close'].min():.0f}-${df['close'].max():.0f}")
    close = df["close"].values

    # Build pipeline once (transition_builder untouched)
    logger.info("Building pipeline (one-time)...")
    t0 = time.time()
    bg = BackgroundBuilder(); bg.build(df)
    lh = LHBuilder(); pivots = lh.build(df, tf=1)
    div = DivergenceBuilder(); divs = div.build(df, pivots)
    zb = ZoneBuilder(); zb.build(df, bg, pivots)
    tb = TrendBuilder()
    trans = TransitionBuilder()
    candidates = trans.build(df, pivots, zb, tb, divs)
    logger.info(f"Pipeline done: {len(candidates)} candidates in {time.time()-t0:.1f}s")

    # ── A/B test grid ──
    combos = [
        (16, 0.002),
        (16, 0.003),
        (16, 0.005),  # baseline
        (24, 0.002),
        (24, 0.003),
        (24, 0.005),
    ]

    baseline_key = (16, 0.005)
    results = {}

    for horizon, min_pct in combos:
        labels = label_with_params(close, candidates, horizon, min_pct)
        n_labels = len(labels)
        conf = sum(1 for l in labels if l.verdict == LabelVerdict.CONFIRMED)
        den = sum(1 for l in labels if l.verdict == LabelVerdict.DENIED)
        amb = sum(1 for l in labels if l.verdict == LabelVerdict.AMBIGUOUS)
        denom_cd = conf + den
        prec = conf / denom_cd if denom_cd > 0 else 0.0
        nothing = amb / n_labels * 100 if n_labels > 0 else 0.0
        decisive = denom_cd / n_labels * 100 if n_labels > 0 else 0.0
        mfe, mae = compute_mfe_mae(close, candidates, labels, horizon)
        directional = analyze_directional(candidates, labels)

        results[(horizon, min_pct)] = {
            "n": n_labels, "confirmed": conf, "denied": den, "ambiguous": amb,
            "precision": prec, "nothing_pct": nothing, "decisive_pct": decisive,
            "mfe": mfe, "mae": mae, "directional": directional,
        }

    baseline = results[baseline_key]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Table 1: 조합별 요약
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    sep = "=" * 100
    print(f"\n{sep}")
    print("  [표1] 조합별 n / precision / nothing% / decisive% / MFE / MAE")
    print(sep)
    hdr = f"  {'combo':>18}  {'n':>5}  {'prec':>8}  {'nothing%':>9}  {'decisive%':>10}  {'MFE':>8}  {'MAE':>8}"
    print(hdr)
    print("  " + "-" * 90)
    for (h, mp), r in sorted(results.items()):
        tag = "★ baseline" if (h, mp) == baseline_key else ""
        print(f"  h={h:2d} min={mp:.3f}  {r['n']:5d}  {r['precision']:8.4f}  "
              f"{r['nothing_pct']:8.1f}%  {r['decisive_pct']:9.1f}%  "
              f"{r['mfe']:8.4f}  {r['mae']:8.4f}  {tag}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Table 2: 방향별 분해
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n{sep}")
    print("  [표2] bull_to_bear / bear_to_bull / neutral 분리")
    print(sep)
    hdr2 = f"  {'combo':>18}  {'dir':>13}  {'n':>4}  {'C':>4}  {'D':>4}  {'A':>4}  {'prec':>7}  {'nothing%':>9}"
    print(hdr2)
    print("  " + "-" * 90)
    for (h, mp), r in sorted(results.items()):
        for dname in ["bull_to_bear", "bear_to_bull", "neutral"]:
            d = r["directional"][dname]
            tag = ""
            if (h, mp) == baseline_key:
                tag = "★"
            print(f"  h={h:2d} min={mp:.3f}  {dname:>13}  {d['n']:4d}  "
                  f"{d['confirmed']:4d}  {d['denied']:4d}  {d['ambiguous']:4d}  "
                  f"{d['precision']:7.4f}  {d['nothing_pct']:8.1f}%  {tag}")
        print("  " + "·" * 90)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Table 3: baseline 대비 delta
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n{sep}")
    print(f"  [표3] Baseline (h={baseline_key[0]}, min={baseline_key[1]}) 대비 delta")
    print(sep)
    hdr3 = f"  {'combo':>18}  {'Δn':>6}  {'Δn%':>7}  {'Δprec':>8}  {'Δnothing':>9}  {'Δdecisive':>10}  {'ΔMFE':>8}  {'ΔMAE':>8}"
    print(hdr3)
    print("  " + "-" * 90)
    for (h, mp), r in sorted(results.items()):
        dn = r["n"] - baseline["n"]
        dn_pct = dn / baseline["n"] * 100 if baseline["n"] > 0 else 0
        dp = r["precision"] - baseline["precision"]
        dno = r["nothing_pct"] - baseline["nothing_pct"]
        dde = r["decisive_pct"] - baseline["decisive_pct"]
        dmfe = r["mfe"] - baseline["mfe"]
        dmae = r["mae"] - baseline["mae"]
        tag = "★ baseline" if (h, mp) == baseline_key else ""
        fail_sig = "⚠️ >10% loss" if dn_pct < -10 else ""
        print(f"  h={h:2d} min={mp:.3f}  {dn:+6d}  {dn_pct:+6.1f}%  {dp:+8.4f}  "
              f"{dno:+8.1f}pp  {dde:+9.1f}pp  {dmfe:+8.4f}  {dmae:+8.4f}  {tag} {fail_sig}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Table 4: 최종 추천
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n{sep}")
    print("  [표4] 최종 추천안")
    print(sep)

    # Scoring: each criterion
    # 1. 신호 수 감소 10% 이내 (must pass)
    # 2. decisive% 상승 (higher = better)
    # 3. bull/bear 균형 (smaller gap = better)
    # 4. precision 하락 최소 (higher = better)
    # 5. nothing% 의미 있게 감소 (lower = better)

    print("\n  판정 기준별 평가:")
    print(f"  {'combo':>18}  {'①sig<10%':>9}  {'②deci↑':>7}  {'③balance':>9}  {'④prec':>7}  {'⑤noth↓':>7}  {'SCORE':>6}")
    print("  " + "-" * 80)

    best_score = -999
    best_combo = baseline_key

    for (h, mp), r in sorted(results.items()):
        dn_pct = (r["n"] - baseline["n"]) / baseline["n"] * 100 if baseline["n"] > 0 else 0
        c1_pass = dn_pct >= -10  # must pass
        c1 = "PASS" if c1_pass else "FAIL"

        c2_val = r["decisive_pct"] - baseline["decisive_pct"]
        c3_b2b = r["directional"]["bull_to_bear"]["precision"]
        c3_b2br = r["directional"]["bear_to_bull"]["precision"]
        c3_gap = abs(c3_b2b - c3_b2br)
        c4_val = r["precision"] - baseline["precision"]
        c5_val = baseline["nothing_pct"] - r["nothing_pct"]  # positive = improvement

        # Score
        if not c1_pass:
            total = -999
        else:
            total = 0
            total += min(c2_val / 5, 3)     # decisive improvement, cap at 3
            total += max(-c3_gap * 10, -2)   # balance penalty
            total += min(c4_val * 50, 2)     # precision bonus/penalty
            total += min(c5_val / 5, 3)      # nothing reduction, cap at 3

        tag = ""
        if (h, mp) == baseline_key:
            tag = "★ baseline"
        if total > best_score and (h, mp) != baseline_key:
            best_score = total
            best_combo = (h, mp)

        print(f"  h={h:2d} min={mp:.3f}  {c1:>9}  {c2_val:+6.1f}pp  gap={c3_gap:.3f}  "
              f"{c4_val:+7.4f}  {c5_val:+6.1f}pp  {total:6.2f}  {tag}")

    # Check if best beats baseline
    bl_score_val = 0  # baseline score is 0 by definition
    best_r = results[best_combo]
    bl_r = results[baseline_key]

    print(f"\n  ──────────────────────────────────────────────")
    print(f"  최종 추천: h={best_combo[0]}, min_pct={best_combo[1]}")
    print(f"  ──────────────────────────────────────────────")

    # Final comparison
    print(f"\n  {'':>20}  {'Baseline':>12}  {'추천안':>12}  {'delta':>12}")
    print(f"  {'n':>20}  {bl_r['n']:>12}  {best_r['n']:>12}  {best_r['n']-bl_r['n']:>+12}")
    print(f"  {'precision':>20}  {bl_r['precision']:>12.4f}  {best_r['precision']:>12.4f}  {best_r['precision']-bl_r['precision']:>+12.4f}")
    print(f"  {'nothing%':>20}  {bl_r['nothing_pct']:>11.1f}%  {best_r['nothing_pct']:>11.1f}%  {best_r['nothing_pct']-bl_r['nothing_pct']:>+11.1f}pp")
    print(f"  {'decisive%':>20}  {bl_r['decisive_pct']:>11.1f}%  {best_r['decisive_pct']:>11.1f}%  {best_r['decisive_pct']-bl_r['decisive_pct']:>+11.1f}pp")
    print(f"  {'MFE':>20}  {bl_r['mfe']:>12.4f}  {best_r['mfe']:>12.4f}  {best_r['mfe']-bl_r['mfe']:>+12.4f}")
    print(f"  {'MAE':>20}  {bl_r['mae']:>12.4f}  {best_r['mae']:>12.4f}  {best_r['mae']-bl_r['mae']:>+12.4f}")

    # Judgment
    dp = best_r["precision"] - bl_r["precision"]
    dn_pct = (best_r["n"] - bl_r["n"]) / bl_r["n"] * 100 if bl_r["n"] > 0 else 0
    d_nothing = best_r["nothing_pct"] - bl_r["nothing_pct"]

    adopt = (
        dn_pct >= -10
        and d_nothing < -3  # meaningful nothing% reduction
        and dp > -0.05      # precision doesn't crash
    )

    print(f"\n  ──────────────────────────────────────────────")
    if adopt:
        print(f"  ✅ 채택: h={best_combo[0]}, LABEL_MIN_PCT={best_combo[1]}")
        print(f"  근거: 신호 수 {dn_pct:+.1f}%, nothing% {d_nothing:+.1f}pp, precision {dp:+.4f}")
    else:
        print(f"  ⊘ 현재 baseline 유지 (h=16, min=0.005)")
        if dn_pct < -10:
            print(f"    → 신호 수 {dn_pct:.1f}% 감소 (10% 초과)")
        if d_nothing >= -3:
            print(f"    → nothing% 개선 {d_nothing:.1f}pp (3pp 미만)")
        if dp <= -0.05:
            print(f"    → precision 하락 {dp:.4f} (5pp 초과)")
    print(f"  ──────────────────────────────────────────────")


if __name__ == "__main__":
    main()
