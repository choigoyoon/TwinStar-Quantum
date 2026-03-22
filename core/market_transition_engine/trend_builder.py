"""
Market Transition Engine - Trend Builder (Stage 3b)
====================================================
L/H 간 리듬(간격, 방향, 크기)으로 추세 상태를 판단한다.

[핵심 철학]
- 추세는 선이 아니라, 다음 반응의 리듬이다.
- Higher-High + Higher-Low = 상승 추세
- Lower-High + Lower-Low = 하락 추세
- 리듬이 깨지면(둔화) 전이 가능성이 올라간다.

[둔화(Dulling) 측정]
- 최근 스윙 크기가 이전보다 작아지면 둔화.
- dulling = (이전 스윙 크기 - 현재 스윙 크기) / 이전 스윙 크기
- DULLING_RATIO(0.5) 이상이면 "유의미한 둔화"

[미래참조 방지]
- confirmed_at <= t 인 피벗만 사용
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from core.market_transition_engine.config import (
    DULLING_RATIO,
    TREND_MIN_PIVOTS,
)
from core.market_transition_engine.types import (
    Pivot,
    PivotType,
    TrendDirection,
    TrendState,
)
from core.market_transition_engine.lh_builder import get_pivots_known_at

logger = logging.getLogger(__name__)


class TrendBuilder:
    """
    L/H 리듬 기반 추세 상태 빌더.

    사용법:
        builder = TrendBuilder()
        state = builder.get_trend_at(pivots, t=1000)
    """

    def get_trend_at(
        self, pivots: list[Pivot], t: int
    ) -> TrendState:
        """
        시점 t 에서의 추세 상태를 반환한다.

        Args:
            pivots: 전체 피벗 리스트
            t: 시점 (15분봉 인덱스)

        Returns:
            TrendState
        """
        known = get_pivots_known_at(pivots, t)

        if len(known) < TREND_MIN_PIVOTS:
            return TrendState(
                direction=TrendDirection.NEUTRAL,
                pivot_count=len(known),
            )

        # 최근 피벗들로 추세 판단
        recent = known[-min(len(known), 10):]  # 최근 10개 피벗

        highs = [p for p in recent if p.pivot_type == PivotType.HIGH]
        lows = [p for p in recent if p.pivot_type == PivotType.LOW]

        direction = self._determine_direction(highs, lows)
        magnitude = self._compute_magnitude(recent)
        rhythm = self._compute_rhythm(recent)
        dulling = self._compute_dulling(recent)

        return TrendState(
            direction=direction,
            magnitude=magnitude,
            rhythm_interval=rhythm,
            dulling=dulling,
            pivot_count=len(known),
            last_pivot_idx=recent[-1].idx if recent else 0,
        )

    def _determine_direction(
        self,
        highs: list[Pivot],
        lows: list[Pivot],
    ) -> TrendDirection:
        """
        H 와 L 의 시퀀스로 추세 방향을 결정한다.

        HH + HL = bullish
        LH + LL = bearish
        그 외 = neutral
        """
        if len(highs) < 2 or len(lows) < 2:
            return TrendDirection.NEUTRAL

        # 최근 2개씩 비교
        hh = highs[-1].price > highs[-2].price  # Higher High
        hl = lows[-1].price > lows[-2].price     # Higher Low
        lh = highs[-1].price < highs[-2].price   # Lower High
        ll = lows[-1].price < lows[-2].price     # Lower Low

        if hh and hl:
            return TrendDirection.BULLISH
        elif lh and ll:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL

    def _compute_magnitude(self, pivots: list[Pivot]) -> float:
        """
        최근 스윙 크기의 가중 평균으로 추세 강도를 계산한다.
        최근 것일수록 가중치가 높다.
        """
        if len(pivots) < 2:
            return 0.0

        swings: list[float] = []
        for i in range(1, len(pivots)):
            swing = abs(pivots[i].price - pivots[i - 1].price)
            swings.append(swing)

        if not swings:
            return 0.0

        # 최근 것에 더 높은 가중치 (선형 가중)
        weights = np.arange(1, len(swings) + 1, dtype=float)
        return float(np.average(swings, weights=weights))

    def _compute_rhythm(self, pivots: list[Pivot]) -> float:
        """
        L→H 또는 H→L 간 평균 간격 (15분봉 수).
        리듬의 규칙성을 나타낸다.
        """
        if len(pivots) < 2:
            return 0.0

        intervals: list[int] = []
        for i in range(1, len(pivots)):
            interval = pivots[i].idx - pivots[i - 1].idx
            if interval > 0:
                intervals.append(interval)

        if not intervals:
            return 0.0

        return float(np.mean(intervals))

    def _compute_dulling(self, pivots: list[Pivot]) -> float:
        """
        둔화도를 계산한다.

        최근 스윙 크기가 이전보다 작아진 비율.
        dulling = (prev_swing - curr_swing) / prev_swing
        양수이면 둔화 (스윙이 줄어들고 있음).

        DULLING_RATIO(0.5) 이상이면 유의미한 둔화.
        """
        if len(pivots) < 4:
            return 0.0

        # 최근 2개 스윙과 그 이전 2개 스윙 비교
        swings: list[float] = []
        for i in range(1, len(pivots)):
            swings.append(abs(pivots[i].price - pivots[i - 1].price))

        if len(swings) < 2:
            return 0.0

        # 후반부 vs 전반부
        mid = len(swings) // 2
        early_avg = float(np.mean(swings[:mid])) if mid > 0 else 0.0
        late_avg = float(np.mean(swings[mid:])) if mid < len(swings) else 0.0

        if early_avg <= 0:
            return 0.0

        dulling = (early_avg - late_avg) / early_avg
        return max(0.0, dulling)  # 음수는 0 (가속 = 둔화 아님)
