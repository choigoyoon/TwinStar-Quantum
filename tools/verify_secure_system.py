"""
verify_secure_system.py - 보안 시스템 전체 검증 도구

검증 항목:
1. 암호화 키 설정 확인
2. 암호화된 모듈 파일 검증
3. 복호화 테스트
4. 라이선스 매니저 연동
5. 서버 API 연결
6. 티어별 모듈 접근 권한
7. 실제 모듈 로드 테스트

사용법:
    python tools/verify_secure_system.py           # 전체 검증
    python tools/verify_secure_system.py --quick   # 빠른 검증 (서버 제외)
    python tools/verify_secure_system.py --server  # 서버 연결만 검증
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 색상 출력 (Windows 지원)
try:
    import colorama
    colorama.init()
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
except ImportError:
    GREEN = RED = YELLOW = BLUE = RESET = BOLD = ""


def print_header(title: str):
    """섹션 헤더 출력"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_result(name: str, passed: bool, detail: str = ""):
    """결과 출력"""
    status = f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"
    detail_str = f" - {detail}" if detail else ""
    print(f"  {status} {name}{detail_str}")


def print_warning(msg: str):
    """경고 출력"""
    print(f"  {YELLOW}[WARN]{RESET} {msg}")


def print_info(msg: str):
    """정보 출력"""
    print(f"  {BLUE}[INFO]{RESET} {msg}")


class SecureSystemVerifier:
    """보안 시스템 검증기"""

    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.details: Dict[str, str] = {}
        self.start_time = time.time()

    def verify_all(self, include_server: bool = True) -> bool:
        """전체 검증 실행"""
        print(f"\n{BOLD}TwinStar Quantum - 보안 시스템 검증{RESET}")
        print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"프로젝트: {PROJECT_ROOT}")

        # 1. 환경 설정 검증
        self._verify_environment()

        # 2. 암호화 파일 검증
        self._verify_encrypted_files()

        # 3. 암호화 키 검증
        self._verify_encryption_key()

        # 4. 복호화 테스트
        self._verify_decryption()

        # 5. 라이선스 매니저 검증
        self._verify_license_manager()

        # 6. 서버 API 검증 (선택)
        if include_server:
            self._verify_server_api()

        # 7. 모듈 로드 테스트
        self._verify_module_loading()

        # 8. 티어별 권한 검증
        self._verify_tier_permissions()

        # 결과 요약
        self._print_summary()

        return all(self.results.values())

    def _verify_environment(self):
        """환경 설정 검증"""
        print_header("1. 환경 설정 검증")

        # .env 파일 존재
        env_file = PROJECT_ROOT / ".env"
        env_exists = env_file.exists()
        self.results["env_file"] = env_exists
        print_result(".env 파일", env_exists)

        # .env.example 존재
        env_example = PROJECT_ROOT / ".env.example"
        example_exists = env_example.exists()
        self.results["env_example"] = example_exists
        print_result(".env.example 파일", example_exists)

        # 필수 환경 변수 확인
        required_vars = ["MODULE_ENCRYPTION_KEY"]
        optional_vars = ["MODULE_SERVER_URL", "API_SERVER_URL"]

        for var in required_vars:
            value = os.environ.get(var)
            has_value = value is not None and len(value) > 0
            self.results[f"env_{var}"] = has_value
            if has_value:
                # 키 형식 표시
                if var == "MODULE_ENCRYPTION_KEY":
                    if len(value) == 44 and value.endswith('='):
                        print_result(f"${var}", True, "Base64 형식")
                    elif len(value) == 64:
                        print_result(f"${var}", True, "Hex 형식")
                    else:
                        print_result(f"${var}", True, f"Raw 형식 ({len(value)}자)")
                else:
                    print_result(f"${var}", True)
            else:
                print_result(f"${var}", False, "미설정")

        for var in optional_vars:
            value = os.environ.get(var)
            has_value = value is not None and len(value) > 0
            if has_value:
                print_info(f"${var} = {value[:50]}...")
            else:
                print_warning(f"${var} 미설정 (선택 사항)")

    def _verify_encrypted_files(self):
        """암호화된 파일 검증"""
        print_header("2. 암호화된 모듈 파일 검증")

        enc_dir = PROJECT_ROOT / "encrypted_modules"
        dir_exists = enc_dir.exists()
        self.results["enc_dir"] = dir_exists
        print_result("encrypted_modules/ 디렉토리", dir_exists)

        if not dir_exists:
            print_warning("암호화된 모듈 디렉토리가 없습니다. encrypt_module.py --all 실행 필요")
            return

        # 필수 모듈 목록
        required_modules = [
            "strategy_core.enc",
            "optimizer.enc",
            "indicators.enc",
            "signal_processor.enc",
        ]
        optional_modules = [
            "order_executor.enc",
            "position_manager.enc",
            "coarse_to_fine_optimizer.enc",
            "wm_pattern_strategy.enc",
            "base_strategy.enc",
        ]

        enc_files = list(enc_dir.glob("*.enc"))
        total_size = sum(f.stat().st_size for f in enc_files)

        print_info(f"총 {len(enc_files)}개 파일, {total_size:,} bytes")

        # 필수 모듈 확인
        for module in required_modules:
            path = enc_dir / module
            exists = path.exists()
            self.results[f"enc_{module}"] = exists
            if exists:
                size = path.stat().st_size
                print_result(module, True, f"{size:,} bytes")
            else:
                print_result(module, False, "파일 없음")

        # 선택 모듈 확인
        for module in optional_modules:
            path = enc_dir / module
            if path.exists():
                size = path.stat().st_size
                print_info(f"{module}: {size:,} bytes")

    def _verify_encryption_key(self):
        """암호화 키 검증"""
        print_header("3. 암호화 키 검증")

        try:
            from core.secure_module_loader import get_encryption_key
            key = get_encryption_key()

            # 키 길이 확인
            key_len_ok = len(key) == 32
            self.results["key_length"] = key_len_ok
            print_result("키 길이 (32바이트)", key_len_ok, f"{len(key)} bytes")

            # 기본 키 사용 여부 확인
            default_key = b'TwinStar_Quantum_Secret_Key_32!!'
            using_default = key == default_key
            self.results["key_not_default"] = not using_default
            if using_default:
                print_result("프로덕션 키 사용", False, "기본 키 사용 중 (보안 취약)")
            else:
                print_result("프로덕션 키 사용", True, "커스텀 키 사용")

        except ImportError as e:
            self.results["key_length"] = False
            self.results["key_not_default"] = False
            print_result("암호화 모듈 import", False, str(e))

    def _verify_decryption(self):
        """복호화 테스트"""
        print_header("4. 복호화 테스트")

        enc_dir = PROJECT_ROOT / "encrypted_modules"
        if not enc_dir.exists():
            print_warning("암호화 디렉토리 없음 - 테스트 건너뜀")
            return

        try:
            from tools.encrypt_module import decrypt_file

            enc_files = list(enc_dir.glob("*.enc"))[:3]  # 처음 3개만 테스트

            for enc_file in enc_files:
                try:
                    source = decrypt_file(enc_file)
                    if source:
                        # Python 구문 검증
                        compile(source, enc_file.name, 'exec')
                        self.results[f"decrypt_{enc_file.stem}"] = True
                        print_result(enc_file.name, True, f"{len(source):,} bytes 복호화")
                    else:
                        self.results[f"decrypt_{enc_file.stem}"] = False
                        print_result(enc_file.name, False, "복호화 실패")
                except SyntaxError as e:
                    self.results[f"decrypt_{enc_file.stem}"] = False
                    print_result(enc_file.name, False, f"구문 오류: {e}")
                except Exception as e:
                    self.results[f"decrypt_{enc_file.stem}"] = False
                    print_result(enc_file.name, False, str(e))

        except ImportError as e:
            print_warning(f"encrypt_module import 실패: {e}")

    def _verify_license_manager(self):
        """라이선스 매니저 검증"""
        print_header("5. 라이선스 매니저 검증")

        try:
            from license_manager import get_license_manager, LicenseManager

            lm = get_license_manager()

            # 인스턴스 생성 확인
            is_instance = isinstance(lm, LicenseManager)
            self.results["lm_instance"] = is_instance
            print_result("LicenseManager 인스턴스", is_instance)

            # HW ID 생성 확인
            hw_id = lm.get_hw_id()
            has_hw_id = hw_id and len(hw_id) >= 8
            self.results["lm_hw_id"] = has_hw_id
            print_result("HW ID 생성", has_hw_id, f"{hw_id[:16]}..." if hw_id else "없음")

            # 티어 확인
            tier = lm.get_tier()
            has_tier = tier is not None
            self.results["lm_tier"] = has_tier
            print_result("현재 티어", has_tier, tier)

            # 제한 정보
            limits = lm.get_limits()
            has_limits = limits is not None
            print_info(f"제한: {limits}")

        except ImportError as e:
            self.results["lm_instance"] = False
            print_result("LicenseManager import", False, str(e))

    def _verify_server_api(self):
        """서버 API 검증"""
        print_header("6. 서버 API 연결 검증")

        import requests

        # Ping 테스트
        ping_urls = [
            "https://youngstreet.co.kr/membership/ping.php",
            os.environ.get("API_SERVER_URL", "https://youngstreet.co.kr/api") + "/ping"
        ]

        server_ok = False
        for url in ping_urls:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    server_ok = True
                    self.results["server_ping"] = True
                    print_result(f"서버 연결 ({url})", True, f"HTTP {resp.status_code}")
                    break
                else:
                    print_warning(f"{url}: HTTP {resp.status_code}")
            except requests.RequestException as e:
                print_warning(f"{url}: {e}")

        if not server_ok:
            self.results["server_ping"] = False
            print_result("서버 연결", False, "모든 엔드포인트 실패")

        # 모듈 서버 테스트 (선택)
        module_url = os.environ.get("MODULE_SERVER_URL")
        if module_url:
            try:
                resp = requests.get(module_url, timeout=5)
                module_ok = resp.status_code in [200, 401, 403]  # 인증 필요해도 OK
                self.results["module_server"] = module_ok
                print_result("모듈 서버", module_ok, f"HTTP {resp.status_code}")
            except requests.RequestException as e:
                self.results["module_server"] = False
                print_result("모듈 서버", False, str(e))

    def _verify_module_loading(self):
        """모듈 로드 테스트"""
        print_header("7. 모듈 로드 테스트")

        try:
            from core.secure_module_loader import get_loader

            loader = get_loader()

            test_modules = ['indicators', 'strategy_core', 'optimizer']

            for module_name in test_modules:
                try:
                    module = loader.load_module(module_name)
                    loaded = module is not None
                    self.results[f"load_{module_name}"] = loaded

                    if loaded:
                        # 주요 속성 확인
                        attrs = [a for a in dir(module) if not a.startswith('_')][:3]
                        print_result(module_name, True, f"속성: {', '.join(attrs)}")
                    else:
                        print_result(module_name, False, "로드 실패")

                except Exception as e:
                    self.results[f"load_{module_name}"] = False
                    print_result(module_name, False, str(e))

        except ImportError as e:
            print_result("SecureModuleLoader import", False, str(e))

    def _verify_tier_permissions(self):
        """티어별 권한 검증"""
        print_header("8. 티어별 모듈 권한 검증")

        from core.secure_module_loader import MODULE_PERMISSIONS

        print_info("티어별 접근 가능 모듈:")
        for tier, modules in MODULE_PERMISSIONS.items():
            if '*' in modules:
                print(f"    {tier}: 전체 ({len(modules)}개 정의)")
            else:
                print(f"    {tier}: {len(modules)}개 - {modules}")

        # 현재 티어 확인
        try:
            from license_manager import get_license_manager
            lm = get_license_manager()
            current_tier = lm.get_tier().lower()

            # 티어 매핑
            tier_map = {'trial': 'free', 'expired': 'free'}
            mapped_tier = tier_map.get(current_tier, current_tier)

            allowed = MODULE_PERMISSIONS.get(mapped_tier, [])
            self.results["tier_permission"] = True
            print_info(f"현재 티어 '{current_tier}' -> 접근 가능: {allowed if allowed else '없음'}")

        except Exception as e:
            print_warning(f"티어 확인 실패: {e}")

    def _print_summary(self):
        """결과 요약 출력"""
        print_header("검증 결과 요약")

        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        elapsed = time.time() - self.start_time

        print(f"\n  총 {total}개 항목 중 {passed}개 통과")
        print(f"  통과율: {passed/total*100:.1f}%")
        print(f"  소요 시간: {elapsed:.2f}초")

        # 실패 항목 표시
        failed = [k for k, v in self.results.items() if not v]
        if failed:
            print(f"\n  {RED}실패 항목:{RESET}")
            for item in failed:
                print(f"    - {item}")

        # 최종 판정
        all_critical_passed = all(
            self.results.get(k, False) for k in [
                "env_MODULE_ENCRYPTION_KEY",
                "enc_dir",
                "key_length",
                "lm_instance"
            ]
        )

        print(f"\n  {BOLD}최종 판정:{RESET} ", end="")
        if all_critical_passed:
            print(f"{GREEN}시스템 정상{RESET}")
        else:
            print(f"{RED}필수 항목 실패 - 점검 필요{RESET}")

        print(f"\n{'='*60}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="보안 시스템 전체 검증")
    parser.add_argument('--quick', action='store_true', help='빠른 검증 (서버 제외)')
    parser.add_argument('--server', action='store_true', help='서버 연결만 검증')
    args = parser.parse_args()

    verifier = SecureSystemVerifier()

    if args.server:
        # 서버만 검증
        verifier._verify_server_api()
    else:
        # 전체 검증
        include_server = not args.quick
        success = verifier.verify_all(include_server=include_server)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
