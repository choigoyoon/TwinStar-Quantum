"""
거래소 관련 상수 및 메타데이터
"""

from typing import List, Dict, Any

# ============ 거래소 타입 ============
SPOT_EXCHANGES = {'upbit', 'bithumb'}
KRW_EXCHANGES = {'upbit', 'bithumb'}
FUTURES_EXCHANGES = {'bybit', 'binance', 'okx', 'bitget', 'bingx'}

# ============ 거래소 심볼 형식 ============
EXCHANGE_PAIR_FORMAT = {
    "bybit": "{symbol}USDT",
    "binance": "{symbol}USDT",
    "okx": "{symbol}USDT",
    "bitget": "{symbol}USDT",
    "bingx": "{symbol}USDT",
    "upbit": "KRW-{symbol}",
    "bithumb": "{symbol}_KRW",
    "lighter": "{symbol}USDT"
}

EXCHANGE_QUOTE = {
    "bybit": "USDT",
    "binance": "USDT",
    "okx": "USDT",
    "bitget": "USDT",
    "bingx": "USDT",
    "upbit": "KRW",
    "bithumb": "KRW",
    "lighter": "USDT"
}

# ============ 거래소 메타데이터 ============
EXCHANGE_INFO: Dict[str, Dict[str, Any]] = {
    'bybit': {
        'icon': '🟨',
        'type': 'CEX',
        'market': 'Future/Spot',
        'maker_fee': 0.02,
        'taker_fee': 0.055,
        'testnet': True,
        'symbols': [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
            'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT', 'LINKUSDT'
        ],
        'api_url': 'https://www.bybit.com/app/user/api-management',
        'permissions': [
            '✅ Read (필수)',
            '✅ Derivatives - Trade (선물 거래)',
            '⛔ Withdrawal (출금 권한 비활성화!)'
        ],
        'features': [
            'Unified Trading Account 사용 권장',
            'IP 제한 설정 권장',
            'API Key 생성 후 Secret은 한 번만 표시됨'
        ]
    },
    'binance': {
        'icon': '🟨',
        'type': 'CEX',
        'market': 'Future',
        'maker_fee': 0.02,
        'taker_fee': 0.04,
        'testnet': True,
        'symbols': [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
            'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT', 'LINKUSDT'
        ],
        'api_url': 'https://www.binance.com/en/my/settings/api-management',
        'permissions': [
            '✅ Enable Reading',
            '✅ Enable Futures (선물 거래)',
            '⛔ Enable Withdrawals 비활성화!'
        ],
        'features': [
            '선물 계정 활성화 필요',
            'IP 화이트리스트 권장',
            'HMAC SHA256 서명 사용'
        ]
    },
    'okx': {
        'icon': '🔵',
        'type': 'CEX',
        'market': 'Future/Spot',
        'maker_fee': 0.02,
        'taker_fee': 0.05,
        'passphrase': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'api_url': 'https://www.okx.com/account/my-api',
        'permissions': [
            '✅ Read (읽기)',
            '✅ Trade (거래)',
            '⛔ Withdraw 비활성화!'
        ],
        'features': [
            'Passphrase 필수 입력',
            '별도 거래 비밀번호 설정 권장',
            'V5 API 사용'
        ]
    },
    'bitget': {
        'icon': '🟢',
        'type': 'CEX',
        'market': 'Future/Spot',
        'maker_fee': 0.02,
        'taker_fee': 0.06,
        'passphrase': True,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'api_url': 'https://www.bitget.com/api-mgmt',
        'permissions': [
            '✅ Read-Only',
            '✅ Futures Trade',
            '⛔ Withdraw 비활성화!'
        ],
        'features': [
            'Passphrase 필수',
            'Mix API (선물) 사용',
            'IP 바인딩 권장'
        ]
    },
    'bingx': {
        'icon': '🟣',
        'type': 'CEX',
        'market': 'Future/Spot',
        'maker_fee': 0.02,
        'taker_fee': 0.05,
        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'],
        'api_url': 'https://bingx.com/en-us/account/api/',
        'permissions': [
            '✅ Read',
            '✅ Perpetual Futures',
            '⛔ Transfer/Withdraw 비활성화!'
        ],
        'features': [
            'Standard Futures API 사용',
            '거래 → 무기한 계약 메뉴',
            'IP 제한 선택적'
        ]
    },
    'lighter': {
        'icon': '⚡',
        'type': 'DEX',
        'market': 'Perp',
        'maker_fee': 0.01,
        'taker_fee': 0.01,
        'network': 'Arbitrum',
        'symbols': ['BTCUSDT', 'ETHUSDT'],
        'api_url': 'https://app.lighter.xyz',
        'permissions': ['지갑 연결 (MetaMask/WalletConnect)', 'Arbitrum 네트워크 사용'],
        'features': ['가스비 최소화', '탈중앙화 거래소', 'Private Key 필요']
    },
    'upbit': {
        'icon': '🇰🇷',
        'type': 'CEX',
        'market': 'Spot',
        'maker_fee': 0.05,
        'taker_fee': 0.05,
        'currency': 'KRW',
        'symbols': [
            'KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL', 'KRW-DOGE',
            'KRW-ADA', 'KRW-AVAX', 'KRW-DOT', 'KRW-MATIC', 'KRW-LINK'
        ],
        'api_url': 'https://upbit.com/mypage/open_api_management',
        'permissions': [
            '✅ 자산조회',
            '✅ 주문조회',
            '✅ 주문하기',
            '⛔ 출금하기 비활성화!'
        ],
        'features': ['카카오 인증 필요', 'IP 주소 등록 필수', '하루 요청 제한 있음']
    },
    'bithumb': {
        'icon': '🇰🇷',
        'type': 'CEX',
        'market': 'Spot',
        'maker_fee': 0.04,
        'taker_fee': 0.04,
        'currency': 'KRW',
        'symbols': [
            'BTC', 'ETH', 'XRP', 'SOL', 'DOGE',
            'ADA', 'AVAX', 'DOT', 'MATIC', 'LINK'
        ],
        'api_url': 'https://www.bithumb.com/react/info/mypage/api-management',
        'permissions': [
            '✅ 조회 (Info)',
            '✅ 거래 (Trade)',
            '⛔ 출금 비활성화!'
        ],
        'features': ['보안 인증 필수', '연속키 + Secret 키', 'API 사용 약관 동의']
    }
}

# ============ 공통 심볼 ============
COMMON_KRW_SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'SOL', 'ADA', 'DOGE', 'AVAX', 'DOT', 'LINK', 'MATIC',
    'STX', 'ETC', 'NEAR', 'SUI', 'APT', 'ALGO', 'SAND', 'MANA', 'CHZ', 'HBAR',
    'FIL', 'ARB', 'OP', 'EGLD', 'THETA', 'GRT', 'AAVE', 'VET', 'FLOW', 'ICP'
]


# ============ 헬퍼 함수 ============

def get_exchange_symbols(exchange: str) -> List[str]:
    """거래소별 지원 심볼 반환"""
    info = EXCHANGE_INFO.get(exchange.lower(), {})
    return info.get('symbols', [])


def get_exchange_fees(exchange: str) -> Dict[str, float]:
    """거래소별 수수료 반환"""
    info = EXCHANGE_INFO.get(exchange.lower(), {})
    return {
        'maker': info.get('maker_fee', 0.02),
        'taker': info.get('taker_fee', 0.05)
    }


def is_spot_exchange(exchange: str) -> bool:
    """현물 거래소 여부"""
    return exchange.lower() in SPOT_EXCHANGES


def is_krw_exchange(exchange: str) -> bool:
    """원화 거래소 여부"""
    return exchange.lower() in KRW_EXCHANGES


def get_quote_currency(exchange: str) -> str:
    """거래소별 Quote 통화 반환"""
    return EXCHANGE_QUOTE.get(exchange.lower(), "USDT")


def requires_passphrase(exchange: str) -> bool:
    """패스프레이즈 필요 여부"""
    info = EXCHANGE_INFO.get(exchange.lower(), {})
    return info.get('passphrase', False)


def get_all_exchanges() -> List[str]:
    """모든 지원 거래소 목록"""
    return list(EXCHANGE_INFO.keys())


def get_futures_exchanges() -> List[str]:
    """선물 거래소 목록"""
    return list(FUTURES_EXCHANGES)
