"""
Parquet 파일명 정규화 테스트
Phase A-3: 대소문자 및 타임프레임 형식 통일
"""

from config.constants import (
    normalize_exchange,
    normalize_symbol,
    normalize_timeframe,
    get_parquet_filename
)


def test_normalize_exchange():
    """거래소 이름 정규화"""
    assert normalize_exchange('Bybit') == 'bybit'
    assert normalize_exchange('BINANCE') == 'binance'
    assert normalize_exchange('  OKX  ') == 'okx'
    assert normalize_exchange('upbit') == 'upbit'
    print("✅ Exchange normalization OK")


def test_normalize_symbol():
    """심볼 정규화"""
    assert normalize_symbol('BTC/USDT') == 'btcusdt'
    assert normalize_symbol('BTC-USDT') == 'btcusdt'
    assert normalize_symbol('BTC:USDT') == 'btcusdt'
    assert normalize_symbol('ETH_USDT') == 'ethusdt'
    assert normalize_symbol('  KRW-BTC  ') == 'krwbtc'
    print("✅ Symbol normalization OK")


def test_normalize_timeframe():
    """타임프레임 정규화 (핵심!)"""
    assert normalize_timeframe('15m') == '15m'
    assert normalize_timeframe('1H') == '1h'  # 대문자 → 소문자
    assert normalize_timeframe('4H') == '4h'  # 대문자 → 소문자
    assert normalize_timeframe('1D') == '1d'  # 대문자 → 소문자
    assert normalize_timeframe('  1W  ') == '1w'
    print("✅ Timeframe normalization OK (1H → 1h, 4H → 4h)")


def test_parquet_filename():
    """Parquet 파일명 생성"""
    # 기본 케이스
    assert get_parquet_filename('Bybit', 'BTC/USDT', '15m') == 'bybit_btcusdt_15m.parquet'

    # 대소문자 혼합
    assert get_parquet_filename('BINANCE', 'ETH-USDT', '1H') == 'binance_ethusdt_1h.parquet'

    # 타임프레임 대문자 → 소문자 변환 (핵심!)
    assert get_parquet_filename('okx', 'BTC:USDT', '4H') == 'okx_btcusdt_4h.parquet'

    # 공백 처리
    assert get_parquet_filename('  upbit  ', '  KRW-BTC  ', '  1D  ') == 'upbit_krwbtc_1d.parquet'

    print("✅ Parquet filename generation OK")


def test_edge_cases():
    """엣지 케이스"""
    # 모두 대문자
    assert get_parquet_filename('BYBIT', 'BTCUSDT', '15M') == 'bybit_btcusdt_15m.parquet'

    # 모두 소문자
    assert get_parquet_filename('binance', 'ethusdt', '1h') == 'binance_ethusdt_1h.parquet'

    # 특수문자 다중
    assert normalize_symbol('BTC/-_:USDT') == 'btcusdt'

    print("✅ Edge cases OK")


if __name__ == '__main__':
    print("=" * 80)
    print("Parquet Filename Normalization Tests (Phase A-3)")
    print("=" * 80)

    test_normalize_exchange()
    test_normalize_symbol()
    test_normalize_timeframe()
    test_parquet_filename()
    test_edge_cases()

    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)

    # 실제 예시 출력
    print("\n📁 Parquet 파일명 예시:")
    examples = [
        ('Bybit', 'BTC/USDT', '15m'),
        ('BINANCE', 'ETH-USDT', '1H'),  # 대문자 H
        ('OKX', 'BTC:USDT', '4H'),      # 대문자 H
        ('Upbit', 'KRW-BTC', '1D'),     # 대문자 D
        ('bithumb', 'BTC_KRW', '1W'),   # 대문자 W
    ]

    for ex, sym, tf in examples:
        filename = get_parquet_filename(ex, sym, tf)
        print(f"  {ex:10s} | {sym:15s} | {tf:5s} → {filename}")

    print("\n✅ 모든 파일명이 소문자로 통일되었습니다!")
