"""
test_secure_module_loader.py - SecureModuleLoader 통합 테스트

테스트 항목:
1. 서버 연결 확인
2. 로그인 API 호출
3. 모듈 다운로드 API 호출
4. 암호화된 모듈 복호화
5. 모듈 로드 및 함수 실행

사용법:
    python tools/test_secure_module_loader.py
    python tools/test_secure_module_loader.py --server  # 서버 연동 테스트
    python tools/test_secure_module_loader.py --local   # 로컬만 테스트
"""

import os
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_local_encryption():
    """로컬 암호화/복호화 테스트"""
    print("\n" + "=" * 60)
    print("1. 로컬 암호화/복호화 테스트")
    print("=" * 60)

    from tools.encrypt_module import ENCRYPTED_DIR, decrypt_file

    enc_files = list(ENCRYPTED_DIR.glob("*.enc"))
    print(f"   암호화된 파일: {len(enc_files)}개")

    if not enc_files:
        print("   [SKIP] 암호화된 파일 없음 - 먼저 --all 실행 필요")
        return False

    # 첫 번째 파일 복호화 테스트
    test_file = enc_files[0]
    source = decrypt_file(test_file)

    if source:
        print(f"   [OK] {test_file.name} 복호화 성공 ({len(source):,} bytes)")
        return True
    else:
        print(f"   [FAIL] {test_file.name} 복호화 실패")
        return False


def test_module_loader():
    """SecureModuleLoader 테스트"""
    print("\n" + "=" * 60)
    print("2. SecureModuleLoader 테스트")
    print("=" * 60)

    from core.secure_module_loader import SecureModuleLoader, get_loader

    loader = get_loader()
    print(f"   로더 생성: OK")

    # 모듈 로드 테스트
    test_modules = ['indicators', 'strategy_core', 'optimizer']
    results = {}

    for module_name in test_modules:
        module = loader.load_module(module_name)
        results[module_name] = module is not None

        if module:
            # 주요 속성 확인
            attrs = [attr for attr in dir(module) if not attr.startswith('_')][:3]
            print(f"   [OK] {module_name}: {', '.join(attrs)}")
        else:
            print(f"   [FAIL] {module_name}: 로드 실패")

    return all(results.values())


def test_module_functions():
    """로드된 모듈 함수 실행 테스트"""
    print("\n" + "=" * 60)
    print("3. 모듈 함수 실행 테스트")
    print("=" * 60)

    from core.secure_module_loader import get_loader
    import pandas as pd
    import numpy as np

    loader = get_loader()

    # indicators 테스트
    indicators = loader.load_module('indicators')
    if indicators and hasattr(indicators, 'calculate_rsi'):
        # 테스트 데이터 생성
        test_data = pd.Series(np.random.randn(100).cumsum() + 100)
        try:
            rsi = indicators.calculate_rsi(test_data, 14)
            # 반환 타입에 따라 처리
            if hasattr(rsi, 'iloc'):
                last_val = rsi.iloc[-1]
            elif hasattr(rsi, '__getitem__'):
                last_val = rsi[-1]
            else:
                last_val = float(rsi) if rsi is not None else 0
            print(f"   [OK] calculate_rsi(): RSI 계산 성공 (최근값: {last_val:.2f})")
        except Exception as e:
            print(f"   [FAIL] calculate_rsi(): {e}")
            return False
    else:
        print("   [SKIP] indicators 모듈 없음")

    # strategy_core 테스트
    strategy = loader.load_module('strategy_core')
    if strategy and hasattr(strategy, 'AlphaX7Core'):
        print(f"   [OK] AlphaX7Core 클래스 존재")
    else:
        print("   [SKIP] strategy_core 모듈 없음")

    return True


def test_license_integration():
    """LicenseGuard 연동 테스트"""
    print("\n" + "=" * 60)
    print("4. LicenseGuard 연동 테스트")
    print("=" * 60)

    from core.license_guard import get_license_guard, get_module_manager, MODULE_PERMISSIONS

    guard = get_license_guard()
    manager = get_module_manager()

    print(f"   현재 티어: {guard.tier}")
    print(f"   접근 가능 모듈: {manager.get_allowed_modules()}")

    # 티어별 권한 표시
    print("\n   티어별 모듈 권한:")
    for tier, modules in MODULE_PERMISSIONS.items():
        count = "전체" if '*' in modules else len(modules)
        print(f"     {tier}: {count}개")

    return True


def test_server_connection():
    """서버 연결 테스트"""
    print("\n" + "=" * 60)
    print("5. 서버 연결 테스트")
    print("=" * 60)

    import requests

    api_url = os.environ.get("API_SERVER_URL", "https://youngstreet.co.kr/api")

    try:
        # ping 테스트
        response = requests.get(f"{api_url}/ping", timeout=5)
        if response.status_code == 200:
            print(f"   [OK] 서버 연결 성공: {api_url}")
            return True
        else:
            print(f"   [WARN] 서버 응답 코드: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"   [SKIP] 서버 연결 실패: {e}")
        print("   (오프라인 모드에서는 로컬 모듈만 사용)")
        return False


def test_login_api():
    """로그인 API 테스트"""
    print("\n" + "=" * 60)
    print("6. 로그인 API 테스트")
    print("=" * 60)

    from core.license_guard import get_license_guard

    guard = get_license_guard()

    # 테스트 계정으로 로그인 시도 (실제 서버 필요)
    test_email = os.environ.get("TEST_EMAIL", "test@example.com")

    print(f"   테스트 계정: {test_email}")

    # login() 메서드는 email만 받음
    result = guard.login(test_email)

    if result.get('success'):
        print(f"   [OK] 로그인 성공")
        print(f"   토큰: {guard.token[:20]}..." if guard.token else "   토큰: None")
        print(f"   티어: {guard.tier}")
        print(f"   남은 일수: {guard.days_left}")
        return True
    else:
        print(f"   [SKIP] 로그인 실패: {result.get('error', 'Unknown')}")
        print("   (테스트 계정이 없거나 서버 미연결)")
        return False


def main():
    parser = argparse.ArgumentParser(description="SecureModuleLoader 통합 테스트")
    parser.add_argument('--server', action='store_true', help='서버 연동 테스트 포함')
    parser.add_argument('--local', action='store_true', help='로컬만 테스트')
    args = parser.parse_args()

    print("=" * 60)
    print("SecureModuleLoader 통합 테스트")
    print("=" * 60)

    results = {}

    # 1. 로컬 암호화 테스트
    results['encryption'] = test_local_encryption()

    # 2. 모듈 로더 테스트
    results['loader'] = test_module_loader()

    # 3. 함수 실행 테스트
    results['functions'] = test_module_functions()

    # 4. 라이선스 연동 테스트
    results['license'] = test_license_integration()

    # 5-6. 서버 테스트 (옵션)
    if args.server or not args.local:
        results['server'] = test_server_connection()
        if results.get('server'):
            results['login'] = test_login_api()

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "PASS" if result else "FAIL/SKIP"
        print(f"   {name}: {status}")

    print(f"\n   총 {passed}/{total} 통과")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
