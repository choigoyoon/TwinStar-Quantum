"""
Market Transition Engine
=========================
"왜 L/H가 여기서 생겼는지"를 과거 구조물과 힘의 변화로 설명하는 엔진.

매수/매도 신호기가 아니다.
구조를 읽고 설명하는 것이 핵심이다.

[4단계 순차 파이프라인]
  Stage 1: OHLCV-only 배경      → background_builder
  Stage 2: L/H + 다이버전스      → lh_builder + divergence_builder
  Stage 3: 배경 재점수화          → zone_builder + trend_builder
  Stage 4: 최종 판단             → transition_builder + labeler + score_engine + backtest_report

[사용법]
    from core.market_transition_engine import run_pipeline

    result = run_pipeline(df_15m, tf=228)
    print(result.report)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from core.market_transition_engine.config import (
    SCORE_THRESHOLD,
    DULLING_RATIO,
    LABEL_HORIZON,
    MAX_TF,
)
from core.market_transition_engine.types import (
    TransitionCandidate,
    TransitionLabel,
)
from core.market_transition_engine.data_loader import DataLoader, aggregate_tf
from core.market_transition_engine.background_builder import BackgroundBuilder
from core.market_transition_engine.lh_builder import LHBuilder
from core.market_transition_engine.divergence_builder import DivergenceBuilder
from core.market_transition_engine.zone_builder import ZoneBuilder
from core.market_transition_engine.trend_builder import TrendBuilder
from core.market_transition_engine.transition_builder import TransitionBuilder
from core.market_transition_engine.labeler import Labeler
from core.market_transition_engine.score_engine import ScoreEngine
from core.market_transition_engine.backtest_report import BacktestReport, ReportMetrics

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """파이프라인 전체 실행 결과"""
    candidates: list[TransitionCandidate] = field(default_factory=list)
    labels: list[TransitionLabel] = field(default_factory=list)
    metrics: Optional[ReportMetrics] = None
    report: str = ""


def run_pipeline(
    df_15m: pd.DataFrame,
    tf: int = MAX_TF,
    with_labels: bool = True,
) -> PipelineResult:
    """
    4단계 순차 파이프라인을 실행한다.

    Args:
        df_15m: 15분봉 DataFrame (clean, OHLCV)
        tf: L/H 탐색 TF 배수 (default: 228)
        with_labels: 사후 검증 라벨을 생성할지 (True = 백테스트 모드)

    Returns:
        PipelineResult
    """
    result = PipelineResult()

    logger.info("=" * 50)
    logger.info("Market Transition Engine - Pipeline Start")
    logger.info("  Data: %d rows, TF=%d", len(df_15m), tf)
    logger.info("=" * 50)

    # ── Stage 1: OHLCV-only 배경 ──────────────────────────
    logger.info("[Stage 1] Building background...")
    bg_builder = BackgroundBuilder()
    bg_builder.build(df_15m)
    logger.info("  Background candidates: %d", len(bg_builder.candidates))

    # ── Stage 2: L/H + 다이버전스 ─────────────────────────
    logger.info("[Stage 2] Building L/H pivots (TF=%d)...", tf)
    lh_builder = LHBuilder()
    pivots = lh_builder.build(df_15m, tf=tf)
    logger.info("  Pivots: %d", len(pivots))

    logger.info("[Stage 2] Building divergences...")
    div_builder = DivergenceBuilder()
    divergences = div_builder.build(df_15m, pivots, tf=tf)
    logger.info("  Divergences: %d", len(divergences))

    # ── Stage 3: 배경 재점수화 ────────────────────────────
    logger.info("[Stage 3] Building zones (background + L/H)...")
    zone_builder = ZoneBuilder()
    zone_builder.build(df_15m, bg_builder, pivots)
    logger.info("  Zones: %d", len(zone_builder.zones))

    trend_builder = TrendBuilder()

    # ── Stage 4: 최종 판단 ────────────────────────────────
    logger.info("[Stage 4] Evaluating transitions...")
    trans_builder = TransitionBuilder()
    candidates = trans_builder.build(
        df_15m, pivots, zone_builder, trend_builder, divergences
    )
    logger.info("  Transition candidates (score>=%d): %d", SCORE_THRESHOLD, len(candidates))

    # 설명 점수 부여
    score_engine = ScoreEngine()
    candidates = score_engine.score_all(candidates)
    result.candidates = candidates

    # 라벨링 (백테스트 모드)
    if with_labels:
        logger.info("[Stage 4] Labeling (t+%d)...", LABEL_HORIZON)
        labeler = Labeler()
        labels = labeler.label(df_15m, candidates)
        result.labels = labels

        # 리포트 (close 배열 전달하여 MFE/MAE 계산)
        report_gen = BacktestReport()
        close_arr = df_15m["close"].values
        metrics = report_gen.generate(
            candidates, labels, close=close_arr, horizon=LABEL_HORIZON,
        )
        result.metrics = metrics
        result.report = report_gen.print_report(metrics)

    logger.info("Pipeline complete.")
    return result
