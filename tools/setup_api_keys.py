"""
API 키 설정 도구 (v7.29)

거래소 API 키를 안전하게 암호화하여 저장합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from storage.secure_storage import SecureKeyStorage


def setup_api_keys():
    """API 키 대화형 설정"""

    print("=" * 80)
    print("API Key Setup Tool (v7.29)")
    print("=" * 80)
    print("\n거래소 API 키를 안전하게 암호화하여 저장합니다.")
    print("암호화 방식: 하드웨어 기반 키 (MAC 주소 + 시스템 정보)\n")

    # 저장소 초기화
    storage = SecureKeyStorage()

    # 거래소 선택
    exchanges = ['bybit', 'binance', 'okx', 'bingx', 'bitget']

    print("지원 거래소:")
    for i, ex in enumerate(exchanges, 1):
        print(f"  {i}. {ex.capitalize()}")

    while True:
        choice = input("\n거래소 번호를 선택하세요 (1-5, 0=종료): ").strip()

        if choice == '0':
            print("\n설정을 종료합니다.")
            break

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(exchanges):
                print("[ERROR] 잘못된 번호입니다. 1-5 사이의 숫자를 입력하세요.")
                continue

            exchange = exchanges[idx]
            print(f"\n[{exchange.upper()}] API 키 설정")
            print("-" * 40)

            # API 키 입력
            api_key = input("API Key: ").strip()
            if not api_key:
                print("[ERROR] API Key를 입력하세요.")
                continue

            secret = input("Secret Key: ").strip()
            if not secret:
                print("[ERROR] Secret Key를 입력하세요.")
                continue

            # Testnet 여부
            testnet_input = input("Testnet 사용? (y/n, 기본=n): ").strip().lower()
            testnet = testnet_input == 'y'

            # 키 저장
            keys_data = {
                'api_key': api_key,
                'secret': secret,
                'testnet': testnet
            }

            print(f"\n[{exchange.upper()}] 키를 암호화하여 저장 중...")

            try:
                # 기존 키 로드 (있으면)
                all_keys = storage.load_api_keys() or {}

                # 현재 거래소 키 추가/업데이트
                all_keys[exchange] = keys_data

                # 저장
                storage.save_api_keys(all_keys)

                print(f"[OK] {exchange.upper()} API 키가 저장되었습니다!")
                print(f"     Testnet: {'Yes' if testnet else 'No'}")

            except Exception as e:
                print(f"[ERROR] 키 저장 실패: {e}")
                continue

            # 추가 설정 여부
            more = input("\n다른 거래소도 설정하시겠습니까? (y/n): ").strip().lower()
            if more != 'y':
                break

        except ValueError:
            print("[ERROR] 숫자를 입력하세요.")

    # 최종 확인
    print("\n" + "=" * 80)
    print("현재 저장된 API 키:")
    print("=" * 80)

    try:
        all_keys = storage.load_api_keys()
        if all_keys:
            for exchange, keys in all_keys.items():
                testnet_str = "Testnet" if keys.get('testnet') else "Mainnet"
                print(f"  {exchange.upper():10s}: API Key={keys['api_key'][:8]}*** ({testnet_str})")
        else:
            print("  (저장된 키 없음)")
    except Exception as e:
        print(f"  [ERROR] 키 로드 실패: {e}")

    print("=" * 80)
    print("\n설정이 완료되었습니다.")
    print("다음 단계: python tools/test_api_connection.py (API 연결 테스트)")


if __name__ == "__main__":
    setup_api_keys()
