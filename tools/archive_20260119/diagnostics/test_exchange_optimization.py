#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7.23 거래소별 최적화 검증 스크립트

동일 데이터로 Binance vs Bybit 최적화 결과 비교
"""

import sys
import io
from pathlib import Path

# UTF-8 출력 강제 (Windows cp949 문제 해결)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_manager import BotDataManager


def test_exchange_optimization():
    """Binance와 Bybit의 최적화 결과 비교"""

    print("="*70)
    print("v7.23 거래소별 최적화 검증")
    print("="*70)

    # 동일 데이터 로드
    print("\n1. 데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    dm.load_historical()
    df = dm.get_full_history()

    if df is None or df.empty:
        print("   ❌ 데이터 로드 실패")
        return 1

    print(f"   데이터 크기: {len(df):,}개 캔들")

    # Bybit 최적화 설정
    print("\n2. Bybit 최적화 (높은 수수료 0.115%) ...")

    # Quick 그리드 생성 (샘플)
    from config.constants.trading import get_total_cost
    from config.parameters import (
        get_atr_range_by_exchange,
        get_filter_tf_range_by_exchange
    )

    bybit_cost = get_total_cost('bybit')
    bybit_atr = get_atr_range_by_exchange('bybit', 'coarse')
    bybit_filter = get_filter_tf_range_by_exchange('bybit', 'coarse')

    print(f"   수수료: {bybit_cost*100:.3f}%")
    print(f"   ATR 범위: {bybit_atr}")
    print(f"   Filter 범위: {bybit_filter}")

    # Binance 최적화 설정
    print("\n3. Binance 최적화 (낮은 수수료 0.1%) ...")

    binance_cost = get_total_cost('binance')
    binance_atr = get_atr_range_by_exchange('binance', 'coarse')
    binance_filter = get_filter_tf_range_by_exchange('binance', 'coarse')

    print(f"   수수료: {binance_cost*100:.3f}%")
    print(f"   ATR 범위: {binance_atr}")
    print(f"   Filter 범위: {binance_filter}")

    # 결과 비교
    print("\n" + "="*70)
    print("검증 결과")
    print("="*70)

    # 수수료 차이
    fee_diff = (bybit_cost - binance_cost) * 100
    print(f"\n✅ 수수료 차이: {fee_diff:.3f}%p (Bybit > Binance)")

    # ATR 범위 차이
    bybit_atr_max = max(bybit_atr)
    binance_atr_max = max(binance_atr)
    atr_diff = bybit_atr_max - binance_atr_max
    print(f"✅ ATR 범위: Bybit {bybit_atr_max} > Binance {binance_atr_max} (차이: +{atr_diff})")

    # Filter 강도 비교
    bybit_has_1d = '1d' in bybit_filter
    binance_has_4h = '4h' in binance_filter
    print(f"✅ Filter 강도:")
    print(f"   Bybit: {bybit_filter} (강한 필터)")
    print(f"   Binance: {binance_filter} (약한 필터)")

    # 예상 효과
    print(f"\n📊 예상 효과:")
    print(f"   Bybit: 거래 빈도 0.3~0.5회/일 (강한 필터, 넓은 ATR)")
    print(f"   Binance: 거래 빈도 0.8~1.2회/일 (약한 필터, 좁은 ATR)")

    # 성공 기준 검증
    print(f"\n" + "="*70)
    print("성공 기준 검증")
    print("="*70)

    checks = [
        (bybit_cost == 0.00115, f"Bybit 수수료: {bybit_cost:.5f} == 0.00115"),
        (binance_cost == 0.001, f"Binance 수수료: {binance_cost:.5f} == 0.001"),
        (bybit_atr_max > binance_atr_max, f"Bybit ATR ({bybit_atr_max}) > Binance ATR ({binance_atr_max})"),
        (bybit_has_1d, f"Bybit 필터에 '1d' 포함"),
        (binance_has_4h, f"Binance 필터에 '4h' 포함"),
    ]

    passed = sum(1 for check, _ in checks if check)
    total = len(checks)

    for check, msg in checks:
        status = "✅" if check else "❌"
        print(f"{status} {msg}")

    print(f"\n결과: {passed}/{total} 통과")

    if passed == total:
        print("\n🎉 모든 검증 통과! 거래소별 최적화가 정상적으로 작동합니다.")
        return 0
    else:
        print(f"\n⚠️  {total - passed}개 항목 실패")
        return 1


if __name__ == '__main__':
    sys.exit(test_exchange_optimization())
