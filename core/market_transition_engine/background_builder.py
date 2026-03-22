"""
Market Transition Engine - Background Builder (Stage 1)
========================================================
L/H를 모르는 상태에서 OHLCV만으로 "여기 뭔가 있었다"를 잡는다.

[역할]
- 거래량 클러스터 감지: 특정 가격대에서 거래량이 반복 집중
- 반복 반응 구간 감지: 같은 가격대를 여러 번 터치/반등
- 가격 리듬 감지: 스윙 간격의 규칙성

[구조 - 피드백 반영]
- BackgroundZoneCandidate: 불변 구간 정의
- BackgroundEvent: 이벤트 로그 (터치, 반등, 관통, 거래량 스파이크)
- get_state_at(t): 로그를 t까지 필터링해서 상태를 재구성
  → 전 시점 배열을 저장하지 않으므로 메모리 가볍다.

[미래참조 방지]
- 모든 판단은 시점 t 이하의 데이터만 사용한다.
- BackgroundZoneCandidate.first_seen 이후에만 해당 구간이 존재한다.

[giant zone 문제 해결 - v2]
- _detect_reaction_zones: 적응형 gap 계산 + 클러스터 최대 너비 제한
- _merge_overlapping_zones: 병합 결과가 MAX_ZONE_WIDTH_PCT 초과 시 병합 거부
- _split_oversized_zones: 병합 후 과대 zone 을 밀도 기반으로 분할
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import (
    BG_MIN_TOUCHES,
    BG_VOLUME_CLUSTER_STD,
    BG_ZONE_MERGE_PCT,
)
from core.market_transition_engine.types import (
    BackgroundEvent,
    BackgroundEventType,
    BackgroundZoneCandidate,
)

logger = logging.getLogger(__name__)

# ── zone 크기 제한 상수 ─────────────────────────────────────
# 개별 zone 의 최대 허용 너비 (mid 가격 대비 비율)
# 예: BTC $90k 기준 5% = $4,500 → 지지/저항 구간으로 합리적
MAX_ZONE_WIDTH_PCT: float = 0.05

# 반응 구간 클러스터링 gap 상한 (절대 비율)
# BG_ZONE_MERGE_PCT * 4 = 2% 는 BTC 에서 너무 넓으므로 1% 로 제한
REACTION_CLUSTER_GAP_PCT: float = 0.01


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BackgroundBuilder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BackgroundBuilder:
    """
    Stage 1: OHLCV-only 배경 구간 빌더.

    사용법:
        builder = BackgroundBuilder()
        builder.build(df_15m)
        state = builder.get_state_at(t=500)
    """

    def __init__(self):
        self.candidates: list[BackgroundZoneCandidate] = []
        self.events: list[BackgroundEvent] = []
        self._next_zone_id: int = 0
        self._built: bool = False

    def build(self, df_15m: pd.DataFrame) -> None:
        """
        15분봉 전체를 순차적으로 스캔하며 배경 구간 + 이벤트 로그를 생성한다.
        시점 0부터 끝까지 한 번만 순방향 스캔한다.
        """
        self.candidates.clear()
        self.events.clear()
        self._next_zone_id = 0

        prices = df_15m[["open", "high", "low", "close", "volume"]].values
        n = len(prices)

        if n < BG_MIN_TOUCHES * 2:
            logger.warning("Not enough data for background building: %d rows", n)
            self._built = True
            return

        # Step 1: 거래량 프로파일 기반 가격대 클러스터 감지
        self._detect_volume_clusters(prices, n)

        # Step 2: 반복 반응 구간 감지 (스윙 극점 기반)
        self._detect_reaction_zones(prices, n)

        # Step 3: 겹치는 구간 병합 (너비 제한 적용)
        self._merge_overlapping_zones()

        # Step 3.5: 과대 zone 분할 (밀도 기반)
        self._split_oversized_zones(prices, n)

        # Step 4: 전체 이벤트 로그 생성 (순방향 스캔)
        self._scan_events(prices, n)

        self._built = True
        logger.info(
            "Background built: %d candidates, %d events",
            len(self.candidates), len(self.events),
        )

    def get_state_at(self, t: int) -> list[BackgroundZoneState]:
        """
        시점 t 에서의 배경 구간 상태를 반환한다.
        이벤트 로그를 t 까지 필터링해서 상태를 재구성한다.
        전 시점 배열을 저장하지 않는다.

        Args:
            t: 15분봉 인덱스

        Returns:
            시점 t 에서 존재하는 배경 구간들의 상태 리스트
        """
        if not self._built:
            raise RuntimeError("build() must be called first")

        # t 이전에 생성된 candidates 만 필터
        active = [c for c in self.candidates if c.first_seen <= t]
        if not active:
            return []

        # 각 candidate 별로 t 까지의 이벤트를 집계
        result = []
        for cand in active:
            events_for_zone = [
                e for e in self.events
                if e.zone_id == cand.zone_id and e.t <= t
            ]

            touch_count = sum(
                1 for e in events_for_zone
                if e.event_type in (
                    BackgroundEventType.TOUCH,
                    BackgroundEventType.BOUNCE,
                )
            )
            vol_sum = sum(e.volume for e in events_for_zone)
            last_touch = max((e.t for e in events_for_zone), default=cand.first_seen)
            is_broken = any(
                e.event_type == BackgroundEventType.PENETRATE
                for e in events_for_zone
            )

            result.append(BackgroundZoneState(
                zone_id=cand.zone_id,
                candidate=cand,
                touch_count=touch_count,
                volume_weight=vol_sum,
                last_touch_at=last_touch,
                is_broken=is_broken,
            ))

        return result

    # ── Step 1: 거래량 클러스터 ─────────────────────────────

    def _detect_volume_clusters(self, prices: np.ndarray, n: int) -> None:
        """
        가격대별 거래량 프로파일을 만들고, 거래량이 집중된 구간을 찾는다.
        히스토그램 방식: 가격 범위를 bin 으로 나누고, 거래량을 누적.
        """
        all_highs = prices[:, 1]
        all_lows = prices[:, 2]
        all_volumes = prices[:, 4]

        price_min = np.min(all_lows)
        price_max = np.max(all_highs)
        price_range = price_max - price_min

        if price_range <= 0:
            return

        # 가격대를 50개 bin 으로 나눔
        n_bins = 50
        bin_edges = np.linspace(price_min, price_max, n_bins + 1)
        vol_profile = np.zeros(n_bins)

        # 각 봉의 거래량을 해당 가격 범위 bin 에 분배
        for i in range(n):
            low_i = all_lows[i]
            high_i = all_highs[i]
            vol_i = all_volumes[i]

            # 이 봉이 걸치는 bin 범위
            bin_start = max(0, int((low_i - price_min) / price_range * n_bins))
            bin_end = min(n_bins - 1, int((high_i - price_min) / price_range * n_bins))

            if bin_start > bin_end:
                continue

            # 균등 분배
            spread = bin_end - bin_start + 1
            for b in range(bin_start, bin_end + 1):
                vol_profile[b] += vol_i / spread

        # 거래량이 평균 + BG_VOLUME_CLUSTER_STD * std 이상인 bin 을 클러스터로
        vol_mean = np.mean(vol_profile)
        vol_std = np.std(vol_profile)
        threshold = vol_mean + BG_VOLUME_CLUSTER_STD * vol_std

        if vol_std == 0:
            return

        for b in range(n_bins):
            if vol_profile[b] >= threshold:
                zone_low = bin_edges[b]
                zone_high = bin_edges[b + 1]

                # 이 가격대에 처음 도달한 시점 찾기
                first_seen = 0
                for i in range(n):
                    if all_lows[i] <= zone_high and all_highs[i] >= zone_low:
                        first_seen = i
                        break

                self._add_candidate(zone_low, zone_high, first_seen, vol_profile[b])

    # ── Step 2: 반복 반응 구간 ──────────────────────────────

    def _detect_reaction_zones(self, prices: np.ndarray, n: int) -> None:
        """
        로컬 스윙 극점(local min/max)을 찾고,
        같은 가격대에 여러 번 모이는 곳을 반응 구간으로 등록한다.

        [v2 변경] 적응형 gap 계산 + 클러스터 최대 너비 제한으로
        가격이 넓은 범위를 걸쳐도 하나의 거대 클러스터로 묶이지 않도록 한다.
        """
        # 로컬 min/max 찾기 (좌우 5봉 기준)
        lookback = 5
        swing_prices: list[float] = []
        swing_indices: list[int] = []

        lows = prices[:, 2]
        highs = prices[:, 1]

        for i in range(lookback, n - lookback):
            # local low
            window_lows = lows[i - lookback: i + lookback + 1]
            if lows[i] == np.min(window_lows):
                swing_prices.append(lows[i])
                swing_indices.append(i)
            # local high
            window_highs = highs[i - lookback: i + lookback + 1]
            if highs[i] == np.max(window_highs):
                swing_prices.append(highs[i])
                swing_indices.append(i)

        if len(swing_prices) < BG_MIN_TOUCHES:
            return

        # 스윙 극점들을 가격 기준으로 클러스터링
        # v2: 적응형 gap 기준 + 클러스터 너비 제한
        sorted_pairs = sorted(zip(swing_prices, swing_indices))

        cluster_start = 0
        for i in range(1, len(sorted_pairs)):
            prev_price = sorted_pairs[i - 1][0]
            curr_price = sorted_pairs[i][0]
            mid = (prev_price + curr_price) / 2.0
            gap_pct = abs(curr_price - prev_price) / mid if mid > 0 else 1.0

            # v2: REACTION_CLUSTER_GAP_PCT (1%) 기준으로 클러스터 분리
            # 추가로 현재 클러스터의 누적 너비가 MAX_ZONE_WIDTH_PCT 초과 시 강제 분리
            cluster_low = sorted_pairs[cluster_start][0]
            cluster_width_pct = (curr_price - cluster_low) / mid if mid > 0 else 1.0

            should_split = (
                gap_pct > REACTION_CLUSTER_GAP_PCT
                or cluster_width_pct > MAX_ZONE_WIDTH_PCT
            )

            if should_split:
                self._maybe_register_cluster(sorted_pairs[cluster_start:i])
                cluster_start = i

        # 마지막 클러스터
        self._maybe_register_cluster(sorted_pairs[cluster_start:])

    def _maybe_register_cluster(
        self, pairs: list[tuple[float, int]]
    ) -> None:
        """클러스터의 터치 횟수가 기준 이상이면 배경 구간으로 등록"""
        if len(pairs) < BG_MIN_TOUCHES:
            return

        prices_in_cluster = [p for p, _ in pairs]
        indices_in_cluster = [i for _, i in pairs]

        zone_low = min(prices_in_cluster)
        zone_high = max(prices_in_cluster)
        first_seen = min(indices_in_cluster)

        self._add_candidate(zone_low, zone_high, first_seen, 0.0)

    # ── Step 3: 겹치는 구간 병합 ────────────────────────────

    def _merge_overlapping_zones(self) -> None:
        """
        가격이 겹치는 배경 구간을 병합한다.

        [v2 변경] 병합 결과의 너비가 MAX_ZONE_WIDTH_PCT 를 초과하면
        병합하지 않고 별도 zone 으로 유지한다.
        """
        if len(self.candidates) <= 1:
            return

        # 가격 하한 기준 정렬
        self.candidates.sort(key=lambda c: c.price_low)

        merged: list[BackgroundZoneCandidate] = []
        current = self.candidates[0]

        for i in range(1, len(self.candidates)):
            nxt = self.candidates[i]
            mid = (current.price_high + nxt.price_low) / 2.0
            gap_pct = (nxt.price_low - current.price_high) / mid if mid > 0 else 1.0

            # 병합 후보 너비 체크
            merged_low = min(current.price_low, nxt.price_low)
            merged_high = max(current.price_high, nxt.price_high)
            merged_mid = (merged_low + merged_high) / 2.0
            merged_width_pct = (
                (merged_high - merged_low) / merged_mid
                if merged_mid > 0 else 1.0
            )

            # v2: gap 이 충분히 가깝고, 병합 결과가 MAX_ZONE_WIDTH_PCT 이내일 때만 병합
            if gap_pct <= BG_ZONE_MERGE_PCT and merged_width_pct <= MAX_ZONE_WIDTH_PCT:
                # 병합
                current = BackgroundZoneCandidate(
                    zone_id=current.zone_id,
                    price_low=merged_low,
                    price_high=merged_high,
                    first_seen=min(current.first_seen, nxt.first_seen),
                    touch_count=current.touch_count + nxt.touch_count,
                    volume_weight=current.volume_weight + nxt.volume_weight,
                )
            else:
                merged.append(current)
                current = nxt

        merged.append(current)
        self.candidates = merged

        # zone_id 재부여
        for i, c in enumerate(self.candidates):
            c.zone_id = i
        self._next_zone_id = len(self.candidates)

    # ── Step 3.5: 과대 zone 분할 ────────────────────────────

    def _split_oversized_zones(
        self, prices: np.ndarray, n: int
    ) -> None:
        """
        병합 후에도 MAX_ZONE_WIDTH_PCT 를 초과하는 zone 이 있으면
        내부 스윙 밀도를 기반으로 하위 zone 으로 분할한다.

        [원칙]
        - 인위적으로 zone 수를 늘리지 않는다.
        - 밀도가 높은 가격 구간만 하위 zone 으로 승격한다.
        - 밀도가 낮으면 해당 zone 을 그대로 제거 (BG_MIN_TOUCHES 미만 시).
        - 미래참조 없음: first_seen 은 해당 구간 내 최초 도달 시점.
        """
        lows = prices[:, 2]
        highs = prices[:, 1]

        new_candidates: list[BackgroundZoneCandidate] = []

        for cand in self.candidates:
            mid = (cand.price_low + cand.price_high) / 2.0
            width_pct = (
                (cand.price_high - cand.price_low) / mid
                if mid > 0 else 0.0
            )

            if width_pct <= MAX_ZONE_WIDTH_PCT:
                # 정상 크기 → 그대로 유지
                new_candidates.append(cand)
                continue

            # 과대 zone → 내부를 sub-bin 으로 나누어 밀도 분석
            logger.info(
                "Splitting oversized zone [%.1f - %.1f] (width %.2f%%)",
                cand.price_low, cand.price_high, width_pct * 100,
            )

            zone_range = cand.price_high - cand.price_low
            # sub-bin 개수: zone 너비를 MAX_ZONE_WIDTH_PCT 단위로 분할
            n_sub = max(2, int(zone_range / (mid * MAX_ZONE_WIDTH_PCT)))
            n_sub = min(n_sub, 50)  # 상한

            sub_edges = np.linspace(cand.price_low, cand.price_high, n_sub + 1)
            sub_counts = np.zeros(n_sub, dtype=int)
            sub_first_seen = np.full(n_sub, n, dtype=int)

            # 스윙 극점 밀도 계산 (해당 zone 가격 구간 내의 로컬 min/max)
            lookback = 5
            for i in range(lookback, n - lookback):
                price_val = None
                # local low
                window_lows = lows[i - lookback: i + lookback + 1]
                if lows[i] == np.min(window_lows) and cand.price_low <= lows[i] <= cand.price_high:
                    price_val = lows[i]
                # local high
                window_highs = highs[i - lookback: i + lookback + 1]
                if highs[i] == np.max(window_highs) and cand.price_low <= highs[i] <= cand.price_high:
                    price_val = highs[i]

                if price_val is not None:
                    # 어느 sub-bin 에 속하는지
                    b = int((price_val - cand.price_low) / zone_range * n_sub)
                    b = min(b, n_sub - 1)
                    sub_counts[b] += 1
                    if i < sub_first_seen[b]:
                        sub_first_seen[b] = i

            # 밀도 기반 필터: 평균 이상인 sub-bin 만 zone 으로 승격
            if np.sum(sub_counts) == 0:
                continue
            density_threshold = max(BG_MIN_TOUCHES, np.mean(sub_counts))

            # 인접한 고밀도 bin 을 연결하여 sub-zone 생성
            in_zone = False
            sub_low = 0.0
            sub_high = 0.0
            sub_touch = 0
            sub_vol = cand.volume_weight / max(1, n_sub)
            sub_fs = n

            for b in range(n_sub):
                if sub_counts[b] >= density_threshold:
                    if not in_zone:
                        sub_low = sub_edges[b]
                        sub_touch = 0
                        sub_fs = n
                        in_zone = True
                    sub_high = sub_edges[b + 1]
                    sub_touch += sub_counts[b]
                    sub_fs = min(sub_fs, int(sub_first_seen[b]))
                else:
                    if in_zone:
                        # sub-zone 등록
                        self._register_sub_zone(
                            new_candidates, sub_low, sub_high,
                            sub_fs, sub_touch, sub_vol,
                        )
                        in_zone = False

            # 마지막 sub-zone
            if in_zone:
                self._register_sub_zone(
                    new_candidates, sub_low, sub_high,
                    sub_fs, sub_touch, sub_vol,
                )

        self.candidates = new_candidates

        # zone_id 재부여
        for i, c in enumerate(self.candidates):
            c.zone_id = i
        self._next_zone_id = len(self.candidates)

        logger.info(
            "After split: %d candidates", len(self.candidates),
        )

    def _register_sub_zone(
        self,
        target: list[BackgroundZoneCandidate],
        price_low: float,
        price_high: float,
        first_seen: int,
        touch_count: int,
        volume_weight: float,
    ) -> None:
        """sub-zone 을 후보 리스트에 추가 (BG_MIN_TOUCHES 미만이면 무시)"""
        if touch_count < BG_MIN_TOUCHES:
            return

        # 너비가 0이면 최소 너비 부여
        if price_high <= price_low:
            mid = (price_high + price_low) / 2.0
            margin = mid * BG_ZONE_MERGE_PCT if mid > 0 else 1.0
            price_low = mid - margin
            price_high = mid + margin

        target.append(BackgroundZoneCandidate(
            zone_id=0,  # 나중에 재부여
            price_low=price_low,
            price_high=price_high,
            first_seen=first_seen,
            touch_count=touch_count,
            volume_weight=volume_weight,
        ))

    # ── Step 4: 이벤트 스캔 ─────────────────────────────────

    def _scan_events(self, prices: np.ndarray, n: int) -> None:
        """
        전체 15분봉을 순방향으로 스캔하며 각 배경 구간에 대한 이벤트를 기록한다.
        """
        for t in range(n):
            bar_high = prices[t, 1]
            bar_low = prices[t, 2]
            bar_close = prices[t, 3]
            bar_vol = prices[t, 4]

            for cand in self.candidates:
                if t < cand.first_seen:
                    continue

                # 가격이 구간과 겹치는지 확인
                if bar_low > cand.price_high or bar_high < cand.price_low:
                    continue

                # 구간 내부에 있음 → 이벤트 타입 판별
                zone_mid = (cand.price_low + cand.price_high) / 2.0
                zone_width = cand.price_high - cand.price_low

                # 관통: 봉이 구간을 완전히 가로지름
                if bar_low < cand.price_low and bar_high > cand.price_high:
                    evt_type = BackgroundEventType.PENETRATE
                # 반등: close 가 구간 바깥으로 나감
                elif (bar_close > cand.price_high or bar_close < cand.price_low):
                    evt_type = BackgroundEventType.BOUNCE
                else:
                    evt_type = BackgroundEventType.TOUCH

                self.events.append(BackgroundEvent(
                    t=t,
                    zone_id=cand.zone_id,
                    event_type=evt_type,
                    price=bar_close,
                    volume=bar_vol,
                ))

        # 거래량 스파이크 이벤트 추가 감지
        self._detect_volume_spike_events(prices, n)

    def _detect_volume_spike_events(
        self, prices: np.ndarray, n: int
    ) -> None:
        """구간 내에서 거래량이 급증한 시점을 별도 이벤트로 기록"""
        if not self.candidates:
            return

        volumes = prices[:, 4]
        # 이동평균 거래량 (20봉)
        window = 20
        if n < window:
            return

        vol_ma = np.convolve(volumes, np.ones(window) / window, mode="valid")
        # pad front with NaN-equivalent
        vol_ma = np.concatenate([np.full(window - 1, np.nan), vol_ma])

        for cand in self.candidates:
            zone_events = [
                e for e in self.events
                if e.zone_id == cand.zone_id
                and e.event_type == BackgroundEventType.TOUCH
            ]
            for evt in zone_events:
                t = evt.t
                if t < window or np.isnan(vol_ma[t]):
                    continue
                if volumes[t] > vol_ma[t] * (1 + BG_VOLUME_CLUSTER_STD):
                    self.events.append(BackgroundEvent(
                        t=t,
                        zone_id=cand.zone_id,
                        event_type=BackgroundEventType.VOLUME_SPIKE,
                        price=evt.price,
                        volume=volumes[t],
                    ))

    # ── Internal helpers ────────────────────────────────────

    def _add_candidate(
        self,
        price_low: float,
        price_high: float,
        first_seen: int,
        volume_weight: float,
    ) -> None:
        """배경 구간 후보를 추가한다."""
        # 너비가 0이면 최소 너비 부여
        if price_high <= price_low:
            mid = (price_high + price_low) / 2.0
            margin = mid * BG_ZONE_MERGE_PCT if mid > 0 else 1.0
            price_low = mid - margin
            price_high = mid + margin

        self.candidates.append(BackgroundZoneCandidate(
            zone_id=self._next_zone_id,
            price_low=price_low,
            price_high=price_high,
            first_seen=first_seen,
            volume_weight=volume_weight,
        ))
        self._next_zone_id += 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BackgroundZoneState: get_state_at 반환용
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class BackgroundZoneState:
    """시점 t 에서의 배경 구간 상태 (get_state_at 이 반환하는 객체)"""
    zone_id: int
    candidate: BackgroundZoneCandidate
    touch_count: int = 0
    volume_weight: float = 0.0
    last_touch_at: int = 0
    is_broken: bool = False
