"""
Market Transition Engine - Score Engine (설명/정렬 전용)
=========================================================

★★★ 경고 ★★★
이 모듈이 산출하는 점수는 설명/정렬 전용이다.
통과/탈락 판정에 직접 사용하면 안 된다.
운영 판단은 반드시 transition_score >= SCORE_THRESHOLD(4) 로만 한다.

[근거]
- weighted_score를 운영 필터로 쓰는 건 실패했다.
- n_contributing_tfs가 228 TF에서 포화되기 때문이다.
  (median 225, p75 227, p90 228, 221~228 비중 72%+)
- 따라서 이 점수는 "왜 강한 전이인지" 설명하는 용도로만 쓴다.

[사용 가능한 변수]
- zone_proximity     : zone과의 거리
- zone_strength      : zone 강도
- dulling_intensity  : 둔화 강도
- trend_magnitude    : 추세 강도
- div_chain_max      : 다이버전스 체인 최대 길이
- new_zone_appeared  : 새 zone 출현 여부

[사용 금지 변수]
- n_contributing_tfs : 228 TF에서 포화 → 설명력 없음

[출력]
- explanation_score: 0~100 정규화 점수 (설명 전용)
- explanation: 사람이 읽을 수 있는 설명 문장
"""

from __future__ import annotations

import logging
from typing import Optional

from core.market_transition_engine.types import (
    TransitionCandidate,
    TrendDirection,
)

logger = logging.getLogger(__name__)


class ScoreEngine:
    """
    ★ 설명/정렬 전용 점수 엔진 ★
    운영 필터로 사용 금지.
    """

    def score(self, candidate: TransitionCandidate) -> TransitionCandidate:
        """
        전이 후보에 설명 점수와 설명 문장을 부여한다.

        기존 TransitionCandidate 를 수정하여 반환한다.
        (explanation_score, explanation 필드 갱신)

        Returns:
            동일 객체 (explanation_score, explanation 갱신됨)
        """
        components: list[tuple[str, float]] = []

        # ① zone 근접도 (가까울수록 높음, 0~25점)
        if candidate.zone_proximity <= 0:
            prox_score = 25.0
            components.append(("zone 내부에 위치", 25.0))
        elif candidate.zone_proximity < 0.01:
            prox_score = 20.0
            components.append(("zone 1% 이내 근접", 20.0))
        elif candidate.zone_proximity < 0.02:
            prox_score = 10.0
            components.append(("zone 2% 이내 근접", 10.0))
        else:
            prox_score = 0.0

        # ② zone 강도 (0~20점)
        strength_score = min(20.0, candidate.zone_strength * 2.0)
        if strength_score > 0:
            components.append((f"zone 강도 {candidate.zone_strength:.0f}", strength_score))

        # ③ 둔화 강도 (0~20점)
        dull_score = min(20.0, candidate.dulling_intensity * 40.0)
        if dull_score > 0:
            components.append((f"둔화 {candidate.dulling_intensity:.2f}", dull_score))

        # ④ 추세 강도 (0~15점)
        mag = candidate.trend_before.magnitude
        if mag > 0:
            # 추세가 강했는데 둔화 → 전이 설명력 높음
            mag_score = min(15.0, mag / 100.0 * 15.0)
            components.append((f"직전 추세 크기 {mag:.0f}", mag_score))
        else:
            mag_score = 0.0

        # ⑤ 다이버전스 체인 (0~15점)
        div_score = min(15.0, candidate.div_chain_length * 5.0)
        if div_score > 0:
            components.append((f"다이버 체인 {candidate.div_chain_length}연속", div_score))

        # ⑥ 새 zone 출현 (0~5점)
        new_zone_score = 5.0 if candidate.new_zone_appeared else 0.0
        if new_zone_score > 0:
            components.append(("새 zone 출현", 5.0))

        # 합산 (0~100)
        total = prox_score + strength_score + dull_score + mag_score + div_score + new_zone_score
        total = min(100.0, total)

        # 설명 문장 생성
        direction = candidate.trend_before.direction
        if direction == TrendDirection.BEARISH:
            dir_str = "하락 추세"
            reversal_str = "상승 전환"
        elif direction == TrendDirection.BULLISH:
            dir_str = "상승 추세"
            reversal_str = "하락 전환"
        else:
            dir_str = "횡보"
            reversal_str = "방향 전환"

        reasons = [desc for desc, _ in components if _ > 0]
        reason_str = ", ".join(reasons) if reasons else "근거 부족"

        explanation = (
            f"[score={candidate.score}, expl={total:.0f}] "
            f"기존 {dir_str}에서 {reversal_str} 가능성. "
            f"근거: {reason_str}"
        )

        # 필드 갱신
        candidate.explanation_score = total
        candidate.explanation = explanation

        return candidate

    def score_all(
        self, candidates: list[TransitionCandidate]
    ) -> list[TransitionCandidate]:
        """
        전체 후보에 설명 점수를 부여하고, explanation_score 기준 내림차순 정렬.
        """
        for cand in candidates:
            self.score(cand)

        candidates.sort(key=lambda c: c.explanation_score, reverse=True)
        return candidates
