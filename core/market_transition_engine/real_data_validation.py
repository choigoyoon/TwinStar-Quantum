"""
Market Transition Engine - Real Data Validation
=================================================
실제 BTC 15분봉 데이터로 전체 파이프라인을 검증한다.

출력: 표1(기본 실행), 표2(검증 결과), 표3(score 분포), 표4(구조 체크)
"""
from __future__ import annotations

import logging
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

# ── 모듈 import ────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.market_transition_engine.config import (
    SCORE_THRESHOLD, DULLING_RATIO, LABEL_HORIZON, MAX_TF,
)
from core.market_transition_engine.types import (
    TransitionCandidate, TransitionLabel, TransitionType,
    TrendDirection, LabelVerdict, PivotType,
)
from core.market_transition_engine.data_loader import aggregate_tf
from core.market_transition_engine.background_builder import BackgroundBuilder
from core.market_transition_engine.lh_builder import LHBuilder, get_pivots_known_at
from core.market_transition_engine.divergence_builder import (
    DivergenceBuilder, get_max_chain_at,
)
from core.market_transition_engine.zone_builder import ZoneBuilder
from core.market_transition_engine.trend_builder import TrendBuilder
from core.market_transition_engine.transition_builder import TransitionBuilder
from core.market_transition_engine.score_engine import ScoreEngine
from core.market_transition_engine.labeler import Labeler
from core.market_transition_engine.backtest_report import BacktestReport

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Result containers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SingleTFResult:
    tf: int
    n_rows: int = 0
    n_pivots: int = 0
    n_pivots_high: int = 0
    n_pivots_low: int = 0
    n_divergences: int = 0
    n_div_bull: int = 0
    n_div_bear: int = 0
    n_zones: int = 0
    n_zone_from_bg: int = 0
    n_zone_from_lh: int = 0
    n_bg_candidates: int = 0
    n_bg_events: int = 0
    n_zone_events: int = 0
    n_transitions: int = 0
    n_labeled: int = 0
    n_confirmed: int = 0
    n_denied: int = 0
    n_ambiguous: int = 0
    precision: float = 0.0
    # Directional precision
    bull_to_bear_total: int = 0
    bull_to_bear_confirmed: int = 0
    bear_to_bull_total: int = 0
    bear_to_bull_confirmed: int = 0
    neutral_total: int = 0
    # Trend weakening stats
    trend_weakening_total: int = 0
    trend_weakening_confirmed: int = 0
    # Score distribution
    score_dist: dict[int, int] = field(default_factory=dict)
    score_precision: dict[int, float] = field(default_factory=dict)
    # MFE / MAE
    mfe_values: list[float] = field(default_factory=list)
    mae_values: list[float] = field(default_factory=list)
    # Timing / memory
    elapsed_sec: float = 0.0
    peak_mem_mb: float = 0.0
    # Explanation score stats
    expl_scores: list[float] = field(default_factory=list)
    # Transition type counts
    type_reversal: int = 0
    type_bounce: int = 0
    type_continuation: int = 0
    # Structure check
    n_bg_promoted: int = 0
    n_recent_zones: int = 0
    n_mid_zones: int = 0
    n_old_zones: int = 0
    # Error
    error: Optional[str] = None


def run_single_tf(df_15m: pd.DataFrame, tf: int) -> SingleTFResult:
    """단일 TF 파이프라인 실행 + 전체 메트릭 수집"""
    result = SingleTFResult(tf=tf, n_rows=len(df_15m))
    close = df_15m["close"].values
    n = len(close)

    tracemalloc.start()
    t0 = time.time()

    try:
        # Stage 1: Background
        bg_builder = BackgroundBuilder()
        bg_builder.build(df_15m)
        result.n_bg_candidates = len(bg_builder.candidates)
        result.n_bg_events = len(bg_builder.events)

        # Stage 2a: L/H
        lh_builder = LHBuilder()
        pivots = lh_builder.build(df_15m, tf=tf)
        result.n_pivots = len(pivots)
        result.n_pivots_high = sum(1 for p in pivots if p.pivot_type == PivotType.HIGH)
        result.n_pivots_low = sum(1 for p in pivots if p.pivot_type == PivotType.LOW)

        # Stage 2b: Divergence
        div_builder = DivergenceBuilder()
        divergences = div_builder.build(df_15m, pivots, tf=tf)
        result.n_divergences = len(divergences)
        from core.market_transition_engine.types import DivergenceType
        result.n_div_bull = sum(1 for d in divergences if d.div_type == DivergenceType.BULLISH)
        result.n_div_bear = sum(1 for d in divergences if d.div_type == DivergenceType.BEARISH)

        # Stage 3a: Zones
        zone_builder = ZoneBuilder()
        zone_builder.build(df_15m, bg_builder, pivots)
        result.n_zones = len(zone_builder.zones)
        result.n_zone_from_bg = sum(1 for z in zone_builder.zones if z.from_background)
        result.n_zone_from_lh = sum(1 for z in zone_builder.zones if not z.from_background)
        result.n_zone_events = len(zone_builder.events)
        result.n_bg_promoted = result.n_zone_from_bg  # bg→zone promoted count

        # Zone age analysis (recent / mid / old)
        last_t = n - 1
        for z in zone_builder.zones:
            age = last_t - z.born_at
            if age < 500:
                result.n_recent_zones += 1
            elif age < 5000:
                result.n_mid_zones += 1
            else:
                result.n_old_zones += 1

        # Stage 3b: Trend
        trend_builder = TrendBuilder()

        # Stage 4a: Transition
        trans_builder = TransitionBuilder()
        candidates = trans_builder.build(
            df_15m, pivots, zone_builder, trend_builder, divergences
        )
        result.n_transitions = len(candidates)

        # Transition type counts
        for c in candidates:
            if c.transition_type == TransitionType.TREND_REVERSAL:
                result.type_reversal += 1
            elif c.transition_type == TransitionType.SINGLE_BOUNCE:
                result.type_bounce += 1
            else:
                result.type_continuation += 1

        # Directional breakdown
        for c in candidates:
            if c.trend_before.direction == TrendDirection.BULLISH:
                result.bull_to_bear_total += 1
            elif c.trend_before.direction == TrendDirection.BEARISH:
                result.bear_to_bull_total += 1
            else:
                result.neutral_total += 1

        # Trend weakening
        result.trend_weakening_total = sum(
            1 for c in candidates if c.dulling_intensity >= DULLING_RATIO
        )

        # Score engine (explanation only)
        score_engine = ScoreEngine()
        candidates = score_engine.score_all(candidates)
        result.expl_scores = [c.explanation_score for c in candidates]

        # Score distribution
        for c in candidates:
            result.score_dist[c.score] = result.score_dist.get(c.score, 0) + 1

        # Labeling
        labeler = Labeler()
        labels = labeler.label(df_15m, candidates)
        result.n_labeled = len(labels)
        result.n_confirmed = sum(1 for l in labels if l.verdict == LabelVerdict.CONFIRMED)
        result.n_denied = sum(1 for l in labels if l.verdict == LabelVerdict.DENIED)
        result.n_ambiguous = sum(1 for l in labels if l.verdict == LabelVerdict.AMBIGUOUS)

        denom = result.n_confirmed + result.n_denied
        result.precision = result.n_confirmed / denom if denom > 0 else 0.0

        # Per-score precision
        label_map = {l.t: l for l in labels}
        for score_val in sorted(result.score_dist.keys()):
            scored_cands = [c for c in candidates if c.score == score_val]
            conf = sum(1 for c in scored_cands
                       if c.t in label_map and label_map[c.t].verdict == LabelVerdict.CONFIRMED)
            den = sum(1 for c in scored_cands
                      if c.t in label_map and label_map[c.t].verdict == LabelVerdict.DENIED)
            result.score_precision[score_val] = conf / (conf + den) if (conf + den) > 0 else 0.0

        # Directional precision
        for c in candidates:
            label = label_map.get(c.t)
            if not label:
                continue
            if c.trend_before.direction == TrendDirection.BULLISH:
                if label.verdict == LabelVerdict.CONFIRMED:
                    result.bull_to_bear_confirmed += 1
            elif c.trend_before.direction == TrendDirection.BEARISH:
                if label.verdict == LabelVerdict.CONFIRMED:
                    result.bear_to_bull_confirmed += 1

        # Trend weakening precision
        for c in candidates:
            if c.dulling_intensity >= DULLING_RATIO:
                label = label_map.get(c.t)
                if label and label.verdict == LabelVerdict.CONFIRMED:
                    result.trend_weakening_confirmed += 1

        # MFE / MAE calculation (Maximum Favorable / Adverse Excursion over label horizon)
        for c in candidates:
            t = c.t
            end_t = min(t + LABEL_HORIZON, n - 1)
            if t >= n or end_t <= t:
                continue
            entry_price = close[t]
            if entry_price == 0:
                continue

            # Expected direction
            if c.trend_before.direction == TrendDirection.BEARISH:
                expected_up = True
            elif c.trend_before.direction == TrendDirection.BULLISH:
                expected_up = False
            else:
                continue  # skip neutral

            horizon_prices = close[t + 1: end_t + 1]
            if len(horizon_prices) == 0:
                continue

            pct_changes = (horizon_prices - entry_price) / entry_price

            if expected_up:
                mfe = float(np.max(pct_changes))
                mae = float(np.min(pct_changes))
            else:
                mfe = float(-np.min(pct_changes))
                mae = float(-np.max(pct_changes))

            result.mfe_values.append(mfe)
            result.mae_values.append(mae)

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"

    result.elapsed_sec = time.time() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.peak_mem_mb = peak / 1024 / 1024

    return result


def run_multi_tf_integrated(df_15m: pd.DataFrame, tf_list: list[int]) -> SingleTFResult:
    """
    TF=1~10 통합 실행: 각 TF에서 피벗을 모은 뒤 하나의 zone/transition으로 통합.
    """
    result = SingleTFResult(tf=0, n_rows=len(df_15m))
    close = df_15m["close"].values
    n = len(close)

    tracemalloc.start()
    t0 = time.time()

    try:
        # Stage 1
        bg_builder = BackgroundBuilder()
        bg_builder.build(df_15m)
        result.n_bg_candidates = len(bg_builder.candidates)

        # Stage 2: Collect pivots from all TFs
        lh_builder = LHBuilder()
        all_pivots = []
        all_divs = []
        div_builder = DivergenceBuilder()

        for tf in tf_list:
            try:
                pivots_tf = lh_builder.build(df_15m, tf=tf)
                all_pivots.extend(pivots_tf)
                divs_tf = div_builder.build(df_15m, pivots_tf, tf=tf)
                all_divs.extend(divs_tf)
            except ValueError:
                pass

        # Deduplicate pivots by (idx, pivot_type)
        seen = set()
        unique_pivots = []
        for p in all_pivots:
            key = (p.idx, p.pivot_type)
            if key not in seen:
                seen.add(key)
                unique_pivots.append(p)
        all_pivots = sorted(unique_pivots, key=lambda p: p.confirmed_at)

        result.n_pivots = len(all_pivots)
        result.n_divergences = len(all_divs)

        # Stage 3
        zone_builder = ZoneBuilder()
        zone_builder.build(df_15m, bg_builder, all_pivots)
        result.n_zones = len(zone_builder.zones)
        result.n_zone_from_bg = sum(1 for z in zone_builder.zones if z.from_background)
        result.n_zone_from_lh = sum(1 for z in zone_builder.zones if not z.from_background)

        trend_builder = TrendBuilder()

        # Stage 4
        trans_builder = TransitionBuilder()
        candidates = trans_builder.build(
            df_15m, all_pivots, zone_builder, trend_builder, all_divs
        )
        result.n_transitions = len(candidates)

        score_engine = ScoreEngine()
        candidates = score_engine.score_all(candidates)
        result.expl_scores = [c.explanation_score for c in candidates]

        for c in candidates:
            result.score_dist[c.score] = result.score_dist.get(c.score, 0) + 1

        # Labels
        labeler = Labeler()
        labels = labeler.label(df_15m, candidates)
        result.n_labeled = len(labels)
        result.n_confirmed = sum(1 for l in labels if l.verdict == LabelVerdict.CONFIRMED)
        result.n_denied = sum(1 for l in labels if l.verdict == LabelVerdict.DENIED)
        result.n_ambiguous = sum(1 for l in labels if l.verdict == LabelVerdict.AMBIGUOUS)

        denom = result.n_confirmed + result.n_denied
        result.precision = result.n_confirmed / denom if denom > 0 else 0.0

        # Score precision
        label_map = {l.t: l for l in labels}
        for score_val in sorted(result.score_dist.keys()):
            scored_cands = [c for c in candidates if c.score == score_val]
            conf = sum(1 for c in scored_cands
                       if c.t in label_map and label_map[c.t].verdict == LabelVerdict.CONFIRMED)
            den = sum(1 for c in scored_cands
                      if c.t in label_map and label_map[c.t].verdict == LabelVerdict.DENIED)
            result.score_precision[score_val] = conf / (conf + den) if (conf + den) > 0 else 0.0

    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"

    result.elapsed_sec = time.time() - t0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result.peak_mem_mb = peak / 1024 / 1024

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Print Tables
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_table1(results: dict[str, SingleTFResult]):
    """표1: 기본 실행 결과"""
    print()
    print("=" * 100)
    print("  표1. 기본 실행 결과 (Real BTC 15m Data)")
    print("=" * 100)
    header = f"{'TF':>8} {'Rows':>7} {'Pivots':>8} {'H/L':>10} {'Divs':>7} {'B/S':>10} {'Zones':>7} {'Bg/LH':>8} {'Trans':>7} {'Time(s)':>8} {'Mem(MB)':>8}"
    print(header)
    print("-" * 100)
    for name, r in results.items():
        if r.error:
            print(f"{name:>8} ERROR: {r.error}")
            continue
        hl = f"{r.n_pivots_high}/{r.n_pivots_low}"
        bs = f"{r.n_div_bull}/{r.n_div_bear}"
        bglh = f"{r.n_zone_from_bg}/{r.n_zone_from_lh}"
        print(f"{name:>8} {r.n_rows:>7} {r.n_pivots:>8} {hl:>10} {r.n_divergences:>7} {bs:>10} {r.n_zones:>7} {bglh:>8} {r.n_transitions:>7} {r.elapsed_sec:>8.2f} {r.peak_mem_mb:>8.1f}")
    print("=" * 100)


def print_table2(results: dict[str, SingleTFResult]):
    """표2: 검증 결과"""
    print()
    print("=" * 120)
    print("  표2. 검증 결과 (Precision / Directional / MFE / MAE)")
    print("=" * 120)
    header = (f"{'TF':>8} {'ALL prec':>10} {'b→s prec':>10} {'s→b prec':>10} "
              f"{'weak prec':>10} {'MFE avg':>10} {'MAE avg':>10} "
              f"{'nothing%':>10} {'decisive%':>10}")
    print(header)
    print("-" * 120)
    for name, r in results.items():
        if r.error:
            print(f"{name:>8} ERROR: {r.error}")
            continue

        # bull_to_bear precision
        b2b_prec = (r.bull_to_bear_confirmed / r.bull_to_bear_total
                    if r.bull_to_bear_total > 0 else 0.0)
        # bear_to_bull precision
        s2b_prec = (r.bear_to_bull_confirmed / r.bear_to_bull_total
                    if r.bear_to_bull_total > 0 else 0.0)
        # trend weakening precision
        tw_prec = (r.trend_weakening_confirmed / r.trend_weakening_total
                   if r.trend_weakening_total > 0 else 0.0)
        # MFE / MAE
        mfe_avg = float(np.mean(r.mfe_values)) if r.mfe_values else 0.0
        mae_avg = float(np.mean(r.mae_values)) if r.mae_values else 0.0
        # nothing% = ambiguous / labeled
        nothing_pct = (r.n_ambiguous / r.n_labeled * 100) if r.n_labeled > 0 else 0.0
        # decisive% = (confirmed + denied) / labeled
        decisive_pct = ((r.n_confirmed + r.n_denied) / r.n_labeled * 100) if r.n_labeled > 0 else 0.0

        print(f"{name:>8} {r.precision:>10.4f} {b2b_prec:>10.4f} {s2b_prec:>10.4f} "
              f"{tw_prec:>10.4f} {mfe_avg:>10.4f} {mae_avg:>10.4f} "
              f"{nothing_pct:>9.1f}% {decisive_pct:>9.1f}%")

    print("=" * 120)
    print(f"  [기준] SCORE_THRESHOLD={SCORE_THRESHOLD}, DULLING_RATIO={DULLING_RATIO}, LABEL_HORIZON={LABEL_HORIZON}")


def print_table3(results: dict[str, SingleTFResult]):
    """표3: Score 분포"""
    print()
    print("=" * 100)
    print("  표3. Score 분포 및 Score별 Precision")
    print("=" * 100)

    for name, r in results.items():
        if r.error:
            continue
        print(f"\n  [{name}] Total transitions={r.n_transitions}, Labeled={r.n_labeled}")
        print(f"  {'Score':>7} {'Count':>8} {'Precision':>12} {'Pct':>8}")
        print(f"  {'-'*40}")

        # Score <4 (filtered out, we can show count of score 3 etc.)
        all_scores = sorted(r.score_dist.keys())
        for s in all_scores:
            cnt = r.score_dist[s]
            prec = r.score_precision.get(s, 0.0)
            pct = cnt / r.n_transitions * 100 if r.n_transitions > 0 else 0
            print(f"  {s:>7} {cnt:>8} {prec:>12.4f} {pct:>7.1f}%")

        # Cumulative ≥ score
        print(f"  {'-'*40}")
        for threshold in [4, 5, 6]:
            cum_cnt = sum(v for k, v in r.score_dist.items() if k >= threshold)
            print(f"  {'≥'+str(threshold):>7} {cum_cnt:>8}")

    print("=" * 100)


def print_table4(results: dict[str, SingleTFResult]):
    """표4: 구조 체크"""
    print()
    print("=" * 100)
    print("  표4. 구조 체크 (Background / Zone / Transition Type)")
    print("=" * 100)

    for name, r in results.items():
        if r.error:
            continue
        print(f"\n  [{name}]")
        print(f"    Background candidates     : {r.n_bg_candidates}")
        print(f"    Background events          : {r.n_bg_events}")
        print(f"    bg_promoted (→ zone)        : {r.n_bg_promoted}")
        print(f"    Zone (from BG / from LH)   : {r.n_zone_from_bg} / {r.n_zone_from_lh}")
        print(f"    Zone events                : {r.n_zone_events}")
        print(f"    Zone age (recent/mid/old)   : {r.n_recent_zones} / {r.n_mid_zones} / {r.n_old_zones}")
        print(f"    Transition types:")
        print(f"      trend_reversal           : {r.type_reversal}")
        print(f"      single_bounce            : {r.type_bounce}")
        print(f"      continuation             : {r.type_continuation}")
        print(f"    Directional:")
        print(f"      bull→bear (상→하)         : {r.bull_to_bear_total} (confirmed: {r.bull_to_bear_confirmed})")
        print(f"      bear→bull (하→상)         : {r.bear_to_bull_total} (confirmed: {r.bear_to_bull_confirmed})")
        print(f"      neutral                  : {r.neutral_total}")
        print(f"    Trend weakening            : {r.trend_weakening_total} (confirmed: {r.trend_weakening_confirmed})")
        if r.expl_scores:
            print(f"    Explanation score range     : {min(r.expl_scores):.0f} ~ {max(r.expl_scores):.0f} (avg {np.mean(r.expl_scores):.1f})")
        if r.mfe_values:
            print(f"    MFE (max favorable)         : avg={np.mean(r.mfe_values):.4f}, med={np.median(r.mfe_values):.4f}, max={max(r.mfe_values):.4f}")
            print(f"    MAE (max adverse)           : avg={np.mean(r.mae_values):.4f}, med={np.median(r.mae_values):.4f}, min={min(r.mae_values):.4f}")

    print("=" * 100)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # Load real data
    parquet_path = "storage/bybit_btcusdt_15m.parquet"
    if not os.path.exists(parquet_path):
        print(f"ERROR: {parquet_path} not found")
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    # Validate columns
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()

    print("=" * 100)
    print("  Market Transition Engine - Real Data Validation")
    print("=" * 100)
    print(f"  Source      : {parquet_path}")
    print(f"  Rows        : {len(df):,}")
    print(f"  Period      : {df.index[0]} ~ {df.index[-1]}")
    print(f"  Days        : {(df.index[-1] - df.index[0]).days}")
    print(f"  Price       : ${df['low'].min():,.0f} ~ ${df['high'].max():,.0f}")
    print(f"  Volume avg  : {df['volume'].mean():.2f} BTC/candle")
    print("=" * 100)

    results: dict[str, SingleTFResult] = {}

    # ── Single TF runs ──────────────────────────────────
    for tf in [1, 16, 64, 228]:
        name = f"TF={tf}"
        print(f"\n▶ Running {name}...")
        r = run_single_tf(df, tf)
        results[name] = r
        if r.error:
            print(f"  ✗ ERROR: {r.error}")
        else:
            print(f"  ✓ pivots={r.n_pivots}, divs={r.n_divergences}, "
                  f"zones={r.n_zones}, trans={r.n_transitions}, "
                  f"prec={r.precision:.4f}, time={r.elapsed_sec:.1f}s")

    # ── Multi TF integrated (TF 1~10) ──────────────────
    print(f"\n▶ Running TF=1~10 integrated...")
    r_multi = run_multi_tf_integrated(df, list(range(1, 11)))
    results["TF1~10"] = r_multi
    if r_multi.error:
        print(f"  ✗ ERROR: {r_multi.error}")
    else:
        print(f"  ✓ pivots={r_multi.n_pivots}, divs={r_multi.n_divergences}, "
              f"zones={r_multi.n_zones}, trans={r_multi.n_transitions}, "
              f"prec={r_multi.precision:.4f}, time={r_multi.elapsed_sec:.1f}s")

    # ── Print all tables ────────────────────────────────
    print_table1(results)
    print_table2(results)
    print_table3(results)
    print_table4(results)

    # ── PASS / FAIL Judgment ────────────────────────────
    print()
    print("=" * 100)
    print("  최종 판단")
    print("=" * 100)

    errors = [name for name, r in results.items() if r.error]
    if errors:
        print(f"  ✗ FAIL: {len(errors)} TF(s) with errors: {errors}")
        for name in errors:
            print(f"    {name}: {results[name].error}")
    else:
        print("  ✓ 전체 TF 에러 없이 실행 완료")

    # Check transition counts
    for name, r in results.items():
        if r.error:
            continue
        if r.n_transitions == 0 and r.n_pivots > 10:
            print(f"  ⚠ {name}: transitions=0 but pivots={r.n_pivots} → 전이 필터가 너무 엄격할 수 있음")
        elif r.n_transitions > r.n_pivots * 0.8 and r.n_pivots > 10:
            print(f"  ⚠ {name}: transitions/pivots = {r.n_transitions}/{r.n_pivots} → 전이 필터가 너무 느슨할 수 있음")

    overall_pass = len(errors) == 0
    verdict = "PASS" if overall_pass else "FAIL"
    print(f"\n  ═══ 최종: {verdict} ═══")
    print("=" * 100)
