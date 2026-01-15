# constants.py - 통합 상수 정의

# ============ SSOT Imports ============
# 거래소 (SSOT: config/constants/exchanges.py)
from config.constants import (
    SPOT_EXCHANGES, KRW_EXCHANGES,
    EXCHANGE_INFO, COMMON_KRW_SYMBOLS
)

# 타임프레임 (SSOT: config/constants/timeframes.py)
from config.constants import TF_MAPPING, TF_RESAMPLE_MAP

# 방향 상수 (SSOT: config/constants/trading.py)
from config.constants import (
    SLIPPAGE, FEE, TOTAL_COST,
    DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
    to_api_direction, from_api_direction
)

# ============ 기본 파라미터 (전체 프로젝트 공용) ============
# [Phase 3] Single Source of Truth: config/parameters.py에서 import
try:
    from config.parameters import (
        load_params_from_json, DEFAULT_PARAMS, get_param
    )
except ImportError:
    # Fallback for EXE or path issues
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from config.parameters import (
        load_params_from_json
    )


from typing import Dict, Any

def get_params() -> Dict[str, Any]:
    """현재 활성 파라미터 반환 (JSON 우선, 없으면 기본값)"""
    return load_params_from_json()



# ============ 경로 상수 ============
try:
    from paths import Paths
    CACHE_DIR = Paths.CACHE
except ImportError:
    CACHE_DIR = 'data/cache'
PRESET_DIR = 'config/presets'

# ============ 등급별 제한 ============
# ============ 등급 정책 (UI용) ============

GRADE_LIMITS = {
    'TRIAL': {
        'exchanges': 1,
        'coins': ['BTC'],
        'positions': 1,
        'days': 7
    },
    'BASIC': {
        'exchanges': 2,
        'coins': ['BTC'],
        'positions': 1
    },
    'STANDARD': {
        'exchanges': 3,
        'coins': ['BTC', 'ETH'],
        'positions': 2
    },
    'PREMIUM': {
        'exchanges': 6,
        'coins': ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK'],
        'positions': 10
    },
    'EXPIRED': {
        'exchanges': 1,
        'coins': ['BTC'],
        'positions': 1
    }
}

GRADE_COLORS = {
    'TRIAL': '#787b86',
    'BASIC': '#2196f3',
    'STANDARD': '#ff9800',
    'PREMIUM': '#00e676',
    'EXPIRED': '#ef5350'
}


def is_coin_allowed(tier: str, symbol: str) -> bool:
    """등급별 코인 허용 여부"""
    limits = GRADE_LIMITS.get(tier.upper(), GRADE_LIMITS['TRIAL'])
    allowed = limits.get('coins', ['BTC'])
    clean = symbol.replace('USDT', '').replace('KRW-', '').replace('-USDT', '').upper()
    return clean in allowed


def get_tier_color(tier: str) -> str:
    """등급별 색상"""
    return GRADE_COLORS.get(tier.upper(), '#787b86')

