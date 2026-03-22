"""
Market Transition Engine - Labeler (검증 전용)
===============================================
t+LABEL_HORIZON 사후 검증 라벨을 생성한다.

[핵심 철학]
- 라벨링은 검증용이고, 라이브 판단 로직과 분리한다.
- 이 모듈은 미래 데이터(t+16)를 의도적으로 참조한다.
- ★ 절대로 라이브 판단에 사용하면 안 된다 ★
- backtest_report.py 에서만 이 결과를 사용한다.

[라벨 기준]
- CONFIRMED: t+16 시점에서 예측 방향과 같은 방향으로 pct_change > threshold
- DENIED: 반대 방향으로 움직임
- AMBIGUOUS: 변화가 threshold 미만

[운영 규칙]
- LABEL_HORIZON = 16 (변경 금지)

[A/B 테스트 결과 반영 - LABEL_MIN_PCT 조정]
- baseline h=16, min=0.005: nothing% 60.5%, precision 0.328, decisive% 39.5%
- 채택안  h=16, min=0.003: nothing% 43.5%, precision 0.305, decisive% 56.5%
- 근거: 동일 신호 494개에서 ambiguous 17pp 감소, decisive 17pp 증가
- precision 하락(-2.35pp)은 "판정 불가→판정" 전환의 자연적 비용
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import LABEL_HORIZON
from core.market_transition_engine.types import (
    LabelVerdict,
    TransitionCandidate,
    TransitionLabel,
    TransitionType,
    TrendDirection,
)

logger = logging.getLogger(__name__)

# 라벨 확인 최소 변화율
# A/B 테스트 결과: 0.5%→0.3%로 완화 (nothing% 60.5%→43.5%, decisive% +17pp)
# 0.2%는 noise 영역, 0.5%는 과도하게 보수적 → 0.3%가 최적
LABEL_MIN_PCT: float = 0.003


class Labeler:
    """
    사후 검증 라벨러.
    ★ 검증 전용 ★ - 라이브 판단에 사용 금지.
    """

    def label(
        self,
        df_15m: pd.DataFrame,
        candidates: list[TransitionCandidate],
        horizon: int = LABEL_HORIZON,
    ) -> list[TransitionLabel]:
        """
        전이 후보들에 사후 검증 라벨을 부여한다.

        Args:
            df_15m: 15분봉 DataFrame
            candidates: 전이 후보 리스트
            horizon: 라벨 확인 기간 (기본 t+16)

        Returns:
            list[TransitionLabel]
        """
        close = df_15m["close"].values
        n = len(close)
        labels: list[TransitionLabel] = []

        for cand in candidates:
            t = cand.t
            t_horizon = t + horizon

            if t >= n or t_horizon >= n:
                # 미래 데이터 부족 → 라벨링 불가
                continue

            price_at_t = close[t]
            price_at_horizon = close[t_horizon]

            if price_at_t == 0:
                continue

            pct_change = (price_at_horizon - price_at_t) / price_at_t

            # 예측 방향 결정
            expected_up = self._expected_direction_up(cand)

            # 방향 일치 여부
            if expected_up is None:
                direction_matched = False
            elif expected_up:
                direction_matched = pct_change > 0
            else:
                direction_matched = pct_change < 0

            # 라벨 판정
            abs_pct = abs(pct_change)
            if abs_pct < LABEL_MIN_PCT:
                verdict = LabelVerdict.AMBIGUOUS
            elif direction_matched:
                verdict = LabelVerdict.CONFIRMED
            else:
                verdict = LabelVerdict.DENIED

            labels.append(TransitionLabel(
                t=t,
                verdict=verdict,
                price_at_t=price_at_t,
                price_at_horizon=price_at_horizon,
                pct_change=pct_change,
                direction_matched=direction_matched,
            ))

        confirmed = sum(1 for l in labels if l.verdict == LabelVerdict.CONFIRMED)
        denied = sum(1 for l in labels if l.verdict == LabelVerdict.DENIED)
        ambiguous = sum(1 for l in labels if l.verdict == LabelVerdict.AMBIGUOUS)

        logger.info(
            "Labels: %d total (confirmed=%d, denied=%d, ambiguous=%d)",
            len(labels), confirmed, denied, ambiguous,
        )

        return labels

    def _expected_direction_up(
        self, cand: TransitionCandidate
    ) -> Optional[bool]:
        """
        전이 후보의 예측 방향을 결정한다.

        - 기존 추세가 bearish + 전이 → 상승 예측 (True)
        - 기존 추세가 bullish + 전이 → 하락 예측 (False)
        - neutral → None (방향 불명)
        """
        if cand.trend_before.direction == TrendDirection.BEARISH:
            return True  # 하락→상승 전환 예측
        elif cand.trend_before.direction == TrendDirection.BULLISH:
            return False  # 상승→하락 전환 예측
        else:
            return None
