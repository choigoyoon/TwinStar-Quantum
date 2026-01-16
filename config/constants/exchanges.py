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


# ============ 상장일 정보 ============

UPBIT_LISTING_DATES = {
    # 주요 코인 (2017-2018)
    'BTC': '2017-10-01',
    'ETH': '2017-10-01',
    'XRP': '2017-10-24',
    'LTC': '2017-11-06',
    'BCH': '2017-11-09',
    'DASH': '2017-12-05',
    'ETC': '2018-03-21',

    # 2019-2020
    'TRX': '2019-01-25',
    'EOS': '2019-04-16',
    'VET': '2019-05-23',
    'LINK': '2020-07-30',
    'ADA': '2021-02-03',
    'DOGE': '2021-02-05',
    'DOT': '2021-01-28',
    'UNI': '2020-10-22',

    # 2021 (DeFi/Layer1 붐)
    'MATIC': '2021-03-29',
    'THETA': '2021-03-19',
    'FIL': '2021-03-18',
    'AAVE': '2021-05-13',
    'SOL': '2021-08-17',
    'AVAX': '2021-08-19',
    'ALGO': '2021-09-09',

    # 2021-2022 (메타버스/Layer2)
    'SAND': '2021-11-11',
    'MANA': '2021-11-11',
    'CHZ': '2021-11-18',
    'GRT': '2021-12-09',
    'NEAR': '2022-01-13',
    'ARB': '2023-03-23',
    'OP': '2022-08-11',

    # 2023-2024 (최신)
    'SUI': '2023-05-11',
    'APT': '2022-10-19',
    'STX': '2024-01-25',
    'HBAR': '2024-03-14',
    'EGLD': '2024-05-09',
    'ICP': '2024-08-01',
    'FLOW': '2024-09-12',
}


BITHUMB_LISTING_DATES = {
    # 빗썸 주요 코인 상장일
    # 업비트와 유사한 시기에 상장되었으나, 일부 차이 있음
    'BTC': '2014-01-01',  # 빗썸은 2014년부터 운영
    'ETH': '2016-07-21',
    'XRP': '2017-05-12',
    'LTC': '2017-09-25',
    'BCH': '2017-08-03',
    'DASH': '2017-11-15',
    'ETC': '2017-07-24',

    # 2018-2020
    'TRX': '2018-05-31',
    'EOS': '2018-06-14',
    'VET': '2019-08-13',
    'LINK': '2020-09-24',
    'ADA': '2021-03-02',
    'DOGE': '2021-05-10',
    'DOT': '2021-02-22',
    'UNI': '2021-09-15',

    # 2021-2022
    'MATIC': '2021-05-27',
    'THETA': '2021-04-23',
    'FIL': '2021-03-31',
    'AAVE': '2021-09-30',
    'SOL': '2021-10-07',
    'AVAX': '2021-09-30',
    'ALGO': '2021-11-04',

    # 최신 (메타버스/Layer2)
    'SAND': '2021-11-24',
    'MANA': '2021-11-26',
    'CHZ': '2021-12-16',
    'GRT': '2022-02-17',
    'NEAR': '2022-04-21',
    'ARB': '2023-06-08',
    'OP': '2023-01-19',

    # 2023-2024
    'SUI': '2023-08-10',
    'APT': '2022-12-20',
    'STX': '2024-02-15',
    'HBAR': '2024-04-25',
    'EGLD': '2024-06-13',
    'ICP': '2024-09-05',
    'FLOW': '2024-10-18',
}


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


def get_listing_date(exchange: str, symbol: str) -> str | None:
    """거래소별 코인 상장일 반환

    Args:
        exchange: 거래소 이름 ('upbit', 'bithumb')
        symbol: 코인 심볼 ('BTC', 'ETH' 등)

    Returns:
        상장일 문자열 (YYYY-MM-DD) 또는 None

    Examples:
        >>> get_listing_date('upbit', 'BTC')
        '2017-10-01'
        >>> get_listing_date('bithumb', 'ETH')
        '2016-07-21'
    """
    if exchange.lower() == 'upbit':
        return UPBIT_LISTING_DATES.get(symbol.upper())
    elif exchange.lower() == 'bithumb':
        return BITHUMB_LISTING_DATES.get(symbol.upper())
    return None


def get_all_listing_dates(exchange: str) -> Dict[str, str]:
    """거래소의 모든 상장일 정보 반환

    Args:
        exchange: 거래소 이름 ('upbit', 'bithumb')

    Returns:
        {심볼: 상장일} 딕셔너리

    Examples:
        >>> dates = get_all_listing_dates('upbit')
        >>> dates['BTC']
        '2017-10-01'
    """
    if exchange.lower() == 'upbit':
        return UPBIT_LISTING_DATES.copy()
    elif exchange.lower() == 'bithumb':
        return BITHUMB_LISTING_DATES.copy()
    return {}
