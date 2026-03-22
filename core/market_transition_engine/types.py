"""
Market Transition Engine - Type Definitions
=============================================
모든 모듈이 공유하는 dataclass, Enum, TypeAlias 를 정의한다.
운영 상수는 config.py 에서 관리한다 (여기서 정의하지 않는다).

[객체 역할]
- Pivot          : 228 TF 안에서 확정된 L 또는 H 지점
- BackgroundZoneCandidate : OHLCV만으로 잡은 반복 반응 구간 (Stage 1)
- BackgroundEvent : 배경 구간에 일어난 이벤트 로그 (터치, 돌파 등)
- ZoneCandidate  : 배경 + L/H 가 합쳐진 확정 지지/저항 구간 (불변)
- ZoneStateAtT   : 시점 t 에서 본 zone 의 누적 상태
- DivergenceRecord : 가격↔MACD 다이버전스 기록
- TrendState     : L/H 리듬 기반 추세 상태
- TransitionCandidate : 전이 후보
- TransitionLabel : 사후 검증 라벨 (labeler 전용, 라이브 판단과 분리)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PivotType(enum.Enum):
    """L/H 구분"""
    LOW = "L"
    HIGH = "H"


class TrendDirection(enum.Enum):
    """추세 방향"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class DivergenceType(enum.Enum):
    """다이버전스 종류"""
    BULLISH = "bullish"       # 가격 ↓ but MACD ↑ (하락 힘 약화)
    BEARISH = "bearish"       # 가격 ↑ but MACD ↓ (상승 힘 약화)


class BackgroundEventType(enum.Enum):
    """배경 구간에 일어난 이벤트 종류"""
    TOUCH = "touch"           # 가격이 구간에 닿음
    BOUNCE = "bounce"         # 닿고 반등
    PENETRATE = "penetrate"   # 관통
    VOLUME_SPIKE = "vol_spike"  # 구간 내 거래량 폭증


class TransitionType(enum.Enum):
    """전이 분류"""
    TREND_REVERSAL = "trend_reversal"    # 실제 추세 전환
    SINGLE_BOUNCE = "single_bounce"      # 단발성 반등
    CONTINUATION = "continuation"        # 기존 추세 이어감


class LabelVerdict(enum.Enum):
    """사후 검증 결과 (labeler 전용)"""
    CONFIRMED = "confirmed"   # t+16 이후 전이 확인됨
    DENIED = "denied"         # 전이 아니었음
    AMBIGUOUS = "ambiguous"   # 판단 불가


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage 2: Pivot (L/H 확정점)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class Pivot:
    """
    228 TF 안에서 확정된 L 또는 H 지점.
    15분봉 인덱스를 기준으로 위치를 잡는다.
    """
    idx: int                  # 15분봉 인덱스 (원자 단위)
    price: float              # 해당 시점 가격
    pivot_type: PivotType     # L or H
    tf: int                   # 이 피벗이 확정된 TF 배수
    confirmed_at: int         # 확정 시점 (15분봉 인덱스) - 미래참조 방지용


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage 1: Background (OHLCV-only 배경)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class BackgroundZoneCandidate:
    """
    L/H를 모르는 상태에서 OHLCV만으로 잡은 배경 구간.
    "여기서 뭔가 반복적으로 반응했다"는 증거.
    가격 구간 (선이 아니다).
    """
    zone_id: int              # 고유 ID
    price_low: float          # 구간 하한
    price_high: float         # 구간 상한
    first_seen: int           # 최초 발견 시점 (15분봉 인덱스)
    touch_count: int = 0      # 누적 터치 횟수
    volume_weight: float = 0.0  # 거래량 가중치 누적
    last_touch: int = 0       # 마지막 터치 시점


@dataclass
class BackgroundEvent:
    """
    배경 구간에 일어난 이벤트 로그.
    전 시점 배열 대신 이벤트 로그로 상태를 추적한다.
    get_state_at(t) 에서 이 로그를 필터링해서 상태를 재구성한다.
    """
    t: int                           # 이벤트 시점 (15분봉 인덱스)
    zone_id: int                     # 어떤 배경 구간에 대한 이벤트인지
    event_type: BackgroundEventType  # 이벤트 종류
    price: float                     # 이벤트 시점 가격
    volume: float = 0.0              # 이벤트 시점 거래량


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage 3: Zone (배경 + L/H 합쳐진 확정 지지/저항 구간)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class ZoneCandidate:
    """
    배경 구간 + L/H 가 합쳐져서 확정된 지지/저항 구간.
    한번 생기면 정의가 바뀌지 않는다 (frozen=True).
    가격 구간이다 (선이 아니다).
    """
    zone_id: int              # 고유 ID
    price_low: float          # 구간 하한
    price_high: float         # 구간 상한
    born_at: int              # zone 이 생성된 시점 (15분봉 인덱스)
    from_background: bool     # 배경에서 유래했는지
    anchor_pivots: tuple[int, ...] = ()  # 이 zone 에 연결된 피벗 인덱스들


@dataclass
class ZoneStateAtT:
    """
    시점 t 에서 특정 zone 의 누적 상태.
    zone_builder.get_state_at(t) 가 반환하는 객체.
    """
    zone_id: int
    touch_count: int = 0      # t 까지 누적 터치 횟수
    last_touch_at: int = 0    # 마지막 터치 시점
    strength: float = 0.0     # 구간 강도 (터치 + 거래량 기반)
    is_broken: bool = False   # 돌파되었는지
    broken_at: Optional[int] = None  # 돌파 시점


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage 2: Divergence (힘의 불균형 누적)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass(frozen=True)
class DivergenceRecord:
    """
    가격↔MACD 다이버전스 하나의 기록.
    다이버는 독립 신호가 아니라, 힘 불균형의 누적이다.
    """
    start_idx: int            # 다이버 시작 (15분봉 인덱스)
    end_idx: int              # 다이버 끝 (15분봉 인덱스)
    div_type: DivergenceType  # bullish / bearish
    price_delta: float        # 가격 변화량
    macd_delta: float         # MACD 변화량
    tf: int                   # 관측 TF 배수


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage 3: Trend (추세 = 다음 반응의 리듬)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TrendState:
    """
    L/H 간 리듬(간격, 방향, 크기) 기반 추세 상태.
    추세는 선이 아니라, 다음 반응의 리듬이다.
    """
    direction: TrendDirection
    magnitude: float = 0.0    # 추세 강도 (최근 스윙 크기의 가중 평균)
    rhythm_interval: float = 0.0  # L→H 또는 H→L 평균 간격 (15분봉 수)
    dulling: float = 0.0      # 둔화도 (0~1, DULLING_RATIO 와 비교용)
    pivot_count: int = 0      # 추세 판단에 사용된 피벗 수
    last_pivot_idx: int = 0   # 마지막 피벗 시점


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stage 4: Transition (전이)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TransitionCandidate:
    """
    전이 후보.
    전이 = "기존 추세 약화 + 과누적 + 새 지지/저항 출현"
    """
    t: int                       # 전이 감지 시점 (15분봉 인덱스)
    transition_type: TransitionType
    score: int                   # transition_score (운영 판단 기준, >= 4 통과)

    # 전이를 구성하는 근거들
    trend_before: TrendState     # 직전 추세 상태
    dulling_intensity: float     # 둔화 강도
    zone_proximity: float        # 가장 가까운 zone 까지 거리 비율
    zone_strength: float         # 해당 zone 의 강도
    div_chain_length: int        # 연속 다이버전스 체인 길이
    new_zone_appeared: bool      # 새 zone 이 최근 출현했는지

    # 설명용 (운영 필터에 직접 사용 금지)
    explanation_score: float = 0.0  # score_engine 이 산출하는 설명 점수
    explanation: str = ""           # 사람이 읽을 수 있는 설명 문장


@dataclass(frozen=True)
class TransitionLabel:
    """
    사후 검증 라벨. labeler.py 전용.
    라이브 판단 로직과 완전히 분리되어야 한다.
    t+LABEL_HORIZON 이후 데이터를 참조하므로, 라이브에서 절대 사용 금지.
    """
    t: int                       # 전이 시점
    verdict: LabelVerdict        # confirmed / denied / ambiguous
    price_at_t: float            # 전이 시점 가격
    price_at_horizon: float      # t+LABEL_HORIZON 시점 가격
    pct_change: float            # 가격 변화율
    direction_matched: bool      # 예측 방향과 실제 방향 일치 여부
