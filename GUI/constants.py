# constants.py - 통합 상수 정의

# ============ 거래소 타입 ============
SPOT_EXCHANGES = {'upbit', 'bithumb'}
KRW_EXCHANGES = {'upbit', 'bithumb'}

# ============ 타임프레임 매핑 ============
# Trend TF → Entry TF 매핑 (전략 전용)
TF_MAPPING = {
    '1h': '15min',
    '4h': '1h', 
    '1d': '4h',
    '1w': '1d'
}

# 리샘플링 TF 매핑 (전체 프로젝트 공용 - Pandas 호환)
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

# ============ 방향 상수 (config/parameters.py에서 import) ============
try:
    from config.parameters import (
        SLIPPAGE, FEE, TOTAL_COST,
        DIRECTION_LONG, DIRECTION_SHORT, DIRECTION_BOTH,
        to_api_direction, from_api_direction # type: ignore
    )
except ImportError:
    # Fallback
    SLIPPAGE = 0.0006
    FEE = 0.00055
    TOTAL_COST = SLIPPAGE + FEE
    DIRECTION_LONG = 'Long'
    DIRECTION_SHORT = 'Short'
    DIRECTION_BOTH = 'Both'
    def to_api_direction(d): return 'Buy' if d == 'Long' else 'Sell'
    def from_api_direction(d): return 'Long' if d.lower() in ('buy', 'long') else 'Short'

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

# ============ 거래소 메타데이터 ============
EXCHANGE_INFO = {
    'bybit': {
        'icon': '🟨', 'type': 'CEX', 'market': 'Future/Spot', 'maker_fee': 0.02, 'taker_fee': 0.055, 'testnet': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT', 'LINKUSDT'],
        'api_url': 'https://www.bybit.com/app/user/api-management',
        'permissions': ['✅ Read (필수)', '✅ Derivatives - Trade (선물 거래)', '⛔ Withdrawal (출금 권한 비활성화!)'],
        'features': ['Unified Trading Account 사용 권장', 'IP 제한 설정 권장', 'API Key 생성 후 Secret은 한 번만 표시됨']
    },
    'binance': {
        'icon': '🟨', 'type': 'CEX', 'market': 'Future', 'maker_fee': 0.02, 'taker_fee': 0.04, 'testnet': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT', 'LINKUSDT'],
        'api_url': 'https://www.binance.com/en/my/settings/api-management',
        'permissions': ['✅ Enable Reading', '✅ Enable Futures (선물 거래)', '⛔ Enable Withdrawals 비활성화!'],
        'features': ['선물 계정 활성화 필요', 'IP 화이트리스트 권장', 'HMAC SHA256 서명 사용']
    },
    'okx': {
        'icon': '🔵', 'type': 'CEX', 'market': 'Future/Spot', 'maker_fee': 0.02, 'taker_fee': 0.05, 'passphrase': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'api_url': 'https://www.okx.com/account/my-api',
        'permissions': ['✅ Read (읽기)', '✅ Trade (거래)', '⛔ Withdraw 비활성화!'],
        'features': ['Passphrase 필수 입력', '별도 거래 비밀번호 설정 권장', 'V5 API 사용']
    },
    'bitget': {
        'icon': '🟢', 'type': 'CEX', 'market': 'Future/Spot', 'maker_fee': 0.02, 'taker_fee': 0.06, 'passphrase': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'api_url': 'https://www.bitget.com/api-mgmt',
        'permissions': ['✅ Read-Only', '✅ Futures Trade', '⛔ Withdraw 비활성화!'],
        'features': ['Passphrase 필수', 'Mix API (선물) 사용', 'IP 바인딩 권장']
    },
    'bingx': {
        'icon': '🟣', 'type': 'CEX', 'market': 'Future/Spot', 'maker_fee': 0.02, 'taker_fee': 0.05,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'api_url': 'https://bingx.com/en-us/account/api/',
        'permissions': ['✅ Read', '✅ Perpetual Futures', '⛔ Transfer/Withdraw 비활성화!'],
        'features': ['Standard Futures API 사용', '거래 → 무기한 계약 메뉴', 'IP 제한 선택적']
    },
    'lighter': {
        'icon': '⚡', 'type': 'DEX', 'market': 'Perp', 'maker_fee': 0.01, 'taker_fee': 0.01, 'network': 'Arbitrum',
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'api_url': 'https://app.lighter.xyz',
        'permissions': ['지갑 연결 (MetaMask/WalletConnect)', 'Arbitrum 네트워크 사용'],
        'features': ['가스비 최소화', '탈중앙화 거래소', 'Private Key 필요']
    },
    'upbit': {
        'icon': '🇰🇷', 'type': 'CEX', 'market': 'Spot', 'maker_fee': 0.05, 'taker_fee': 0.05, 'currency': 'KRW',
        'symbols': ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-DOGE', 'KRW-ADA', 'KRW-AVAX', 'KRW-DOT', 'KRW-MATIC', 'KRW-LINK'],
        'api_url': 'https://upbit.com/mypage/open_api_management',
        'permissions': ['✅ 자산조회', '✅ 주문조회', '✅ 주문하기', '⛔ 출금하기 비활성화!'],
        'features': ['카카오 인증 필요', 'IP 주소 등록 필수', '하루 요청 제한 있음']
    },
    'bithumb': {
        'icon': '🇰🇷', 'type': 'CEX', 'market': 'Spot', 'maker_fee': 0.04, 'taker_fee': 0.04, 'currency': 'KRW',
        'symbols': ['BTC', 'ETH', 'XRP', 'SOL', 'DOGE', 'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK'],
        'api_url': 'https://www.bithumb.com/react/info/mypage/api-management',
        'permissions': ['✅ 조회 (Info)', '✅ 거래 (Trade)', '⛔ 출금 비활성화!'],
        'features': ['보안 인증 필수', '연속키 + Secret 키', 'API 사용 약관 동의']
    }
}

# ============ 빗썸-업비트 공통 코인 (하이브리드용) ============
COMMON_KRW_SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'SOL', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK', 'MATIC',
    'STX', 'ETC', 'NEAR', 'SUI', 'APT', 'ALGO', 'SAND', 'MANA', 'CHZ', 'HBAR',
    'FIL', 'ARB', 'OP', 'EGLD', 'THETA', 'GRT', 'AAVE', 'VET', 'FLOW', 'ICP'
]

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

