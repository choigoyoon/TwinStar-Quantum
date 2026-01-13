"""
상수 및 기본 설정
================

슬리피지, 수수료, 기본값 정의
"""

# =============================================================================
# 비용 상수 (Bybit 기준)
# =============================================================================
DEFAULT_SLIPPAGE = 0.0006   # 0.06% (편도)
DEFAULT_FEE = 0.00055       # 0.055% (편도, Taker)
INITIAL_CAPITAL = 10000

# 총 비용 계산
TOTAL_COST_ONE_WAY = DEFAULT_SLIPPAGE + DEFAULT_FEE  # 0.115%
TOTAL_COST_ROUND_TRIP = TOTAL_COST_ONE_WAY * 2       # 0.23%


# =============================================================================
# 기본값
# =============================================================================
DEFAULT_TIMEFRAME = '2h'
DEFAULT_METHOD = 'macd'
AVAILABLE_TIMEFRAMES = ['15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
AVAILABLE_METHODS = ['macd', 'adxdi']


# =============================================================================
# 등급 기준
# =============================================================================
GRADE_CRITERIA = {
    'S': {'win_rate': 85, 'mdd': 10, 'pf': 3.0},
    'A': {'win_rate': 75, 'mdd': 15, 'pf': 2.0},
    'B': {'win_rate': 65, 'mdd': 20, 'pf': 1.5},
    'C': {},
}


def calculate_grade(win_rate: float, profit_factor: float, max_drawdown: float) -> str:
    """결과 등급 계산"""
    mdd = abs(max_drawdown)
    
    if win_rate >= 85 and profit_factor >= 3.0 and mdd <= 10:
        return '🏆S'
    elif win_rate >= 75 and profit_factor >= 2.0 and mdd <= 15:
        return '🥇A'
    elif win_rate >= 65 and profit_factor >= 1.5 and mdd <= 20:
        return '🥈B'
    else:
        return '🥉C'
