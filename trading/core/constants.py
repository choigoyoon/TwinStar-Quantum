"""
상수 정의
=========

v1.8.3 형식 호환
- 비용 상수 (슬리피지, 수수료)
- 타임프레임 매핑
- 방향 상수
- 등급 기준
"""

from typing import Dict

# =============================================================================
# 비용 상수 (SSOT: config/constants/trading.py)
# =============================================================================
from config.constants import SLIPPAGE, FEE, TOTAL_COST

# 레거시 별칭 (하위 호환성)
DEFAULT_SLIPPAGE = SLIPPAGE
DEFAULT_FEE = FEE
TOTAL_COST_ONE_WAY = TOTAL_COST
TOTAL_COST_ROUND_TRIP = TOTAL_COST * 2

INITIAL_CAPITAL = 10000        # 초기자본 $10,000


# =============================================================================
# 타임프레임 (SSOT: config/constants/timeframes.py)
# =============================================================================
from config.constants import TF_MAPPING, TF_RESAMPLE_MAP, TIMEFRAMES

AVAILABLE_TIMEFRAMES = ['15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
DEFAULT_TIMEFRAME = '1h'


# =============================================================================
# 방향 상수 (SSOT: config/constants/trading.py)
# =============================================================================
from config.constants import (
    DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
    to_api_direction, from_api_direction
)

AVAILABLE_DIRECTIONS = [DIRECTION_BOTH, DIRECTION_LONG, DIRECTION_SHORT]


# =============================================================================
# 전략 상수
# =============================================================================
AVAILABLE_STRATEGIES = ['macd', 'adxdi']
DEFAULT_STRATEGY = 'macd'

STRATEGY_DESCRIPTIONS = {
    'macd': 'MACD 히스토그램 W/M 패턴',
    'adxdi': '+DI/-DI 크로스오버 W/M 패턴',
}


# =============================================================================
# 등급 기준 (v1.8.3 호환)
# =============================================================================
GRADE_CRITERIA = {
    'S': {'win_rate': 85, 'pf': 3.0, 'mdd': 10},
    'A': {'win_rate': 75, 'pf': 2.0, 'mdd': 15},
    'B': {'win_rate': 65, 'pf': 1.5, 'mdd': 20},
    'C': {},  # 기본값
}


def calculate_grade(win_rate: float, profit_factor: float, max_drawdown: float) -> str:
    """
    성과 등급 계산 (utils.metrics wrapper - v1.8.3 호환)

    Args:
        win_rate: 승률 (%)
        profit_factor: 손익비
        max_drawdown: 최대 낙폭 (%)

    Returns:
        등급 ('S', 'A', 'B', 'C') - 이모지 없음

    Note:
        이 함수는 v1.8.3 호환성을 위해 유지됩니다.
        신규 코드는 utils.metrics.assign_grade_by_preset()를 직접 사용하세요.
    """
    from utils.metrics import assign_grade_by_preset

    # 균형형 기준으로 등급 계산
    grade_with_emoji = assign_grade_by_preset(
        preset_type='balanced',
        metrics={
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'mdd': max_drawdown
        }
    )

    # 이모지 제거하고 문자만 반환 ('S', 'A', 'B', 'C')
    return grade_with_emoji.replace('🏆', '').replace('🥇', '').replace('🥈', '').replace('🥉', '')


# =============================================================================
# 거래소 정보 (v1.8.3 호환)
# =============================================================================
EXCHANGE_INFO = {
    "bybit": {
        "type": "CEX",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
        "default_symbol": "BTCUSDT",
        "maker_fee": 0.0001,    # 0.01%
        "taker_fee": 0.00055,   # 0.055%
        "slippage": 0.0006,     # 0.06%
    },
    "binance": {
        "type": "CEX",
        "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
        "default_symbol": "BTCUSDT",
        "maker_fee": 0.0001,    # 0.01%
        "taker_fee": 0.0004,    # 0.04%
        "slippage": 0.0005,     # 0.05%
    },
}

AVAILABLE_EXCHANGES = list(EXCHANGE_INFO.keys())
DEFAULT_EXCHANGE = "bybit"
