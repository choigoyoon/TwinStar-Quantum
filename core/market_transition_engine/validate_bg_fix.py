#!/usr/bin/env python3
"""
Background Builder v2 검증 스크립트
====================================
실 BTC-USDT 15분봉 데이터에서 background_builder.py 수정 전/후를 비교한다.

보고 항목:
1. bg_candidate 수
2. zone 수
3. zone-width 분포 (min, mean, median, max, >5% 비율)
4. zone_proximity 분포
5. transition 수
6. precision 변화
7. giant zone 해소 여부
"""

import sys
import os
import time
import logging
import tracemalloc

import numpy as np
import pandas as pd

# 프로젝트 루트 설정
_this_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
_project_root = os.path.abspath(os.path.join(_this_dir, '..', '..'))
if os.path.exists(os.path.join(_project_root, 'core')):
    sys.path.insert(0, _project_root)
else:
    # fallback: 현재 디렉토리가 프로젝트 루트
    sys.path.insert(0, os.getcwd())

from core.market_transition_engine.config import (
    SCORE_THRESHOLD, DULLING_RATIO, LABEL_HORIZON, BG_ZONE_MERGE_PCT,
)
from core.market_transition_engine.background_builder import (
    BackgroundBuilder, MAX_ZONE_WIDTH_PCT, REACTION_CLUSTER_GAP_PCT,
)
from core.market_transition_engine.lh_builder import LHBuilder
from core.market_transition_engine.divergence_builder import DivergenceBuilder
from core.market_transition_engine.zone_builder import ZoneBuilder
from core.market_transition_engine.trend_builder import TrendBuilder
from core.market_transition_engine.transition_builder import TransitionBuilder
from core.market_transition_engine.labeler import Labeler

logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")
logger = logging.getLogger("validate_bg_fix")


def load_data() -> pd.DataFrame:
    """실 BTC 데이터 로드"""
    path = "storage/bybit_btcusdt_15m.parquet"
    if not os.path.exists(path):
        raise FileNotFoundError(f"데이터 파일 없음: {path}")
    df = pd.read_parquet(path)
    logger.info(f"데이터 로드: {len(df)} rows, {df['close'].min():.0f}-{df['close'].max():.0f}")
    return df


def run_pipeline(df: pd.DataFrame, tf: int = 1):
    """파이프라인 실행 (TF=1 기본)"""
    tracemalloc.start()
    t0 = time.time()

    # Stage 1: Background
    bg = BackgroundBuilder()
    bg.build(df)

    # Stage 2: L/H + Divergence
    lh = LHBuilder()
    pivots = lh.build(df, tf=tf)
    div_builder = DivergenceBuilder()
    divs = div_builder.build(df, pivots)

    # Stage 3: Zone + Trend
    zone_builder = ZoneBuilder()
    zone_builder.build(df, bg, pivots)
    trend_builder = TrendBuilder()

    # Stage 4: Transition
    trans_builder = TransitionBuilder()
    candidates = trans_builder.build(df, pivots, zone_builder, trend_builder, divs)

    # Label
    labeler = Labeler()
    labels = labeler.label(df, candidates)

    elapsed = time.time() - t0
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "bg": bg,
        "pivots": pivots,
        "divs": divs,
        "zone_builder": zone_builder,
        "candidates": candidates,
        "labels": labels,
        "elapsed": elapsed,
        "peak_mem_mb": peak_mem / 1024 / 1024,
    }


def analyze_bg_candidates(bg: BackgroundBuilder) -> dict:
    """bg_candidate 분석"""
    cands = bg.candidates
    n = len(cands)
    if n == 0:
        return {"count": 0, "widths_pct": [], "giant_zone": False}

    widths = []
    giant = False
    for c in cands:
        mid = (c.price_low + c.price_high) / 2.0
        w = (c.price_high - c.price_low) / mid if mid > 0 else 0
        widths.append(w)
        if w > 0.5:  # >50% width = giant
            giant = True

    return {
        "count": n,
        "widths_pct": [w * 100 for w in widths],
        "giant_zone": giant,
        "min_width": min(widths) * 100,
        "max_width": max(widths) * 100,
        "mean_width": np.mean(widths) * 100,
        "median_width": np.median(widths) * 100,
        "over_5pct_count": sum(1 for w in widths if w > 0.05),
    }


def analyze_zone_proximity(result: dict, df: pd.DataFrame) -> dict:
    """zone_proximity 분포 분석"""
    candidates = result["candidates"]
    if not candidates:
        return {"count": 0}

    prox_values = [c.zone_proximity for c in candidates]
    zero_count = sum(1 for p in prox_values if p == 0.0)

    return {
        "count": len(prox_values),
        "zero_pct": zero_count / len(prox_values) * 100,
        "min": min(prox_values),
        "max": max(prox_values),
        "mean": np.mean(prox_values),
        "median": np.median(prox_values),
        "p25": np.percentile(prox_values, 25),
        "p75": np.percentile(prox_values, 75),
    }


def analyze_precision(result: dict) -> dict:
    """precision 분석"""
    candidates = result["candidates"]
    labels = result["labels"]

    if not labels:
        return {"total": 0, "precision": 0.0}

    confirmed = sum(1 for l in labels if l.verdict.value == "confirmed")
    denied = sum(1 for l in labels if l.verdict.value == "denied")
    ambiguous = sum(1 for l in labels if l.verdict.value == "ambiguous")
    total = len(labels)

    # non-ambiguous precision
    non_amb = confirmed + denied
    precision = confirmed / non_amb if non_amb > 0 else 0.0

    # MFE / MAE
    mfe_values = []
    mae_values = []
    for l in labels:
        pct = l.pct_change
        if l.direction_matched:
            mfe_values.append(abs(pct))
        else:
            mae_values.append(abs(pct))

    # score 분포
    score_dist = {}
    for c in candidates:
        s = c.score
        if s not in score_dist:
            score_dist[s] = {"count": 0, "confirmed": 0, "denied": 0, "ambiguous": 0}
        score_dist[s]["count"] += 1

    for l, c in zip(labels, candidates):
        s = c.score
        v = l.verdict.value
        if v in score_dist[s]:
            score_dist[s][v] += 1

    score_precision = {}
    for s, d in score_dist.items():
        non_amb_s = d["confirmed"] + d["denied"]
        score_precision[s] = d["confirmed"] / non_amb_s if non_amb_s > 0 else 0.0

    # transition type 분포
    type_dist = {}
    for c in candidates:
        tt = c.transition_type.value
        if tt not in type_dist:
            type_dist[tt] = 0
        type_dist[tt] += 1

    # nothing % (ambiguous / total)
    nothing_pct = ambiguous / total * 100 if total > 0 else 0

    # decisive % (confirmed + denied) / total
    decisive_pct = non_amb / total * 100 if total > 0 else 0

    return {
        "total_candidates": len(candidates),
        "total_labels": total,
        "confirmed": confirmed,
        "denied": denied,
        "ambiguous": ambiguous,
        "precision": precision,
        "nothing_pct": nothing_pct,
        "decisive_pct": decisive_pct,
        "mfe_mean": np.mean(mfe_values) if mfe_values else 0,
        "mae_mean": np.mean(mae_values) if mae_values else 0,
        "score_dist": score_dist,
        "score_precision": score_precision,
        "type_dist": type_dist,
    }


def print_report(df: pd.DataFrame, result: dict):
    """검증 보고서 출력"""
    bg_info = analyze_bg_candidates(result["bg"])
    prox_info = analyze_zone_proximity(result, df)
    prec_info = analyze_precision(result)

    sep = "=" * 70
    print(f"\n{sep}")
    print("  Background Builder v2 검증 보고서")
    print(f"{sep}")
    print(f"  데이터: {len(df)} rows, ${df['close'].min():.0f}-${df['close'].max():.0f}")
    print(f"  실행시간: {result['elapsed']:.1f}s, 메모리: {result['peak_mem_mb']:.1f}MB")
    print(f"  설정: BG_ZONE_MERGE_PCT={BG_ZONE_MERGE_PCT}, MAX_ZONE_WIDTH_PCT={MAX_ZONE_WIDTH_PCT}")
    print(f"         REACTION_CLUSTER_GAP_PCT={REACTION_CLUSTER_GAP_PCT}")
    print(f"{sep}")

    # ── Table 1: bg_candidate 정보 ──
    print("\n[Table 1] bg_candidate 정보")
    print("-" * 50)
    print(f"  bg_candidate 수: {bg_info['count']}")
    print(f"  giant zone (>50% width): {'YES ⚠️' if bg_info['giant_zone'] else 'NO ✅'}")
    if bg_info['count'] > 0:
        print(f"  너비 분포 (mid 대비 %):")
        print(f"    min: {bg_info['min_width']:.2f}%")
        print(f"    mean: {bg_info['mean_width']:.2f}%")
        print(f"    median: {bg_info['median_width']:.2f}%")
        print(f"    max: {bg_info['max_width']:.2f}%")
        print(f"    >5% 초과: {bg_info['over_5pct_count']}개")
        print(f"  개별 zone 목록:")
        for c in result["bg"].candidates:
            mid = (c.price_low + c.price_high) / 2.0
            w = (c.price_high - c.price_low) / mid * 100 if mid > 0 else 0
            print(f"    zone {c.zone_id}: ${c.price_low:.0f}-${c.price_high:.0f} "
                  f"(width {w:.2f}%, first_seen={c.first_seen}, "
                  f"touches={c.touch_count}, vol_wt={c.volume_weight:.1f})")

    # ── Table 2: zone 정보 ──
    zb = result["zone_builder"]
    print(f"\n[Table 2] Zone 정보")
    print("-" * 50)
    print(f"  total zones: {len(zb.zones)}")
    from_bg = sum(1 for z in zb.zones if z.from_background)
    from_lh = len(zb.zones) - from_bg
    print(f"    from_background: {from_bg}")
    print(f"    from_LH: {from_lh}")
    for z in zb.zones[:20]:  # 최대 20개
        mid = (z.price_low + z.price_high) / 2.0
        w = (z.price_high - z.price_low) / mid * 100 if mid > 0 else 0
        print(f"    zone {z.zone_id}: ${z.price_low:.0f}-${z.price_high:.0f} "
              f"(width {w:.2f}%, bg={z.from_background}, born={z.born_at})")

    # ── Table 3: zone_proximity 분포 ──
    print(f"\n[Table 3] zone_proximity 분포")
    print("-" * 50)
    if prox_info["count"] > 0:
        print(f"  transition 수: {prox_info['count']}")
        print(f"  proximity == 0 (inside zone): {prox_info['zero_pct']:.1f}%")
        print(f"  min: {prox_info['min']:.4f}")
        print(f"  p25: {prox_info['p25']:.4f}")
        print(f"  median: {prox_info['median']:.4f}")
        print(f"  mean: {prox_info['mean']:.4f}")
        print(f"  p75: {prox_info['p75']:.4f}")
        print(f"  max: {prox_info['max']:.4f}")
    else:
        print("  transition 없음")

    # ── Table 4: precision 분석 ──
    print(f"\n[Table 4] Precision 분석")
    print("-" * 50)
    print(f"  총 candidates: {prec_info['total_candidates']}")
    print(f"  총 labels: {prec_info['total_labels']}")
    print(f"  confirmed: {prec_info['confirmed']}")
    print(f"  denied: {prec_info['denied']}")
    print(f"  ambiguous: {prec_info['ambiguous']}")
    print(f"  precision (non-amb): {prec_info['precision']:.4f}")
    print(f"  nothing %: {prec_info['nothing_pct']:.1f}%")
    print(f"  decisive %: {prec_info['decisive_pct']:.1f}%")
    print(f"  MFE mean: {prec_info['mfe_mean']:.4f}")
    print(f"  MAE mean: {prec_info['mae_mean']:.4f}")

    # Score 분포
    print(f"\n  Score 분포:")
    for s in sorted(prec_info["score_dist"].keys()):
        d = prec_info["score_dist"][s]
        p = prec_info["score_precision"][s]
        print(f"    score={s}: {d['count']} candidates "
              f"(C={d['confirmed']}, D={d['denied']}, A={d['ambiguous']}) "
              f"precision={p:.4f}")

    # Type 분포
    print(f"\n  Transition type 분포:")
    for tt, cnt in sorted(prec_info["type_dist"].items()):
        print(f"    {tt}: {cnt}")

    # ── 판정 ──
    print(f"\n{'=' * 70}")
    print("  최종 판정")
    print(f"{'=' * 70}")

    issues = []
    if bg_info["giant_zone"]:
        issues.append("giant zone 여전히 존재")
    if bg_info["count"] < 2:
        issues.append(f"bg_candidate 수 부족 ({bg_info['count']})")
    if prox_info.get("zero_pct", 0) > 95:
        issues.append(f"zone_proximity=0 비율 과다 ({prox_info.get('zero_pct', 0):.0f}%)")

    if not issues:
        print("  ✅ PASS - giant zone 해소, 다중 zone 생성 확인")
    else:
        print("  ❌ FAIL -", ", ".join(issues))

    # 이전 결과와 비교
    print(f"\n  [이전 vs 현재 비교]")
    print(f"  항목            이전(v1)        현재(v2)")
    print(f"  bg_candidates   1               {bg_info['count']}")
    print(f"  giant zone      YES             {'YES' if bg_info['giant_zone'] else 'NO'}")
    print(f"  transitions     492             {prec_info['total_candidates']}")
    print(f"  precision       0.3370          {prec_info['precision']:.4f}")
    print(f"  nothing %       ~63%            {prec_info['nothing_pct']:.1f}%")


if __name__ == "__main__":
    df = load_data()
    result = run_pipeline(df, tf=1)
    print_report(df, result)
