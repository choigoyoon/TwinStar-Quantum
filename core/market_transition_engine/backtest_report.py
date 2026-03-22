"""
Market Transition Engine - Backtest Report (Stage 4c)
======================================================
precision / recall / ablation 리포트를 출력한다.

[역할]
- TransitionCandidate + TransitionLabel 을 받아서 성적표를 만든다.
- Precision: confirmed / (confirmed + denied)
- 각 score 항목별 ablation (해당 항목 빼면 precision 이 얼마나 변하는지)
- score 분포 통계
- 방향별 분해: bull_to_bear / bear_to_bull / neutral precision
- decisive% / nothing% / MFE / MAE
- 전이 타입별 품질: trend_reversal / single_bounce / continuation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from core.market_transition_engine.types import (
    LabelVerdict,
    TransitionCandidate,
    TransitionLabel,
    TransitionType,
    TrendDirection,
)

logger = logging.getLogger(__name__)


@dataclass
class DirectionalMetrics:
    """방향별 메트릭"""
    n: int = 0
    confirmed: int = 0
    denied: int = 0
    ambiguous: int = 0
    precision: float = 0.0
    nothing_pct: float = 0.0


@dataclass
class TransitionTypeMetrics:
    """전이 타입별 메트릭 (trend_reversal / single_bounce / continuation)"""
    n: int = 0
    confirmed: int = 0
    denied: int = 0
    ambiguous: int = 0
    precision: float = 0.0
    decisive_pct: float = 0.0
    nothing_pct: float = 0.0
    mfe: float = 0.0
    mae: float = 0.0


@dataclass
class ReportMetrics:
    """리포트 메트릭"""
    total_candidates: int = 0
    labeled: int = 0
    confirmed: int = 0
    denied: int = 0
    ambiguous: int = 0
    precision: float = 0.0      # confirmed / (confirmed + denied)
    recall_proxy: float = 0.0   # 전이 후보 중 라벨된 비율
    decisive_pct: float = 0.0   # (confirmed + denied) / labeled
    nothing_pct: float = 0.0    # ambiguous / labeled
    mfe_mean: float = 0.0       # 평균 최대 유리 이동
    mae_mean: float = 0.0       # 평균 최대 불리 이동
    score_distribution: dict[int, int] = field(default_factory=dict)
    score_precision: dict[int, float] = field(default_factory=dict)
    ablation: dict[str, float] = field(default_factory=dict)
    # 방향별 분해
    bull_to_bear: DirectionalMetrics = field(default_factory=DirectionalMetrics)
    bear_to_bull: DirectionalMetrics = field(default_factory=DirectionalMetrics)
    neutral: DirectionalMetrics = field(default_factory=DirectionalMetrics)
    # 전이 타입별 품질
    type_reversal: TransitionTypeMetrics = field(default_factory=TransitionTypeMetrics)
    type_bounce: TransitionTypeMetrics = field(default_factory=TransitionTypeMetrics)
    type_continuation: TransitionTypeMetrics = field(default_factory=TransitionTypeMetrics)


class BacktestReport:
    """
    백테스트 리포트 생성기.
    """

    def generate(
        self,
        candidates: list[TransitionCandidate],
        labels: list[TransitionLabel],
        close: Optional[np.ndarray] = None,
        horizon: int = 16,
    ) -> ReportMetrics:
        """
        메트릭을 계산하고 ReportMetrics 를 반환한다.

        Args:
            candidates: 전이 후보 리스트
            labels: 라벨 리스트
            close: 종가 배열 (MFE/MAE 계산용, 없으면 생략)
            horizon: 라벨 horizon (MFE/MAE window)
        """
        metrics = ReportMetrics()
        metrics.total_candidates = len(candidates)

        if not labels:
            return metrics

        # label 을 t 기준으로 매핑
        label_map = {l.t: l for l in labels}

        metrics.labeled = len(labels)
        metrics.confirmed = sum(1 for l in labels if l.verdict == LabelVerdict.CONFIRMED)
        metrics.denied = sum(1 for l in labels if l.verdict == LabelVerdict.DENIED)
        metrics.ambiguous = sum(1 for l in labels if l.verdict == LabelVerdict.AMBIGUOUS)

        denom = metrics.confirmed + metrics.denied
        metrics.precision = metrics.confirmed / denom if denom > 0 else 0.0
        metrics.recall_proxy = (
            metrics.labeled / metrics.total_candidates
            if metrics.total_candidates > 0 else 0.0
        )
        metrics.decisive_pct = denom / metrics.labeled * 100 if metrics.labeled > 0 else 0.0
        metrics.nothing_pct = (
            metrics.ambiguous / metrics.labeled * 100
            if metrics.labeled > 0 else 0.0
        )

        # Score 분포 + score별 precision
        score_labels: dict[int, dict] = {}
        for cand in candidates:
            s = cand.score
            metrics.score_distribution[s] = metrics.score_distribution.get(s, 0) + 1
            if s not in score_labels:
                score_labels[s] = {"confirmed": 0, "denied": 0}

        for cand in candidates:
            lbl = label_map.get(cand.t)
            if lbl is None:
                continue
            s = cand.score
            if lbl.verdict == LabelVerdict.CONFIRMED:
                score_labels[s]["confirmed"] += 1
            elif lbl.verdict == LabelVerdict.DENIED:
                score_labels[s]["denied"] += 1

        for s, counts in score_labels.items():
            d = counts["confirmed"] + counts["denied"]
            metrics.score_precision[s] = counts["confirmed"] / d if d > 0 else 0.0

        # 방향별 분해
        metrics.bull_to_bear = self._directional_metrics(
            candidates, labels, TrendDirection.BULLISH
        )
        metrics.bear_to_bull = self._directional_metrics(
            candidates, labels, TrendDirection.BEARISH
        )
        metrics.neutral = self._directional_metrics(
            candidates, labels, TrendDirection.NEUTRAL
        )

        # MFE / MAE
        if close is not None and len(close) > 0:
            metrics.mfe_mean, metrics.mae_mean = self._compute_mfe_mae(
                close, candidates, horizon
            )

        # 전이 타입별 품질
        if close is not None and len(close) > 0:
            metrics.type_reversal = self._type_metrics(
                candidates, label_map, TransitionType.TREND_REVERSAL, close, horizon
            )
            metrics.type_bounce = self._type_metrics(
                candidates, label_map, TransitionType.SINGLE_BOUNCE, close, horizon
            )
            metrics.type_continuation = self._type_metrics(
                candidates, label_map, TransitionType.CONTINUATION, close, horizon
            )
        else:
            metrics.type_reversal = self._type_metrics(
                candidates, label_map, TransitionType.TREND_REVERSAL
            )
            metrics.type_bounce = self._type_metrics(
                candidates, label_map, TransitionType.SINGLE_BOUNCE
            )
            metrics.type_continuation = self._type_metrics(
                candidates, label_map, TransitionType.CONTINUATION
            )

        # Ablation: 각 score 항목을 빼봤을 때의 precision 변화
        metrics.ablation = self._run_ablation(candidates, label_map)

        return metrics

    def print_report(self, metrics: ReportMetrics) -> str:
        """
        사람이 읽을 수 있는 리포트 문자열을 반환한다.
        """
        lines = [
            "=" * 60,
            "  Market Transition Engine - Backtest Report",
            "=" * 60,
            f"  Total candidates : {metrics.total_candidates}",
            f"  Labeled          : {metrics.labeled}",
            f"  Confirmed        : {metrics.confirmed}",
            f"  Denied           : {metrics.denied}",
            f"  Ambiguous        : {metrics.ambiguous}",
            f"  Precision        : {metrics.precision:.4f}",
            f"  Decisive %       : {metrics.decisive_pct:.1f}%",
            f"  Nothing %        : {metrics.nothing_pct:.1f}%",
            f"  Recall proxy     : {metrics.recall_proxy:.4f}",
            f"  MFE (mean)       : {metrics.mfe_mean:.4f}",
            f"  MAE (mean)       : {metrics.mae_mean:.4f}",
            "",
            "  Directional Breakdown:",
            f"    bull→bear : n={metrics.bull_to_bear.n:4d}  "
            f"prec={metrics.bull_to_bear.precision:.4f}  "
            f"nothing={metrics.bull_to_bear.nothing_pct:.1f}%",
            f"    bear→bull : n={metrics.bear_to_bull.n:4d}  "
            f"prec={metrics.bear_to_bull.precision:.4f}  "
            f"nothing={metrics.bear_to_bull.nothing_pct:.1f}%",
            f"    neutral   : n={metrics.neutral.n:4d}  "
            f"prec={metrics.neutral.precision:.4f}  "
            f"nothing={metrics.neutral.nothing_pct:.1f}%",
            "",
            "  Score Distribution:",
        ]

        for score in sorted(metrics.score_distribution.keys()):
            count = metrics.score_distribution[score]
            sp = metrics.score_precision.get(score, 0.0)
            lines.append(f"    score={score}: {count:4d} candidates  precision={sp:.4f}")

        lines.append("")
        lines.append("  Transition Type Quality:")
        for ttype_name, ttype_m in [
            ("trend_reversal", metrics.type_reversal),
            ("single_bounce", metrics.type_bounce),
            ("continuation", metrics.type_continuation),
        ]:
            lines.append(
                f"    {ttype_name:18s}: n={ttype_m.n:4d}  "
                f"prec={ttype_m.precision:.4f}  "
                f"dec%={ttype_m.decisive_pct:.1f}  "
                f"MFE={ttype_m.mfe:.4f}  MAE={ttype_m.mae:.4f}"
            )

        lines.append("")
        lines.append("  Ablation Analysis (precision if item removed):")

        for item, prec in sorted(metrics.ablation.items()):
            delta = prec - metrics.precision
            direction = "+" if delta >= 0 else ""
            lines.append(f"    -{item}: precision={prec:.4f} ({direction}{delta:.4f})")

        lines.append("=" * 60)
        report = "\n".join(lines)

        logger.info("\n%s", report)
        return report

    # ── Internal ────────────────────────────────────────

    def _type_metrics(
        self,
        candidates: list[TransitionCandidate],
        label_map: dict[int, TransitionLabel],
        ttype: TransitionType,
        close: Optional[np.ndarray] = None,
        horizon: int = 16,
    ) -> TransitionTypeMetrics:
        """특정 전이 타입의 메트릭 계산"""
        tm = TransitionTypeMetrics()
        subset = [c for c in candidates if c.transition_type == ttype]
        tm.n = len(subset)
        if tm.n == 0:
            return tm

        for c in subset:
            lbl = label_map.get(c.t)
            if lbl is None:
                continue
            if lbl.verdict == LabelVerdict.CONFIRMED:
                tm.confirmed += 1
            elif lbl.verdict == LabelVerdict.DENIED:
                tm.denied += 1
            else:
                tm.ambiguous += 1

        labeled = tm.confirmed + tm.denied + tm.ambiguous
        denom = tm.confirmed + tm.denied
        tm.precision = tm.confirmed / denom if denom > 0 else 0.0
        tm.decisive_pct = denom / labeled * 100 if labeled > 0 else 0.0
        tm.nothing_pct = tm.ambiguous / labeled * 100 if labeled > 0 else 0.0

        if close is not None and len(close) > 0:
            tm.mfe, tm.mae = self._compute_mfe_mae(close, subset, horizon)

        return tm

    def _directional_metrics(
        self,
        candidates: list[TransitionCandidate],
        labels: list[TransitionLabel],
        direction: TrendDirection,
    ) -> DirectionalMetrics:
        """특정 추세 방향에 속하는 전이의 메트릭 계산"""
        dm = DirectionalMetrics()
        paired = list(zip(candidates, labels))
        subset = [(c, l) for c, l in paired if c.trend_before.direction == direction]
        dm.n = len(subset)
        if dm.n == 0:
            return dm
        dm.confirmed = sum(1 for _, l in subset if l.verdict == LabelVerdict.CONFIRMED)
        dm.denied = sum(1 for _, l in subset if l.verdict == LabelVerdict.DENIED)
        dm.ambiguous = sum(1 for _, l in subset if l.verdict == LabelVerdict.AMBIGUOUS)
        denom = dm.confirmed + dm.denied
        dm.precision = dm.confirmed / denom if denom > 0 else 0.0
        dm.nothing_pct = dm.ambiguous / dm.n * 100 if dm.n > 0 else 0.0
        return dm

    def _compute_mfe_mae(
        self,
        close: np.ndarray,
        candidates: list[TransitionCandidate],
        horizon: int,
    ) -> tuple[float, float]:
        """MFE / MAE 계산 (예측 방향 기준)"""
        n = len(close)
        mfe_vals: list[float] = []
        mae_vals: list[float] = []

        for cand in candidates:
            t = cand.t
            t_h = min(t + horizon, n - 1)
            if t >= n or t + 1 >= n:
                continue
            window = close[t:t_h + 1]
            p_t = close[t]
            if p_t == 0:
                continue

            pcts = (window - p_t) / p_t

            if cand.trend_before.direction == TrendDirection.BEARISH:
                # expect up
                mfe_vals.append(float(np.max(pcts)))
                mae_vals.append(float(np.min(pcts)))
            elif cand.trend_before.direction == TrendDirection.BULLISH:
                # expect down
                mfe_vals.append(float(-np.min(pcts)))
                mae_vals.append(float(-np.max(pcts)))
            else:
                mfe_vals.append(float(np.max(np.abs(pcts))))
                mae_vals.append(float(-np.max(np.abs(pcts))))

        mfe = float(np.mean(mfe_vals)) if mfe_vals else 0.0
        mae = float(np.mean(mae_vals)) if mae_vals else 0.0
        return mfe, mae

    def _run_ablation(
        self,
        candidates: list[TransitionCandidate],
        label_map: dict[int, TransitionLabel],
    ) -> dict[str, float]:
        """
        각 score 항목을 제거했을 때의 precision 을 계산한다.

        score 항목:
        1. trend_weakening (dulling >= 0.5)
        2. zone_reaction (proximity < threshold)
        3. zone_strong (strength >= min)
        4. div_present (chain >= 1)
        5. new_zone
        6. rhythm_break (암묵적)
        """
        from core.market_transition_engine.config import (
            DULLING_RATIO,
            ZONE_MIN_STRENGTH,
        )
        from core.market_transition_engine.transition_builder import (
            ZONE_PROXIMITY_THRESHOLD,
        )

        ablation_items = {
            "trend_weakening": lambda c: 1 if c.dulling_intensity >= DULLING_RATIO else 0,
            "zone_reaction": lambda c: 1 if c.zone_proximity < ZONE_PROXIMITY_THRESHOLD else 0,
            "zone_strong": lambda c: 1 if c.zone_strength >= ZONE_MIN_STRENGTH else 0,
            "div_present": lambda c: 1 if c.div_chain_length >= 1 else 0,
            "new_zone": lambda c: 1 if c.new_zone_appeared else 0,
        }

        result: dict[str, float] = {}

        for item_name, item_fn in ablation_items.items():
            confirmed = 0
            denied = 0

            for cand in candidates:
                label = label_map.get(cand.t)
                if label is None:
                    continue

                # 이 항목의 기여도를 빼서 score 재계산
                item_contrib = item_fn(cand)
                adjusted_score = cand.score - item_contrib

                # 조정된 score 가 여전히 threshold 이상인 경우만 카운트
                if adjusted_score >= 4:  # SCORE_THRESHOLD
                    if label.verdict == LabelVerdict.CONFIRMED:
                        confirmed += 1
                    elif label.verdict == LabelVerdict.DENIED:
                        denied += 1

            denom = confirmed + denied
            result[item_name] = confirmed / denom if denom > 0 else 0.0

        return result
