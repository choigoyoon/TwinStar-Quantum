"""
Market Transition Engine - L/H Builder (Stage 2a)
==================================================
MACD 4기점 기반으로 228 TF의 L/H 확정점(Pivot)을 생성한다.

[MACD 4기점이란?]
MACD 히스토그램의 부호 전환 시점을 기준으로 4가지 기점을 정의:
  1. 양→음 전환 (MACD hist가 양에서 음으로): 이전 구간의 H 확정
  2. 음→양 전환 (MACD hist가 음에서 양으로): 이전 구간의 L 확정
  3. 양 hist 극대점: 상승 모멘텀 피크
  4. 음 hist 극소점: 하락 모멘텀 피크

[핵심 원칙]
- 15분봉이 원자 단위이고, TF 배수(n)로 관측창을 만든다.
- L/H는 MACD hist 부호 전환으로 "확정"된다.
  hist가 양→음이면, 직전 양구간의 최고가가 H로 확정.
  hist가 음→양이면, 직전 음구간의 최저가가 L로 확정.
- confirmed_at = 부호 전환이 일어난 시점 (미래참조 방지).
  pivot.idx 는 실제 L/H 가격이 나타난 시점이고,
  confirmed_at 은 그것이 "확정"된 시점이다.
  confirmed_at > idx 이므로, idx 시점에서 이 피벗을 아는 것은 미래참조.

[사용법]
    builder = LHBuilder()
    pivots = builder.build(df_15m, tf=228)
    # 또는 여러 TF 를 한번에:
    multi = builder.build_multi_tf(df_15m, tf_list=[1, 4, 16, 64, 228])
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import (
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    MAX_TF,
)
from core.market_transition_engine.types import Pivot, PivotType
from core.market_transition_engine.data_loader import aggregate_tf

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MACD 계산
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_macd(
    close: np.ndarray,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    MACD 계산. (macd_line, signal_line, histogram)
    EMA 기반.
    """
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """
    지수이동평균 (EMA).
    NaN 값이 앞에 있는 배열 (예: macd_line) 도 처리한다.
    유효한(non-NaN) 값이 시작되는 지점부터 EMA를 계산한다.
    """
    result = np.full_like(data, np.nan, dtype=np.float64)
    if len(data) < period:
        return result

    # NaN 이 아닌 첫 인덱스 찾기
    valid_start = 0
    for i in range(len(data)):
        if not np.isnan(data[i]):
            valid_start = i
            break
    else:
        return result  # 전부 NaN

    valid_data = data[valid_start:]
    if len(valid_data) < period:
        return result

    # 첫 값은 SMA
    sma_start = valid_start + period - 1
    result[sma_start] = np.mean(valid_data[:period])
    multiplier = 2.0 / (period + 1)

    for i in range(sma_start + 1, len(data)):
        if np.isnan(data[i]):
            continue
        result[i] = data[i] * multiplier + result[i - 1] * (1 - multiplier)

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LHBuilder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LHBuilder:
    """
    MACD 4기점 기반 L/H(Pivot) 빌더.

    TF 배수(n)로 15분봉을 묶은 관측창에서 MACD 를 계산하고,
    히스토그램 부호 전환으로 L/H 를 확정한다.
    """

    def build(
        self, df_15m: pd.DataFrame, tf: int = MAX_TF
    ) -> list[Pivot]:
        """
        단일 TF 에서 L/H 피벗 리스트를 생성한다.

        Args:
            df_15m: 15분봉 DataFrame
            tf: TF 배수 (1~228)

        Returns:
            list[Pivot], confirmed_at 기준 정렬
        """
        if tf < 1 or tf > MAX_TF:
            raise ValueError(f"TF must be 1~{MAX_TF}, got {tf}")

        # TF 집계 (lazy)
        df_tf = aggregate_tf(df_15m, n=tf)
        if len(df_tf) < MACD_SLOW + MACD_SIGNAL:
            logger.warning("Not enough data for MACD at TF=%d: %d rows", tf, len(df_tf))
            return []

        close = df_tf["close"].values
        high = df_tf["high"].values
        low = df_tf["low"].values

        _, _, histogram = compute_macd(close)

        pivots = self._extract_pivots_from_histogram(
            histogram, high, low, tf, len(df_15m)
        )

        # confirmed_at 기준 정렬
        pivots.sort(key=lambda p: p.confirmed_at)

        logger.info("TF=%d: %d pivots found", tf, len(pivots))
        return pivots

    def build_multi_tf(
        self,
        df_15m: pd.DataFrame,
        tf_list: Optional[list[int]] = None,
    ) -> dict[int, list[Pivot]]:
        """
        여러 TF 에서 L/H 를 한번에 생성한다.

        Args:
            df_15m: 15분봉 DataFrame
            tf_list: TF 배수 리스트 (default: [1, 4, 16, 64, 228])

        Returns:
            {tf: [Pivot, ...]} 딕셔너리
        """
        if tf_list is None:
            tf_list = [1, 4, 16, 64, MAX_TF]

        result: dict[int, list[Pivot]] = {}
        for tf in tf_list:
            try:
                result[tf] = self.build(df_15m, tf=tf)
            except ValueError as e:
                logger.warning("Skipping TF=%d: %s", tf, e)
                result[tf] = []

        return result

    def _extract_pivots_from_histogram(
        self,
        histogram: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        tf: int,
        n_15m: int,
    ) -> list[Pivot]:
        """
        MACD 히스토그램 부호 전환으로 L/H 를 추출한다.

        [규칙]
        - hist[i-1] >= 0 and hist[i] < 0 (양→음): 직전 양구간의 최고가 → H
        - hist[i-1] < 0 and hist[i] >= 0 (음→양): 직전 음구간의 최저가 → L

        [미래참조 방지]
        - confirmed_at = 부호 전환 시점 (tf 단위) × tf (15분봉 인덱스로 변환)
        - pivot.idx = 실제 극값 시점 × tf
        """
        pivots: list[Pivot] = []

        # 유효한 범위 (NaN 아닌 부분)
        valid_start = 0
        for i in range(len(histogram)):
            if not np.isnan(histogram[i]):
                valid_start = i
                break

        if valid_start >= len(histogram) - 1:
            return pivots

        # 현재 구간의 극값 추적
        segment_start = valid_start
        segment_high_idx = valid_start
        segment_high_val = high[valid_start]
        segment_low_idx = valid_start
        segment_low_val = low[valid_start]
        prev_sign_positive = histogram[valid_start] >= 0

        for i in range(valid_start + 1, len(histogram)):
            if np.isnan(histogram[i]):
                continue

            curr_sign_positive = histogram[i] >= 0

            # 극값 갱신
            if high[i] > segment_high_val:
                segment_high_val = high[i]
                segment_high_idx = i
            if low[i] < segment_low_val:
                segment_low_val = low[i]
                segment_low_idx = i

            # 부호 전환 감지
            if prev_sign_positive and not curr_sign_positive:
                # 양→음: 직전 양구간의 최고가가 H 로 확정
                pivot_idx_15m = min(segment_high_idx * tf, n_15m - 1)
                confirmed_at_15m = min(i * tf, n_15m - 1)

                pivots.append(Pivot(
                    idx=pivot_idx_15m,
                    price=segment_high_val,
                    pivot_type=PivotType.HIGH,
                    tf=tf,
                    confirmed_at=confirmed_at_15m,
                ))

                # 새 구간 시작
                segment_start = i
                segment_high_idx = i
                segment_high_val = high[i]
                segment_low_idx = i
                segment_low_val = low[i]

            elif not prev_sign_positive and curr_sign_positive:
                # 음→양: 직전 음구간의 최저가가 L 로 확정
                pivot_idx_15m = min(segment_low_idx * tf, n_15m - 1)
                confirmed_at_15m = min(i * tf, n_15m - 1)

                pivots.append(Pivot(
                    idx=pivot_idx_15m,
                    price=segment_low_val,
                    pivot_type=PivotType.LOW,
                    tf=tf,
                    confirmed_at=confirmed_at_15m,
                ))

                # 새 구간 시작
                segment_start = i
                segment_high_idx = i
                segment_high_val = high[i]
                segment_low_idx = i
                segment_low_val = low[i]

            prev_sign_positive = curr_sign_positive

        return pivots


def get_pivots_known_at(pivots: list[Pivot], t: int) -> list[Pivot]:
    """
    시점 t 에서 "알 수 있는" 피벗만 필터링한다.
    pivot.confirmed_at <= t 인 것만 반환.

    [미래참조 방지 핵심 함수]
    pivot.idx 가 아니라 confirmed_at 기준으로 필터링한다.
    """
    return [p for p in pivots if p.confirmed_at <= t]
