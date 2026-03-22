"""
Exchange Symbol Manager 단위 테스트

테스트 항목:
1. CCXT 심볼 로드 (Bybit)
2. 캐시 메커니즘
3. 필터링 (USDT, swap, active)
4. 캐시 유효성 체크
5. 캐시 삭제
"""

import pytest
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from utils.exchange_symbol_manager import ExchangeSymbolManager


@pytest.fixture
def temp_cache_path(tmp_path):
    """임시 캐시 파일 경로"""
    return str(tmp_path / "test_exchange_symbols.json")


@pytest.fixture
def manager(temp_cache_path):
    """ExchangeSymbolManager 인스턴스"""
    return ExchangeSymbolManager(cache_path=temp_cache_path)


def test_load_bybit_symbols(manager):
    """Bybit 심볼 로드 테스트"""
    # 알파벳순 정렬이므로 BTC는 115번째 (숫자 심볼 뒤)
    # 전체 로드하여 BTC 포함 확인
    symbols = manager.load_all_symbols('bybit', filter_quote='USDT', top_n=500)

    assert len(symbols) > 100, "심볼이 100개 이상 로드되어야 함"
    assert len(symbols) <= 500, "top_n=500이므로 최대 500개"
    assert 'BTCUSDT' in symbols, "BTC/USDT는 반드시 포함되어야 함"
    assert all('USDT' in s for s in symbols), "모두 USDT 페어여야 함"


def test_cache_mechanism(manager):
    """캐시 메커니즘 테스트"""
    # 1차 로드 (API 호출)
    start = time.time()
    symbols1 = manager.load_all_symbols('bybit', filter_quote='USDT', top_n=50)
    time1 = time.time() - start

    # 2차 로드 (캐시)
    start = time.time()
    symbols2 = manager.load_all_symbols('bybit', filter_quote='USDT', top_n=50)
    time2 = time.time() - start

    assert symbols1 == symbols2, "캐시된 심볼과 원본이 동일해야 함"
    assert time2 < 0.1, "캐시는 100ms 이하여야 함"
    assert time1 > 1.0, "API 호출은 1초 이상 소요되어야 함"


def test_cache_expiry(manager, temp_cache_path):
    """캐시 만료 테스트"""
    # 1. 심볼 로드 (캐시 생성)
    manager.load_all_symbols('bybit', filter_quote='USDT', top_n=10)

    # 2. 캐시 파일 수동 수정 (25시간 전)
    with open(temp_cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    old_timestamp = (datetime.now() - timedelta(hours=25)).isoformat()
    cache['bybit_USDT_swap']['timestamp'] = old_timestamp

    with open(temp_cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f)

    # 3. 재로드 시 캐시 무시되어야 함
    manager_new = ExchangeSymbolManager(cache_path=temp_cache_path)
    symbols = manager_new.load_all_symbols('bybit', filter_quote='USDT', top_n=10)

    # 캐시가 만료되어 API 재호출됨
    assert len(symbols) > 0


def test_get_cached_symbols(manager):
    """캐시된 심볼 가져오기 테스트"""
    # 1. 캐시 없음
    cached = manager.get_cached_symbols('bybit', 'USDT', 'swap')
    assert cached == [], "캐시가 없으면 빈 리스트"

    # 2. 심볼 로드 (캐시 생성)
    manager.load_all_symbols('bybit', filter_quote='USDT', top_n=10)

    # 3. 캐시에서 가져오기
    cached = manager.get_cached_symbols('bybit', 'USDT', 'swap')
    assert len(cached) > 0, "캐시된 심볼이 있어야 함"


def test_clear_cache(manager):
    """캐시 삭제 테스트"""
    # 1. 심볼 로드 (캐시 생성)
    manager.load_all_symbols('bybit', filter_quote='USDT', top_n=10)

    # 2. 전체 캐시 삭제
    manager.clear_cache()

    # 3. 캐시 없음 확인
    cached = manager.get_cached_symbols('bybit', 'USDT', 'swap')
    assert cached == [], "캐시가 삭제되어 빈 리스트"


def test_force_refresh(manager):
    """강제 새로고침 테스트"""
    # 1. 심볼 로드 (캐시 생성)
    symbols1 = manager.load_all_symbols('bybit', filter_quote='USDT', top_n=10)

    # 2. 강제 새로고침 (캐시 무시)
    symbols2 = manager.load_all_symbols('bybit', filter_quote='USDT', top_n=10, force_refresh=True)

    # 동일한 심볼이지만 API 재호출됨
    assert symbols1 == symbols2


def test_invalid_exchange(manager):
    """잘못된 거래소 이름 테스트"""
    with pytest.raises(ValueError, match="지원하지 않는 거래소"):
        manager.load_all_symbols('invalid_exchange', filter_quote='USDT')


if __name__ == '__main__':
    # 수동 실행
    pytest.main([__file__, '-v'])
