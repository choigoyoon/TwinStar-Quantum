"""
Market Transition Engine - Configuration
=========================================
운영 상수를 한 곳에서 관리한다.
types.py, builder, engine 등 모든 모듈이 여기서 import 한다.

[불변 운영 규칙 - 검증 완료, 변경 금지]
- SCORE_THRESHOLD >= 4     : 전이 판단 통과 기준
- DULLING_RATIO  = 0.5     : 둔화 비율
- LABEL_HORIZON  = 16      : 사후 검증 라벨 (t+16, 검증 전용)
이 3개는 TF=1~10, TF=1~228 에서 모두 무너지지 않음을 확인했다.
"""

from __future__ import annotations

# ── 불변 운영 상수 (검증 완료, 변경 금지) ─────────────────────
SCORE_THRESHOLD: int = 4          # transition_score >= 4 이면 통과
DULLING_RATIO: float = 0.5        # 둔화 비율
LABEL_HORIZON: int = 16           # 사후 라벨 t+16 (labeler 전용)

# ── 15분봉 원자 단위 ──────────────────────────────────────────
BASE_TF_MINUTES: int = 15         # 원자 타임프레임 (분)
MAX_TF: int = 228                 # 관측창 최대 배수

# ── MACD 기본 파라미터 ────────────────────────────────────────
MACD_FAST: int = 12
MACD_SLOW: int = 26
MACD_SIGNAL: int = 9

# ── 배경(Background) 빌더 파라미터 ───────────────────────────
BG_MIN_TOUCHES: int = 3           # 배경 구간 최소 터치 횟수
BG_ZONE_MERGE_PCT: float = 0.005  # 가격 대비 0.5% 이내 구간은 병합
BG_VOLUME_CLUSTER_STD: float = 1.5  # 거래량 클러스터 기준 (표준편차 배수)

# ── Zone 빌더 파라미터 ───────────────────────────────────────
ZONE_WIDTH_PCT: float = 0.01      # zone 너비: 가격 대비 1%
ZONE_MIN_STRENGTH: int = 2        # zone 최소 강도

# ── Trend 빌더 파라미터 ──────────────────────────────────────
TREND_MIN_PIVOTS: int = 3         # 추세 판단 최소 피벗 수

# ── score_engine.py 관련 경고 ────────────────────────────────
# score_engine 이 산출하는 weighted_score / explanation_score 는
# ★ 설명 / 정렬 전용 ★ 이다.
# 통과/탈락 판정에 직접 사용하면 안 된다.
# 운영 판단은 반드시 transition_score >= SCORE_THRESHOLD 로만 한다.
#
# [근거] weighted_score 를 운영 필터로 쓰는 건 실패했다.
# n_contributing_tfs 가 228 TF에서 포화되기 때문이다.
#   - median 225, p75 227, p90 228, 221~228 비중 72%+
# 따라서 weighted_score 는 "왜 강한 전이인지" 설명용으로만 쓴다.

# ── n_contributing_tfs 사용 금지 경고 ────────────────────────
# 이 값을 핵심 변수로 사용하지 마라.
# 228 TF에서 포화되어 설명력이 사라졌다.
