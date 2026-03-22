"""
PHP 서버 통합 테스트 스크립트

테스트 항목:
1. API 서버 연결 확인
2. 로그인 API 테스트
3. 모듈 다운로드 API 테스트
4. 모듈 복호화 테스트

사용법:
    python tools/test_server_integration.py
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .env 로드
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    print("python-dotenv 설치 필요: pip install python-dotenv")

import requests

# 설정
API_URL = os.getenv('API_SERVER_URL', 'https://youngstreet.co.kr/api')
MODULE_KEY = os.getenv('MODULE_ENCRYPTION_KEY', '')

# 테스트 계정 (서버에 등록된 계정)
TEST_EMAIL = 'test2@test.com'
TEST_PASSWORD = 'test123'


def print_header(title: str):
    """섹션 헤더 출력"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(name: str, passed: bool, detail: str = ""):
    """결과 출력"""
    status = "PASS" if passed else "FAIL"
    icon = "[OK]" if passed else "[X]"
    print(f"  {icon} {name}: {status}")
    if detail:
        print(f"      {detail}")


def test_api_connection() -> bool:
    """1. API 서버 연결 테스트"""
    print_header("1. API 서버 연결 테스트")

    # health 엔드포인트가 없을 수 있으므로 로그인 페이지로 테스트
    try:
        response = requests.get(
            f"{API_URL}/auth/login.php",
            timeout=10
        )

        # GET 요청에 대해 405나 200 모두 서버가 살아있다는 의미
        if response.status_code in [200, 405, 400]:
            print_result("서버 연결", True, f"상태 코드: {response.status_code}")
            return True
        else:
            print_result("서버 연결", False, f"상태 코드: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError as e:
        print_result("서버 연결", False, f"연결 실패: {e}")
        return False
    except requests.exceptions.Timeout:
        print_result("서버 연결", False, "타임아웃")
        return False
    except Exception as e:
        print_result("서버 연결", False, f"오류: {e}")
        return False


def test_login() -> str | None:
    """2. 로그인 테스트"""
    print_header("2. 로그인 테스트")

    try:
        response = requests.post(
            f"{API_URL}/auth/login.php",
            json={
                'email': TEST_EMAIL,
                'password': TEST_PASSWORD
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        print(f"  상태 코드: {response.status_code}")

        try:
            data = response.json()
        except:
            print_result("로그인", False, f"JSON 파싱 실패: {response.text[:200]}")
            return None

        if data.get('success'):
            token = data.get('token', '')
            user = data.get('user', {})
            tier = user.get('tier', 'unknown')

            print_result("로그인", True)
            print(f"      토큰: {token[:50]}...")
            print(f"      티어: {tier}")
            print(f"      제한: {user.get('tier_limits', {})}")

            return token
        else:
            print_result("로그인", False, f"오류: {data.get('error', 'Unknown')}")
            return None

    except Exception as e:
        print_result("로그인", False, f"오류: {e}")
        return None


def test_module_download(token: str) -> str | None:
    """3. 모듈 다운로드 테스트"""
    print_header("3. 모듈 다운로드 테스트")

    try:
        # GET 메서드 사용 (서버 API 요구사항)
        response = requests.get(
            f"{API_URL}/modules/get.php",
            params={'module': 'indicators'},
            headers={
                'Authorization': f'Bearer {token}'
            },
            timeout=15
        )

        print(f"  상태 코드: {response.status_code}")

        try:
            data = response.json()
        except:
            print_result("모듈 다운로드", False, f"JSON 파싱 실패: {response.text[:200]}")
            return None

        if data.get('success'):
            module_info = data.get('module', {})
            content = data.get('content', '')

            print_result("모듈 다운로드", True)
            print(f"      모듈: {module_info.get('name', 'unknown')}")
            print(f"      버전: {module_info.get('version', 'unknown')}")
            print(f"      콘텐츠 길이: {len(content)} bytes")

            return content
        else:
            print_result("모듈 다운로드", False, f"오류: {data.get('error', 'Unknown')}")
            return None

    except Exception as e:
        print_result("모듈 다운로드", False, f"오류: {e}")
        return None


def test_module_decrypt(encrypted_content: str) -> bool:
    """4. 모듈 복호화 테스트"""
    print_header("4. 모듈 복호화 테스트")

    if not MODULE_KEY:
        print_result("복호화", False, "MODULE_ENCRYPTION_KEY 환경변수 없음")
        return False

    try:
        import base64
        from core.secure_module_loader import SecureModuleLoader

        # 서버에서 이중 Base64로 보내는 경우 처리
        # 첫 번째 디코딩: API 전송용 Base64 제거
        try:
            first_decode = base64.b64decode(encrypted_content)
            # 결과가 여전히 Base64 문자열인지 확인
            if all(c in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in first_decode[:100]):
                # 이중 Base64 - 첫 번째 디코딩 결과를 사용
                encrypted_data = first_decode
                print("      (이중 Base64 감지 - 첫 번째 디코딩 적용)")
            else:
                # 단일 Base64 - 원본 문자열 사용
                encrypted_data = encrypted_content.encode('utf-8')
        except:
            encrypted_data = encrypted_content.encode('utf-8')

        loader = SecureModuleLoader()
        source_code = loader._decrypt_module(encrypted_data)

        if source_code:
            print_result("복호화", True)
            print(f"      소스 코드 길이: {len(source_code)} bytes")

            # 첫 몇 줄 미리보기
            lines = source_code.split('\n')[:5]
            print("      미리보기:")
            for line in lines:
                print(f"        {line[:60]}")

            return True
        else:
            print_result("복호화", False, "복호화 결과 없음")
            return False

    except ImportError as e:
        print_result("복호화", False, f"모듈 import 실패: {e}")
        return False
    except Exception as e:
        print_result("복호화", False, f"오류: {e}")
        return False


def test_local_fallback() -> bool:
    """5. 로컬 폴백 테스트 (서버 없이 로컬 .enc 파일 로드)"""
    print_header("5. 로컬 폴백 테스트")

    enc_dir = PROJECT_ROOT / "encrypted_modules"

    if not enc_dir.exists():
        print_result("로컬 폴백", False, f"encrypted_modules 폴더 없음")
        return False

    enc_files = list(enc_dir.glob("*.enc"))

    if not enc_files:
        print_result("로컬 폴백", False, "*.enc 파일 없음")
        return False

    print(f"  발견된 .enc 파일: {len(enc_files)}개")
    for f in enc_files[:5]:
        print(f"    - {f.name} ({f.stat().st_size} bytes)")

    # 첫 번째 파일로 복호화 테스트
    try:
        from core.secure_module_loader import SecureModuleLoader

        loader = SecureModuleLoader()

        with open(enc_files[0], 'rb') as f:
            encrypted_data = f.read()

        source_code = loader._decrypt_module(encrypted_data)

        if source_code:
            print_result("로컬 폴백", True, f"{enc_files[0].name} 복호화 성공")
            return True
        else:
            print_result("로컬 폴백", False, "복호화 실패")
            return False

    except Exception as e:
        print_result("로컬 폴백", False, f"오류: {e}")
        return False


def main():
    """전체 테스트 실행"""
    print("\n" + "="*60)
    print("  TwinStar-Quantum PHP 서버 통합 테스트")
    print("="*60)
    print(f"\n  API URL: {API_URL}")
    print(f"  테스트 계정: {TEST_EMAIL}")
    print(f"  암호화 키: {'설정됨' if MODULE_KEY else '미설정'}")

    results = []

    # 1. API 연결
    connected = test_api_connection()
    results.append(("API 연결", connected))

    if not connected:
        print("\n[!] 서버 연결 실패로 나머지 테스트 건너뜀")
        print("    서버 상태를 확인하세요.")
    else:
        # 2. 로그인
        token = test_login()
        results.append(("로그인", token is not None))

        if token:
            # 3. 모듈 다운로드
            content = test_module_download(token)
            results.append(("모듈 다운로드", content is not None))

            if content:
                # 4. 모듈 복호화
                decrypted = test_module_decrypt(content)
                results.append(("모듈 복호화", decrypted))

    # 5. 로컬 폴백 (서버 연결과 무관하게 테스트)
    local_ok = test_local_fallback()
    results.append(("로컬 폴백", local_ok))

    # 결과 요약
    print_header("테스트 결과 요약")

    for name, passed in results:
        print_result(name, passed)

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n  총 {passed_count}/{total_count} 테스트 통과")

    if passed_count == total_count:
        print("\n  [OK] 모든 테스트 통과! 서버 통합 준비 완료")
    else:
        print("\n  [!] 일부 테스트 실패. 위 오류를 확인하세요.")

    return passed_count == total_count


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
