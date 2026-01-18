"""
거래 관련 상수
"""

# ============ 방향 상수 ============
DIRECTION_LONG = 'Long'
DIRECTION_SHORT = 'Short'
DIRECTION_BOTH = 'Both'

DIRECTIONS = [DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH]

# ============ 비용 상수 ============
SLIPPAGE = 0.0006       # 슬리피지 (0.06%)
FEE = 0.00055           # 수수료 (0.055%)
TOTAL_COST = SLIPPAGE + FEE  # 총 비용 (0.115%)

# ============ 레버리지 상수 ============
DEFAULT_LEVERAGE = 10
MAX_LEVERAGE = 125
MIN_LEVERAGE = 1

# ============ 포지션 상수 ============
POSITION_SIDE_LONG = 'long'
POSITION_SIDE_SHORT = 'short'

# ============ 주문 타입 ============
ORDER_TYPE_MARKET = 'Market'
ORDER_TYPE_LIMIT = 'Limit'

# ============ 주문 상태 ============
ORDER_STATUS_PENDING = 'pending'
ORDER_STATUS_FILLED = 'filled'
ORDER_STATUS_CANCELLED = 'cancelled'
ORDER_STATUS_REJECTED = 'rejected'


# ============ 방향 변환 함수 ============

def to_api_direction(direction: str) -> str:
    """
    내부 방향 → API 방향 변환
    
    Args:
        direction: 내부 방향 ('Long', 'Short')
    
    Returns:
        API 방향 ('Buy', 'Sell')
    
    Examples:
        to_api_direction('Long') -> 'Buy'
        to_api_direction('Short') -> 'Sell'
    """
    return 'Buy' if direction == DIRECTION_LONG else 'Sell'


def from_api_direction(api_dir: str) -> str:
    """
    API 방향 → 내부 방향 변환
    
    Args:
        api_dir: API 방향 ('Buy', 'Sell', 'buy', 'sell', 'long', 'short')
    
    Returns:
        내부 방향 ('Long', 'Short')
    
    Examples:
        from_api_direction('Buy') -> 'Long'
        from_api_direction('sell') -> 'Short'
    """
    return DIRECTION_LONG if api_dir.lower() in ('buy', 'long') else DIRECTION_SHORT


def is_long(direction: str) -> bool:
    """롱 방향 여부"""
    return direction == DIRECTION_LONG or direction.lower() in ('buy', 'long')


def is_short(direction: str) -> bool:
    """숏 방향 여부"""
    return direction == DIRECTION_SHORT or direction.lower() in ('sell', 'short')


def opposite_direction(direction: str) -> str:
    """반대 방향 반환"""
    if is_long(direction):
        return DIRECTION_SHORT
    return DIRECTION_LONG


# ============ 비용 계산 함수 ============

def calculate_total_cost(price: float, size: float, fee_rate: float = FEE) -> float:
    """
    총 거래 비용 계산
    
    Args:
        price: 진입 가격
        size: 포지션 크기
        fee_rate: 수수료율 (기본값: FEE)
    
    Returns:
        총 비용
    """
    return price * size * (fee_rate + SLIPPAGE)


def calculate_breakeven_move(fee_rate: float = FEE) -> float:
    """
    손익분기점 가격 변동률 계산
    
    Returns:
        손익분기점 퍼센트 (예: 0.00115 = 0.115%)
    """
    return (fee_rate + SLIPPAGE) * 2  # 진입 + 청산


def calculate_pnl(entry_price: float, exit_price: float, size: float, 
                  direction: str, leverage: int = 1) -> float:
    """
    손익 계산 (수수료 포함)
    
    Args:
        entry_price: 진입 가격
        exit_price: 청산 가격
        size: 포지션 크기 (USDT)
        direction: 방향 ('Long', 'Short')
        leverage: 레버리지
    
    Returns:
        순손익 (USDT)
    """
    if is_long(direction):
        raw_pnl = (exit_price - entry_price) / entry_price * size * leverage
    else:
        raw_pnl = (entry_price - exit_price) / entry_price * size * leverage
    
    # 수수료 차감
    total_fee = size * TOTAL_COST * 2  # 진입 + 청산
    
    return raw_pnl - total_fee
