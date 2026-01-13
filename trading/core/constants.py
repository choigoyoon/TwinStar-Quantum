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
# 비용 상수 (Bybit 기준, v1.8.3 동일)
# =============================================================================
DEFAULT_SLIPPAGE = 0.0006      # 0.06% 편도
DEFAULT_FEE = 0.00055          # 0.055% 편도 (Taker)
INITIAL_CAPITAL = 10000        # 초기자본 $10,000

# 합산 비용
TOTAL_COST_ONE_WAY = DEFAULT_SLIPPAGE + DEFAULT_FEE  # 0.115%
TOTAL_COST_ROUND_TRIP = TOTAL_COST_ONE_WAY * 2       # 0.23%

# v1.8.3 호환 별칭
SLIPPAGE = DEFAULT_SLIPPAGE
FEE = DEFAULT_FEE
TOTAL_COST = TOTAL_COST_ONE_WAY


# =============================================================================
# 타임프레임 (v1.8.3 호환)
# =============================================================================
AVAILABLE_TIMEFRAMES = ['15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
DEFAULT_TIMEFRAME = '1h'

# 전략 TF → Entry TF 매핑 (v1.8.3 호환)
TF_MAPPING = {
    '1h': '15min',
    '4h': '1h',
    '1d': '4h',
    '1w': '1d'
}

# 리샘플링 TF 매핑 (Pandas 호환, v1.8.3 동일)
TF_RESAMPLE_MAP = {
    '15min': '15min', '15m': '15min',
    '30min': '30min', '30m': '30min',
    '45min': '45min', '45m': '45min',
    '1h': '1h', '1H': '1h',
    '2h': '2h', '2H': '2h',
    '3h': '3h', '3H': '3h',
    '4h': '4h', '4H': '4h',
    '6h': '6h', '6H': '6h',
    '12h': '12h', '12H': '12h',
    '1d': '1D', '1D': '1D',
    '1w': 'W-MON', '1W': 'W-MON'
}


# =============================================================================
# 방향 상수 (v1.8.3 호환)
# =============================================================================
DIRECTION_LONG = 'Long'
DIRECTION_SHORT = 'Short'
DIRECTION_BOTH = 'Both'

AVAILABLE_DIRECTIONS = [DIRECTION_BOTH, DIRECTION_LONG, DIRECTION_SHORT]


def to_api_direction(direction: str) -> str:
    """내부 방향 → API 방향 변환 (Long → Buy, Short → Sell)"""
    return 'Buy' if direction == DIRECTION_LONG else 'Sell'


def from_api_direction(api_dir: str) -> str:
    """API 방향 → 내부 방향 변환 (Buy → Long, Sell → Short)"""
    return DIRECTION_LONG if api_dir.lower() in ('buy', 'long') else DIRECTION_SHORT


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
    성과 등급 계산 (v1.8.3 동일)
    
    Args:
        win_rate: 승률 (%)
        profit_factor: 손익비
        max_drawdown: 최대 낙폭 (%)
    
    Returns:
        등급 ('S', 'A', 'B', 'C')
    """
    mdd = abs(max_drawdown)
    
    if win_rate >= 85 and profit_factor >= 3.0 and mdd <= 10:
        return 'S'
    elif win_rate >= 75 and profit_factor >= 2.0 and mdd <= 15:
        return 'A'
    elif win_rate >= 65 and profit_factor >= 1.5 and mdd <= 20:
        return 'B'
    else:
        return 'C'


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
