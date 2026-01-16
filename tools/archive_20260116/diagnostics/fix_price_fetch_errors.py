#!/usr/bin/env python3
"""
Price Fetch 에러 처리 일괄 수정 스크립트

대상 거래소:
- OKX
- BingX
- Bitget
- Upbit
- Bithumb
- Lighter
"""

import re
from pathlib import Path

# 수정할 거래소 목록
EXCHANGES = [
    'okx_exchange.py',
    'bingx_exchange.py',
    'bitget_exchange.py',
    'upbit_exchange.py',
    'bithumb_exchange.py',
    'lighter_exchange.py'
]

# get_current_price() 수정 패턴
OLD_PATTERN = r'''    def get_current_price\(.*?\) -> float:
        """.*?"""
        .*?
        try:
            .*?
        except Exception as e:
            logging\.error\(f"Price fetch .*?: \{e\}"\)
            return 0\.0'''

NEW_CODE = '''    def get_current_price(self) -> float:
        """
        현재 가격 조회

        Raises:
            RuntimeError: API 호출 실패 또는 가격 조회 불가
        """
        # 구현은 거래소별로 다르므로 수동 수정 필요
        raise NotImplementedError("Manual fix required")'''


def fix_exchange_file(file_path: Path):
    """거래소 파일의 get_current_price() 수정"""
    print(f"Processing: {file_path.name}")

    try:
        content = file_path.read_text(encoding='utf-8')

        # 1. get_current_price() 찾기
        pattern = r'def get_current_price\(.*?\) -> float:'
        matches = list(re.finditer(pattern, content))

        if not matches:
            print(f"  ⚠️  get_current_price() not found")
            return

        print(f"  ✓ Found {len(matches)} get_current_price() methods")

        # 수동 수정 필요 메시지 출력
        print(f"  ⚠️  Manual fix required:")
        print(f"      1. Change return type behavior (0.0 → RuntimeError)")
        print(f"      2. Add price validation (price <= 0)")
        print(f"      3. Add try-except in callers (place_market_order, close_position)")

    except Exception as e:
        print(f"  ❌ Error: {e}")


def main():
    exchanges_dir = Path('exchanges')

    if not exchanges_dir.exists():
        print("❌ exchanges/ directory not found")
        return

    print("🔧 Price Fetch Error Handling Fix")
    print("=" * 60)

    for exchange_file in EXCHANGES:
        file_path = exchanges_dir / exchange_file

        if not file_path.exists():
            print(f"⚠️  {exchange_file} not found, skipping")
            continue

        fix_exchange_file(file_path)
        print()

    print("=" * 60)
    print("✅ Analysis complete!")
    print()
    print("📝 Manual Steps Required:")
    print("   1. Modify get_current_price() to raise RuntimeError")
    print("   2. Add price validation (price <= 0 check)")
    print("   3. Add try-except in place_market_order()")
    print("   4. Add try-except in close_position()")
    print()
    print("📋 Pattern (see bybit_exchange.py and binance_exchange.py for reference)")


if __name__ == '__main__':
    main()
