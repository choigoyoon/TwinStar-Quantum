"""
Market Transition Engine - Zone Builder (Stage 3a)
===================================================
배경 구간(Stage 1) + L/H(Stage 2)를 합쳐서 확정 지지/저항 구간을 만든다.

[핵심 철학]
- 지지/저항은 선이 아니라 가격 구간이다.
- ZoneCandidate는 한번 생기면 정의가 바뀌지 않는다 (frozen).
- 배경에서 유래한 zone이든, L/H에서 유래한 zone이든 동일하게 취급.
- zone 이 피벗(L/H)과 겹치면 강화되고, 관통되면 약화/파괴된다.

[Stage 3 재점수화]
- 배경 구간에 L/H가 겹치면 → zone 강도 강화
- L/H 근처에 배경 구간이 없으면 → 새 zone 생성 (L/H 단독)
- zone 이 가격에 의해 관통되면 → broken 마킹

[이벤트 로그 방식]
zone_builder 도 background_builder 처럼 이벤트 로그 + get_state_at(t) 구조.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from core.market_transition_engine.config import (
    ZONE_WIDTH_PCT,
    ZONE_MIN_STRENGTH,
)
from core.market_transition_engine.types import (
    Pivot,
    PivotType,
    ZoneCandidate,
    ZoneStateAtT,
)
from core.market_transition_engine.background_builder import (
    BackgroundBuilder,
    BackgroundZoneState,
)

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Zone Event (이벤트 로그)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class ZoneEvent:
    """zone 에 발생한 이벤트"""
    t: int                    # 시점
    zone_id: int              # 어떤 zone 에 대한 이벤트인지
    event: str                # "touch", "bounce", "break", "pivot_anchor"
    price: float = 0.0
    volume: float = 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZoneBuilder
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ZoneBuilder:
    """
    Stage 3a: 배경 + L/H 를 합쳐서 확정 zone 을 만든다.

    사용법:
        builder = ZoneBuilder()
        builder.build(df_15m, bg_builder, pivots)
        zones_at_t = builder.get_state_at(t=500)
    """

    def __init__(self):
        self.zones: list[ZoneCandidate] = []
        self.events: list[ZoneEvent] = []
        self._next_id: int = 0
        self._built: bool = False

    def build(
        self,
        df_15m: pd.DataFrame,
        bg_builder: BackgroundBuilder,
        pivots: list[Pivot],
    ) -> None:
        """
        배경 구간 + L/H 를 합쳐서 확정 zone 을 만든다.

        Step 1: 배경 구간을 ZoneCandidate 로 변환 (from_background=True)
        Step 2: 각 L/H 피벗에 대해:
                - 기존 zone 과 겹치면 → pivot_anchor 이벤트 (강화)
                - 안 겹치면 → 새 zone 생성 (from_background=False)
        Step 3: 전체 15분봉 순방향 스캔 → touch/bounce/break 이벤트 기록
        """
        self.zones.clear()
        self.events.clear()
        self._next_id = 0

        # Step 1: 배경 → zone
        for cand in bg_builder.candidates:
            self._add_zone(
                price_low=cand.price_low,
                price_high=cand.price_high,
                born_at=cand.first_seen,
                from_background=True,
                anchor_pivots=(),
            )

        # Step 2: L/H → zone 강화 또는 신규 생성
        # confirmed_at 기준 정렬
        sorted_pivots = sorted(pivots, key=lambda p: p.confirmed_at)

        for pivot in sorted_pivots:
            matched_zone = self._find_overlapping_zone(pivot.price)

            if matched_zone is not None:
                # 기존 zone 에 피벗 앵커 추가
                self.events.append(ZoneEvent(
                    t=pivot.confirmed_at,
                    zone_id=matched_zone.zone_id,
                    event="pivot_anchor",
                    price=pivot.price,
                ))
            else:
                # 새 zone 생성
                half_width = pivot.price * ZONE_WIDTH_PCT / 2.0
                self._add_zone(
                    price_low=pivot.price - half_width,
                    price_high=pivot.price + half_width,
                    born_at=pivot.confirmed_at,
                    from_background=False,
                    anchor_pivots=(pivot.idx,),
                )

        # Step 3: 전체 스캔 → 이벤트 기록
        self._scan_events(df_15m)

        self._built = True
        logger.info(
            "Zones built: %d zones, %d events",
            len(self.zones), len(self.events),
        )

    def get_state_at(self, t: int) -> list[ZoneStateAtT]:
        """
        시점 t 에서의 모든 zone 상태를 반환한다.
        이벤트 로그를 t 까지 필터링해서 재구성.
        """
        if not self._built:
            raise RuntimeError("build() must be called first")

        result: list[ZoneStateAtT] = []

        for zone in self.zones:
            if zone.born_at > t:
                continue

            zone_events = [
                e for e in self.events
                if e.zone_id == zone.zone_id and e.t <= t
            ]

            touch_count = sum(
                1 for e in zone_events if e.event in ("touch", "bounce")
            )
            anchor_count = sum(
                1 for e in zone_events if e.event == "pivot_anchor"
            )
            strength = float(touch_count + anchor_count * 2)  # 피벗 앵커는 2배 가중
            last_touch = max(
                (e.t for e in zone_events if e.event in ("touch", "bounce")),
                default=zone.born_at,
            )
            is_broken = any(e.event == "break" for e in zone_events)
            broken_at = next(
                (e.t for e in zone_events if e.event == "break"),
                None,
            )

            result.append(ZoneStateAtT(
                zone_id=zone.zone_id,
                touch_count=touch_count,
                last_touch_at=last_touch,
                strength=strength,
                is_broken=is_broken,
                broken_at=broken_at,
            ))

        return result

    def get_nearest_zone_at(
        self, t: int, price: float
    ) -> Optional[tuple[ZoneCandidate, ZoneStateAtT, float]]:
        """
        시점 t, 가격 price 에서 가장 가까운 활성 zone 을 반환한다.

        Returns:
            (zone, state, proximity) or None
            proximity = 0.0 이면 zone 안에 있음, 양수이면 거리 비율
        """
        states = self.get_state_at(t)
        if not states:
            return None

        best = None
        best_prox = float("inf")

        for state in states:
            if state.is_broken:
                continue
            if state.strength < ZONE_MIN_STRENGTH:
                continue

            zone = self.zones[state.zone_id]
            mid = (zone.price_low + zone.price_high) / 2.0

            if zone.price_low <= price <= zone.price_high:
                prox = 0.0
            else:
                dist = min(abs(price - zone.price_low), abs(price - zone.price_high))
                prox = dist / mid if mid > 0 else float("inf")

            if prox < best_prox:
                best_prox = prox
                best = (zone, state, prox)

        return best

    # ── Internal ────────────────────────────────────────────

    def _add_zone(
        self,
        price_low: float,
        price_high: float,
        born_at: int,
        from_background: bool,
        anchor_pivots: tuple[int, ...],
    ) -> ZoneCandidate:
        zone = ZoneCandidate(
            zone_id=self._next_id,
            price_low=price_low,
            price_high=price_high,
            born_at=born_at,
            from_background=from_background,
            anchor_pivots=anchor_pivots,
        )
        self.zones.append(zone)
        self._next_id += 1
        return zone

    def _find_overlapping_zone(self, price: float) -> Optional[ZoneCandidate]:
        """가격이 겹치는 기존 zone 을 찾는다."""
        for zone in self.zones:
            if zone.price_low <= price <= zone.price_high:
                return zone
        return None

    def _scan_events(self, df_15m: pd.DataFrame) -> None:
        """전체 15분봉을 스캔하며 zone 이벤트를 기록한다."""
        prices = df_15m[["high", "low", "close", "volume"]].values
        n = len(prices)

        # 각 zone 의 break 여부 추적 (한번 broken 이면 더 이상 이벤트 안 남김)
        broken_set: set[int] = set()

        for t in range(n):
            bar_high = prices[t, 0]
            bar_low = prices[t, 1]
            bar_close = prices[t, 2]
            bar_vol = prices[t, 3]

            for zone in self.zones:
                if zone.born_at > t:
                    continue
                if zone.zone_id in broken_set:
                    continue

                # 겹침 확인
                if bar_low > zone.price_high or bar_high < zone.price_low:
                    continue

                # 관통: 봉이 zone 을 완전히 가로지름
                if bar_low < zone.price_low and bar_high > zone.price_high:
                    self.events.append(ZoneEvent(
                        t=t, zone_id=zone.zone_id, event="break",
                        price=bar_close, volume=bar_vol,
                    ))
                    broken_set.add(zone.zone_id)
                # 반등: close 가 zone 바깥
                elif bar_close > zone.price_high or bar_close < zone.price_low:
                    self.events.append(ZoneEvent(
                        t=t, zone_id=zone.zone_id, event="bounce",
                        price=bar_close, volume=bar_vol,
                    ))
                else:
                    self.events.append(ZoneEvent(
                        t=t, zone_id=zone.zone_id, event="touch",
                        price=bar_close, volume=bar_vol,
                    ))
