"""
거래소 API 연결 테스트 (v7.29)

실전 매매 전 필수 검증:
1. API 키 유효성
2. 계정 잔고 확인
3. 현재 포지션 조회
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from storage.secure_storage import SecureKeyStorage
import ccxt


def test_exchange_connection(exchange_name: str = 'bybit') -> bool:
    """거래소 API 연결 테스트

    Args:
        exchange_name: 거래소 이름 (bybit, binance 등)

    Returns:
        True: 테스트 통과
        False: 테스트 실패
    """
    print("=" * 80)
    print(f"Exchange Connection Test ({exchange_name.upper()})")
    print("=" * 80)

    try:
        # 1. API 키 로드
        print("\n[1/4] Loading API keys...")
        storage = SecureKeyStorage()
        all_keys = storage.load_api_keys()

        if not all_keys or exchange_name not in all_keys:
            print(f"[FAIL] No API keys found for {exchange_name}.")
            print(f"       Run: python tools/setup_api_keys.py")
            return False

        keys = all_keys[exchange_name]
        print(f"[OK] API keys loaded")
        print(f"     API Key: {keys['api_key'][:8]}***")
        print(f"     Testnet: {'Yes' if keys.get('testnet') else 'No'}")

        # 2. 거래소 연결
        print(f"\n[2/4] Connecting to {exchange_name}...")

        # CCXT 거래소 객체 생성
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'apiKey': keys['api_key'],
            'secret': keys['secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # 선물 거래
            }
        })

        if keys.get('testnet'):
            exchange.set_sandbox_mode(True)
            print(f"[OK] Connected (Testnet mode)")
        else:
            print(f"[OK] Connected (Mainnet mode)")

        # 3. 잔고 확인
        print(f"\n[3/4] Fetching account balance...")
        balance = exchange.fetch_balance()

        if 'USDT' in balance['total']:
            usdt_balance = balance['total']['USDT']
            print(f"[OK] Account balance: {usdt_balance:,.2f} USDT")

            if usdt_balance < 100:
                print(f"[WARN] Balance is below 100 USDT (recommended minimum)")
        else:
            print(f"[WARN] No USDT balance found")
            usdt_balance = 0

        # 4. 포지션 확인
        print(f"\n[4/4] Checking open positions...")

        try:
            positions = exchange.fetch_positions()
            open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]

            if not open_positions:
                print(f"[OK] No open positions")
            else:
                print(f"[WARN] {len(open_positions)} open position(s) found:")
                for pos in open_positions:
                    symbol = pos.get('symbol', 'Unknown')
                    side = pos.get('side', 'Unknown')
                    size = pos.get('contracts', 0)
                    entry = pos.get('entryPrice', 0)
                    pnl = pos.get('unrealizedPnl', 0)

                    print(f"       - {symbol}: {side} {size} @ {entry:,.2f} (PnL: {pnl:,.2f} USDT)")
                print(f"\n       Recommend closing positions before auto-trading.")

        except Exception as e:
            print(f"[WARN] Could not fetch positions: {e}")

        # 최종 결과
        print("\n" + "=" * 80)
        print("[OK] Connection test completed")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"   Exchange: {exchange_name}")
        print(f"   Balance: {usdt_balance:,.2f} USDT")
        print(f"   Open Positions: {len(open_positions) if 'open_positions' in locals() else '?'}")

        # 권장 사항
        print(f"\nRecommendations:")
        ready = True

        if usdt_balance < 100:
            print(f"   [WARN] Deposit more USDT (minimum 100 USDT recommended)")
            ready = False

        if 'open_positions' in locals() and open_positions:
            print(f"   [WARN] Close open positions before starting auto-trading")
            ready = False

        if ready:
            print(f"   [OK] Ready to start auto-trading!")

        return True

    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test exchange API connection')
    parser.add_argument('--exchange', type=str, default='bybit',
                        help='Exchange name (bybit, binance, etc.)')

    args = parser.parse_args()

    success = test_exchange_connection(args.exchange)

    sys.exit(0 if success else 1)
