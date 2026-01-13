"""
등급/라이선스 관련 상수
"""

from typing import List, Dict, Any

# ============ 등급 목록 ============
GRADES = ['TRIAL', 'BASIC', 'STANDARD', 'PREMIUM', 'ADMIN', 'EXPIRED']

# ============ 등급별 제한 ============
GRADE_LIMITS: Dict[str, Dict[str, Any]] = {
    'TRIAL': {
        'exchanges': 1,
        'coins': ['BTC'],
        'positions': 1,
        'days': 7,
        'description': '7일 체험판'
    },
    'BASIC': {
        'exchanges': 2,
        'coins': ['BTC'],
        'positions': 1,
        'description': '기본 플랜'
    },
    'STANDARD': {
        'exchanges': 3,
        'coins': ['BTC', 'ETH'],
        'positions': 2,
        'description': '스탠다드 플랜'
    },
    'PREMIUM': {
        'exchanges': 6,
        'coins': ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK'],
        'positions': 10,
        'description': '프리미엄 플랜'
    },
    'ADMIN': {
        'exchanges': 999,
        'coins': [],  # 모든 코인 허용
        'positions': 9999,
        'description': '관리자'
    },
    'EXPIRED': {
        'exchanges': 1,
        'coins': ['BTC'],
        'positions': 1,
        'description': '만료됨'
    }
}

# ============ 등급별 색상 ============
GRADE_COLORS: Dict[str, str] = {
    'TRIAL': '#787b86',     # 회색
    'BASIC': '#2196f3',     # 파랑
    'STANDARD': '#ff9800',  # 주황
    'PREMIUM': '#00e676',   # 녹색
    'ADMIN': '#e91e63',     # 분홍
    'EXPIRED': '#ef5350'    # 빨강
}

# ============ 등급별 아이콘 ============
GRADE_ICONS: Dict[str, str] = {
    'TRIAL': '🆓',
    'BASIC': '🔵',
    'STANDARD': '🟠',
    'PREMIUM': '💎',
    'ADMIN': '👑',
    'EXPIRED': '⏰'
}


# ============ 헬퍼 함수 ============

def is_coin_allowed(tier: str, symbol: str) -> bool:
    """
    등급별 코인 허용 여부
    
    Args:
        tier: 등급 ('TRIAL', 'BASIC', 'STANDARD', 'PREMIUM', 'ADMIN')
        symbol: 심볼 (예: 'BTCUSDT', 'KRW-ETH')
    
    Returns:
        허용 여부
    """
    tier_upper = tier.upper()
    
    # ADMIN은 모든 코인 허용
    if tier_upper == 'ADMIN':
        return True
    
    limits = GRADE_LIMITS.get(tier_upper, GRADE_LIMITS['TRIAL'])
    allowed = limits.get('coins', ['BTC'])
    
    # 심볼에서 베이스 코인 추출
    clean = symbol.replace('USDT', '').replace('KRW-', '').replace('-USDT', '').upper()
    
    return clean in allowed


def get_tier_color(tier: str) -> str:
    """
    등급별 색상 반환
    
    Args:
        tier: 등급
    
    Returns:
        HEX 색상 코드
    """
    return GRADE_COLORS.get(tier.upper(), '#787b86')


def get_tier_icon(tier: str) -> str:
    """등급별 아이콘 반환"""
    return GRADE_ICONS.get(tier.upper(), '🆓')


def get_max_positions(tier: str) -> int:
    """
    등급별 최대 포지션 수 반환
    
    Args:
        tier: 등급
    
    Returns:
        최대 포지션 수
    """
    limits = GRADE_LIMITS.get(tier.upper(), GRADE_LIMITS['TRIAL'])
    return limits.get('positions', 1)


def get_max_exchanges(tier: str) -> int:
    """등급별 최대 거래소 수 반환"""
    limits = GRADE_LIMITS.get(tier.upper(), GRADE_LIMITS['TRIAL'])
    return limits.get('exchanges', 1)


def get_allowed_coins(tier: str) -> List[str]:
    """등급별 허용 코인 목록 반환"""
    tier_upper = tier.upper()
    
    if tier_upper == 'ADMIN':
        return []  # 빈 리스트 = 모든 코인 허용
    
    limits = GRADE_LIMITS.get(tier_upper, GRADE_LIMITS['TRIAL'])
    return limits.get('coins', ['BTC'])


def get_trial_days() -> int:
    """트라이얼 기간 (일) 반환"""
    return GRADE_LIMITS['TRIAL'].get('days', 7)


def is_premium_or_higher(tier: str) -> bool:
    """프리미엄 이상 등급 여부"""
    return tier.upper() in ('PREMIUM', 'ADMIN')


def is_valid_grade(tier: str) -> bool:
    """유효한 등급인지 확인"""
    return tier.upper() in GRADES
