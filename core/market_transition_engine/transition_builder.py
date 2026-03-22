"""
Market Transition Engine - Transition Builder (Stage 4a)
=========================================================
전이 후보를 생성하고, 약한 전이를 제거한다.

[핵심 철학]
전이 = "기존 추세 약화 + 과누적 + 새 지지/저항 출현"
이 세 가지가 동시에 만족해야 전이 후보가 된다.

[운영 규칙 - 변경 금지]
- transition_score >= SCORE_THRESHOLD(4) 이면 통과
- 새 조건 추가 금지
- 핵심은 "조건 추가"가 아니라 "약한 전이 제거와 설명력 확보"

[score 계산]
점수 항목 (각각 0 또는 1):
1. trend_weakening : 기존 추세의 둔화가 있는가 (dulling >= DULLING_RATIO)
2. zone_reaction   : 유의미한 zone 근처에 있는가 (proximity < threshold)
3. zone_strong     : 해당 zone 의 강도가 충분한가
4. div_present     : 다이버전스 체인이 존재하는가
5. new_zone        : 최근 새 zone 이 출현했는가
6. rhythm_break    : 리듬 간격이 깨졌는가

score = sum of binary items (0~6)
>= 4 이면 통과.

[분류 조건 - Variant B 채택]
A/B/C 실험 결과 (BTC 30k 15min, TF=1):
  A) trend_weakening AND div>=2 AND new_zone → 3 reversals (new_zone 병목)
  B) trend_weakening AND (div>=2 OR new_zone) → 242 reversals ← 채택
  C) strong dulling AND (div>=2 OR new_zone) → 18 reversals (precision 0.1111)

Variant B가 기존 신호를 더 정확히 분류함:
- 전체 신호 수 불변 (494), precision 불변 (0.3047)
- reversal precision 0.3008, MFE 0.0060
- bull→bear 0.5373, bear→bull 0.4949 (방향 균형 유지)

[검증 결론 반영]
- transition_builder가 전체 병목이다
- provisional zone은 사실상 0이었다 → 만들지 않는다
- bg_bonus / rhythm_bonus는 precision 기준 영향이 거의 없었다 → 보너스 없음
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import (
    DULLING_RATIO,
    SCORE_THRESHOLD,
    ZONE_MIN_STRENGTH,
)
from core.market_transition_engine.types import (
    Pivot,
    PivotType,
    TransitionCandidate,
    TransitionType,
    TrendDirection,
    TrendState,
)
from core.market_transition_engine.lh_builder import get_pivots_known_at
from core.market_transition_engine.zone_builder import ZoneBuilder
from core.market_transition_engine.trend_builder import TrendBuilder
from core.market_transition_engine.divergence_builder import (
    DivergenceRecord,
    get_max_chain_at,
)

logger = logging.getLogger(__name__)

# zone proximity threshold (가격 대비 2% 이내면 "가까움")
ZONE_PROXIMITY_THRESHOLD: float = 0.02
# 새 zone 판단: 최근 N봉 이내에 생긴 zone
NEW_ZONE_RECENCY: int = 50
# 리듬 깨짐 판단: 현재 간격이 평균의 N배 이상
RHYTHM_BREAK_FACTOR: float = 2.0


class TransitionBuilder:
    """
    Stage 4a: 전이 후보 생성기.
    각 피벗 확정 시점에서 전이 여부를 평가한다.
    """

    def build(
        self,
        df_15m: pd.DataFrame,
        pivots: list[Pivot],
        zone_builder: ZoneBuilder,
        trend_builder: TrendBuilder,
        divergences: list[DivergenceRecord],
    ) -> list[TransitionCandidate]:
        """
        전체 피벗에 대해 전이 후보를 평가한다.
        score >= SCORE_THRESHOLD 인 것만 반환.

        Args:
            df_15m: 15분봉 DataFrame
            pivots: 전체 피벗 리스트
            zone_builder: 빌드 완료된 ZoneBuilder
            trend_builder: TrendBuilder 인스턴스
            divergences: 다이버전스 기록

        Returns:
            list[TransitionCandidate], score >= 4 인 것만
        """
        close = df_15m["close"].values
        candidates: list[TransitionCandidate] = []

        # 확정된 피벗 순서대로 평가
        sorted_pivots = sorted(pivots, key=lambda p: p.confirmed_at)

        for pivot in sorted_pivots:
            t = pivot.confirmed_at
            if t >= len(close):
                continue

            price = close[t]

            # ① 추세 상태
            trend = trend_builder.get_trend_at(pivots, t)

            # ② zone 근접도
            nearest = zone_builder.get_nearest_zone_at(t, price)
            zone_proximity = 1.0  # 기본: 멀다
            zone_strength = 0.0
            new_zone_appeared = False

            if nearest is not None:
                zone, zone_state, prox = nearest
                zone_proximity = prox
                zone_strength = zone_state.strength

                # 새 zone 판단
                if zone.born_at >= t - NEW_ZONE_RECENCY:
                    new_zone_appeared = True

            # ③ 다이버전스 체인
            div_chain = get_max_chain_at(divergences, t)

            # ④ 리듬 깨짐 판단
            rhythm_broken = self._check_rhythm_break(pivots, t, trend)

            # ── Score 계산 (각 항목 0 또는 1) ──
            score = 0

            # 1. 추세 둔화
            trend_weakening = trend.dulling >= DULLING_RATIO
            if trend_weakening:
                score += 1

            # 2. zone 근접
            zone_near = zone_proximity < ZONE_PROXIMITY_THRESHOLD
            if zone_near:
                score += 1

            # 3. zone 강도
            zone_strong = zone_strength >= ZONE_MIN_STRENGTH
            if zone_strong:
                score += 1

            # 4. 다이버전스 존재
            div_present = div_chain >= 1
            if div_present:
                score += 1

            # 5. 새 zone 출현
            if new_zone_appeared:
                score += 1

            # 6. 리듬 깨짐
            if rhythm_broken:
                score += 1

            # score < SCORE_THRESHOLD 이면 약한 전이 → 제거
            if score < SCORE_THRESHOLD:
                continue

            # 전이 타입 분류
            transition_type = self._classify_transition(
                trend, trend_weakening, div_chain, new_zone_appeared
            )

            candidates.append(TransitionCandidate(
                t=t,
                transition_type=transition_type,
                score=score,
                trend_before=trend,
                dulling_intensity=trend.dulling,
                zone_proximity=zone_proximity,
                zone_strength=zone_strength,
                div_chain_length=div_chain,
                new_zone_appeared=new_zone_appeared,
            ))

        logger.info(
            "Transitions: %d candidates (score >= %d), %d total pivots evaluated",
            len(candidates), SCORE_THRESHOLD, len(sorted_pivots),
        )

        return candidates

    def _check_rhythm_break(
        self,
        pivots: list[Pivot],
        t: int,
        trend: TrendState,
    ) -> bool:
        """
        현재 피벗 간격이 평균 리듬의 RHYTHM_BREAK_FACTOR 배 이상이면
        리듬이 깨진 것으로 판단.
        """
        if trend.rhythm_interval <= 0:
            return False

        known = get_pivots_known_at(pivots, t)
        if len(known) < 2:
            return False

        last_two = known[-2:]
        current_interval = last_two[1].idx - last_two[0].idx

        return current_interval >= trend.rhythm_interval * RHYTHM_BREAK_FACTOR

    def _classify_transition(
        self,
        trend: TrendState,
        trend_weakening: bool,
        div_chain: int,
        new_zone: bool,
    ) -> TransitionType:
        """
        전이 타입을 분류한다.

        [Variant B 채택 - A/B/C 실험 결과]
        기존(A): trend_weakening AND div>=2 AND new_zone → 3개 reversal (new_zone 3/243만 발화)
        채택(B): trend_weakening AND (div>=2 OR new_zone) → 242개 reversal
        이유:
        - new_zone은 BTC 30k candles에서 3회만 발화 → AND 조건의 병목
        - div>=2는 추세 약화 시 거의 항상 동반 (242/243)
        - OR 완화는 기존 score>=4 신호를 더 정확히 분류할 뿐, 신호를 추가하지 않음
        - 전체 신호 수 불변 (494), precision 불변 (0.3047)
        - reversal precision 0.3008, MFE 0.0060 → 의미 있는 전방 움직임

        - 추세 약화 + (다이버전스 2+ 또는 새 zone) → trend_reversal
        - 추세 약화 없이 zone 반응만 → single_bounce
        - 그 외 → continuation
        """
        if trend_weakening and (div_chain >= 2 or new_zone):
            return TransitionType.TREND_REVERSAL
        elif not trend_weakening:
            return TransitionType.SINGLE_BOUNCE
        else:
            return TransitionType.CONTINUATION
