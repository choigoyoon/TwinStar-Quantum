"""
Market Transition Engine - Divergence Builder (Stage 2b)
========================================================
가격↔MACD 다이버전스의 누적을 계산한다.

[핵심 철학]
- 다이버전스는 독립 신호가 아니라, 힘 불균형의 누적이다.
- bullish div: 가격은 낮아지는데 MACD는 높아짐 (하락 힘 약화)
- bearish div: 가격은 높아지는데 MACD는 낮아짐 (상승 힘 약화)
- 연속으로 이어지는 div chain 이 길수록 전이 가능성이 높다.

[구현]
- 인접한 같은 타입의 Pivot 쌍을 비교해서 다이버전스를 감지한다.
  - L→L 비교: bullish div 후보
  - H→H 비교: bearish div 후보
- confirmed_at 기준으로만 판단 (미래참조 방지).

[사용법]
    builder = DivergenceBuilder()
    divs = builder.build(df_15m, pivots, tf=228)
    chain = builder.get_max_chain_at(divs, t=1000)
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import MACD_FAST, MACD_SLOW, MACD_SIGNAL
from core.market_transition_engine.types import (
    DivergenceRecord,
    DivergenceType,
    Pivot,
    PivotType,
)
from core.market_transition_engine.lh_builder import compute_macd, get_pivots_known_at

logger = logging.getLogger(__name__)


class DivergenceBuilder:
    """
    가격↔MACD 다이버전스 빌더.
    Pivot 쌍을 비교해서 다이버전스를 감지하고 체인 길이를 추적한다.
    """

    def build(
        self,
        df_15m: pd.DataFrame,
        pivots: list[Pivot],
        tf: int = 1,
    ) -> list[DivergenceRecord]:
        """
        피벗 리스트에서 다이버전스를 감지한다.

        Args:
            df_15m: 15분봉 DataFrame (MACD 계산용)
            pivots: LHBuilder 가 생성한 피벗 리스트
            tf: 해당 피벗들의 TF 배수

        Returns:
            list[DivergenceRecord], end_idx 기준 정렬
        """
        if len(pivots) < 2:
            return []

        # MACD 계산 (15분봉 기준)
        close = df_15m["close"].values
        macd_line, _, histogram = compute_macd(close)

        # 같은 타입끼리 분리
        highs = [p for p in pivots if p.pivot_type == PivotType.HIGH]
        lows = [p for p in pivots if p.pivot_type == PivotType.LOW]

        # confirmed_at 기준 정렬
        highs.sort(key=lambda p: p.confirmed_at)
        lows.sort(key=lambda p: p.confirmed_at)

        records: list[DivergenceRecord] = []

        # H→H 비교: bearish divergence 감지
        records.extend(self._compare_pairs(highs, macd_line, DivergenceType.BEARISH, tf))

        # L→L 비교: bullish divergence 감지
        records.extend(self._compare_pairs(lows, macd_line, DivergenceType.BULLISH, tf))

        # end_idx 기준 정렬
        records.sort(key=lambda r: r.end_idx)

        logger.info(
            "TF=%d: %d divergences (bull=%d, bear=%d)",
            tf, len(records),
            sum(1 for r in records if r.div_type == DivergenceType.BULLISH),
            sum(1 for r in records if r.div_type == DivergenceType.BEARISH),
        )

        return records

    def _compare_pairs(
        self,
        pivots_same_type: list[Pivot],
        macd_line: np.ndarray,
        expected_type: DivergenceType,
        tf: int,
    ) -> list[DivergenceRecord]:
        """
        같은 타입의 인접 피벗 쌍을 비교해서 다이버전스를 감지한다.

        bearish div (H→H): 가격 ↑ but MACD ↓
        bullish div (L→L): 가격 ↓ but MACD ↑
        """
        records: list[DivergenceRecord] = []

        for i in range(1, len(pivots_same_type)):
            prev = pivots_same_type[i - 1]
            curr = pivots_same_type[i]

            # 피벗 위치에서의 MACD 값 (15분봉 인덱스 기준)
            prev_macd = self._get_macd_at(macd_line, prev.idx)
            curr_macd = self._get_macd_at(macd_line, curr.idx)

            if prev_macd is None or curr_macd is None:
                continue

            price_delta = curr.price - prev.price
            macd_delta = curr_macd - prev_macd

            is_div = False

            if expected_type == DivergenceType.BEARISH:
                # H→H: 가격 올랐는데 MACD 내렸으면 bearish div
                if price_delta > 0 and macd_delta < 0:
                    is_div = True
            else:
                # L→L: 가격 내렸는데 MACD 올랐으면 bullish div
                if price_delta < 0 and macd_delta > 0:
                    is_div = True

            if is_div:
                records.append(DivergenceRecord(
                    start_idx=prev.confirmed_at,  # 확정 시점 기준
                    end_idx=curr.confirmed_at,
                    div_type=expected_type,
                    price_delta=price_delta,
                    macd_delta=macd_delta,
                    tf=tf,
                ))

        return records

    @staticmethod
    def _get_macd_at(macd_line: np.ndarray, idx: int) -> Optional[float]:
        """15분봉 인덱스에서 MACD 값을 안전하게 가져온다."""
        if idx < 0 or idx >= len(macd_line):
            return None
        val = macd_line[idx]
        if np.isnan(val):
            return None
        return float(val)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 체인 분석 유틸리티
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_divs_known_at(
    records: list[DivergenceRecord], t: int
) -> list[DivergenceRecord]:
    """
    시점 t 에서 알 수 있는 다이버전스만 필터링.
    end_idx <= t 인 것만 반환.
    """
    return [r for r in records if r.end_idx <= t]


def get_max_chain_at(
    records: list[DivergenceRecord],
    t: int,
    div_type: Optional[DivergenceType] = None,
) -> int:
    """
    시점 t 에서의 최대 연속 다이버전스 체인 길이.

    연속 = 같은 타입의 div 가 끊기지 않고 이어지는 것.
    체인이 끊기는 조건: 반대 타입의 div 가 사이에 끼어들거나, 간격이 너무 벌어지거나.

    Args:
        records: 전체 다이버전스 기록
        t: 시점
        div_type: 특정 타입만 볼 경우 (None 이면 양쪽 다 체크하고 max)

    Returns:
        최대 체인 길이 (0 = div 없음)
    """
    known = get_divs_known_at(records, t)
    if not known:
        return 0

    if div_type is not None:
        return _chain_length(known, div_type)

    bull_chain = _chain_length(known, DivergenceType.BULLISH)
    bear_chain = _chain_length(known, DivergenceType.BEARISH)
    return max(bull_chain, bear_chain)


def _chain_length(
    records: list[DivergenceRecord], div_type: DivergenceType
) -> int:
    """특정 타입의 최근 연속 체인 길이를 계산한다."""
    typed = [r for r in records if r.div_type == div_type]
    if not typed:
        return 0

    # end_idx 역순으로 연속성 체크
    typed.sort(key=lambda r: r.end_idx, reverse=True)

    chain = 1
    for i in range(1, len(typed)):
        # 이전 div 의 start_idx 와 현재 div 의 end_idx 가 연결되어야 함
        if typed[i].end_idx <= typed[i - 1].start_idx:
            chain += 1
        else:
            break

    return chain
