"""
프리셋 관련 상수
===============

프리셋 파일 네이밍 규칙 및 관리 상수
"""
from datetime import datetime
from typing import Optional


# ==================== 프리셋 네이밍 규칙 ====================

def generate_preset_filename(
    exchange: str,
    symbol: str,
    timeframe: str,
    mode: Optional[str] = None,
    strategy_type: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    use_timestamp: bool = True
) -> str:
    """
    표준 프리셋 파일명 생성

    Args:
        exchange: 거래소명 (bybit, binance 등)
        symbol: 심볼 (BTCUSDT, ETHUSDT 등)
        timeframe: 타임프레임 (1h, 4h, 1d 등)
        mode: 최적화 모드 (quick, standard, deep) - 선택
        strategy_type: 전략 유형 (macd, adx) - 선택
        timestamp: 생성 시각 (None이면 현재 시각)
        use_timestamp: 타임스탬프 포함 여부

    Returns:
        표준 파일명 (예: bybit_BTCUSDT_1h_macd_20260114_235959_quick.json)

    Examples:
        >>> generate_preset_filename('bybit', 'BTCUSDT', '1h', 'quick', 'macd')
        'bybit_BTCUSDT_1h_macd_20260114_235959_quick.json'

        >>> generate_preset_filename('bybit', 'BTCUSDT', '1h', use_timestamp=False)
        'bybit_BTCUSDT_1h.json'
    """
    # 기본 부분
    exchange_norm = exchange.lower()
    symbol_norm = symbol.upper().replace('/', '_')
    tf_norm = timeframe.lower()

    parts = [exchange_norm, symbol_norm, tf_norm]

    # 전략 유형 추가 (선택) - 타임스탬프 앞에 배치
    if strategy_type:
        parts.append(strategy_type.lower())

    # 타임스탬프 추가
    if use_timestamp:
        if timestamp is None:
            timestamp = datetime.now()
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        parts.extend([date_str, time_str])

    # 모드 추가 (선택)
    if mode:
        parts.append(mode.lower())

    return "_".join(parts) + ".json"


def parse_preset_filename(filename: str) -> dict[str, str | datetime | None]:
    """
    프리셋 파일명에서 정보 추출

    Args:
        filename: 프리셋 파일명

    Returns:
        추출된 정보 dict (exchange, symbol, timeframe, timestamp, mode)

    Examples:
        >>> parse_preset_filename('bybit_BTCUSDT_1h_20260114_235959_quick.json')
        {
            'exchange': 'bybit',
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'date': '20260114',
            'time': '235959',
            'mode': 'quick',
            'timestamp': datetime(2026, 1, 14, 23, 59, 59)
        }
    """
    # .json 제거
    name = filename.replace('.json', '')
    parts = name.split('_')

    result: dict[str, str | datetime | None] = {
        'exchange': None,
        'symbol': None,
        'timeframe': None,
        'date': None,
        'time': None,
        'mode': None,
        'timestamp': None
    }

    if len(parts) >= 3:
        result['exchange'] = parts[0]
        result['symbol'] = parts[1]
        result['timeframe'] = parts[2]

        # 타임스탬프가 있는 경우 (6개 이상)
        if len(parts) >= 5:
            result['date'] = parts[3]
            result['time'] = parts[4]

            # datetime 변환 시도
            try:
                dt_str = f"{parts[3]} {parts[4]}"
                result['timestamp'] = datetime.strptime(dt_str, "%Y%m%d %H%M%S")
            except ValueError:
                pass

        # 모드가 있는 경우
        if len(parts) >= 6:
            result['mode'] = parts[5]

    return result


# ==================== 최적화 모드 ====================

OPTIMIZATION_MODES = {
    'quick': {
        'name': 'Quick',
        'description': '빠른 탐색 (~50개 조합)',
        'combinations': 50,
        'estimated_time_min': 2,
    },
    'standard': {
        'name': 'Standard',
        'description': '표준 탐색 (~5,000개 조합)',
        'combinations': 5000,
        'estimated_time_min': 30,
    },
    'deep': {
        'name': 'Deep',
        'description': '정밀 탐색 (~50,000개 조합)',
        'combinations': 50000,
        'estimated_time_min': 300,
    }
}


# ==================== 프리셋 메타데이터 템플릿 ====================

def get_preset_template() -> dict:
    """
    표준 프리셋 메타데이터 템플릿

    Returns:
        프리셋 데이터 구조
    """
    return {
        '_meta': {
            'symbol': '',
            'exchange': '',
            'timeframe': '',
            'mode': '',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'version': '2.0',  # 새 네이밍 규칙 버전
        },
        '_result': {
            'trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'simple_return': 0.0,
            'compound_return': 0.0,
            'avg_trades_per_day': 0.0,
            'grade': '',
            'stability': '',
        },
        'params': {}
    }


__all__ = [
    'generate_preset_filename',
    'parse_preset_filename',
    'OPTIMIZATION_MODES',
    'get_preset_template',
]
