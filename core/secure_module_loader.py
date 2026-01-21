"""
secure_module_loader.py - 암호화된 모듈 보안 로더

기능:
- 서버에서 .enc 파일 다운로드 (라이선스 검증 포함)
- 로컬 폴백: 서버 실패 시 encrypted_modules/ 폴더에서 로드
- RAM에서 복호화 (디스크 저장 안 함)
- exec() + types.ModuleType으로 동적 모듈 생성

보안 포인트:
- 디스크에 평문 코드 절대 저장 안 함
- 라이선스 검증 실패 시 로드 거부
- 메모리에서만 코드 실행

사용법:
    from core.secure_module_loader import SecureModuleLoader

    loader = SecureModuleLoader()
    strategy_core = loader.load_module('strategy_core')

    if strategy_core:
        core = strategy_core.AlphaX7Core(...)
"""

import os
import sys
import gzip
import base64
import types
import logging
import requests
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# pycryptodome
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    AES = None
    unpad = None
    logger.warning("pycryptodome 없음 - 암호화 모듈 로드 불가")

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
ENCRYPTED_DIR = PROJECT_ROOT / "encrypted_modules"


def get_encryption_key() -> bytes:
    """암호화 키 가져오기 (환경 변수 또는 기본값)

    키 형식 지원:
    - Base64 (44자, '='로 끝남): Base64 디코딩 → 32바이트
    - Hex (64자): Hex 디코딩 → 32바이트
    - Raw (32자): UTF-8 인코딩 → 32바이트
    """
    key = os.environ.get("MODULE_ENCRYPTION_KEY")
    if key:
        # Base64 형식 감지 (44자, '='로 끝나거나 Base64 문자만 포함)
        if len(key) == 44 and key.endswith('='):
            try:
                key_bytes = base64.b64decode(key)
                if len(key_bytes) == 32:
                    return key_bytes
            except Exception:
                pass

        # Hex 형식 감지 (64자, 16진수만 포함)
        if len(key) == 64:
            try:
                key_bytes = bytes.fromhex(key)
                if len(key_bytes) == 32:
                    return key_bytes
            except ValueError:
                pass

        # Raw UTF-8 형식 (32자 이하)
        key_bytes = key.encode('utf-8')
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        return key_bytes
    else:
        # 기본 키 (개발용)
        return b'TwinStar_Quantum_Secret_Key_32!!'


# 티어별 모듈 접근 권한
MODULE_PERMISSIONS = {
    'free': [],
    'basic': ['indicators'],
    'standard': ['indicators', 'strategy_core', 'signal_processor', 'base_strategy'],
    'premium': ['indicators', 'strategy_core', 'signal_processor', 'base_strategy',
                'optimizer', 'meta_optimizer', 'coarse_to_fine_optimizer',
                'wm_pattern_strategy', 'order_executor', 'position_manager'],
    'admin': ['*'],  # 전체 접근
}


class SecureModuleLoader:
    """암호화된 모듈 보안 로더"""

    def __init__(self, license_guard: Optional[Any] = None):
        """
        Args:
            license_guard: LicenseGuard 인스턴스 (라이선스 검증용)
        """
        self.license_guard = license_guard
        self._loaded_modules: dict[str, types.ModuleType] = {}
        self._module_server_url = os.environ.get(
            "MODULE_SERVER_URL",
            "https://youngstreet.co.kr/membership/api_module.php"
        )

    def _check_permission(self, module_name: str) -> bool:
        """모듈 접근 권한 확인"""
        if self.license_guard is None:
            # 라이선스 가드 없으면 개발 모드로 간주
            logger.warning(f"라이선스 가드 없음 - 개발 모드로 {module_name} 허용")
            return True

        # LicenseGuard 또는 LicenseManager 모두 지원
        # LicenseGuard: tier 속성 직접 접근
        # LicenseManager: get_tier() 메서드 사용
        if hasattr(self.license_guard, 'get_tier'):
            tier = self.license_guard.get_tier().lower()
        else:
            tier = getattr(self.license_guard, 'tier', 'free')

        # 티어 이름 정규화 (TRIAL -> free, BASIC -> basic 등)
        tier_map = {
            'trial': 'free',
            'expired': 'free',
            'basic': 'basic',
            'standard': 'standard',
            'premium': 'premium',
            'admin': 'admin'
        }
        tier = tier_map.get(tier.lower(), tier.lower())

        allowed = MODULE_PERMISSIONS.get(tier, [])

        if '*' in allowed:
            return True

        if module_name in allowed:
            return True

        logger.warning(f"접근 거부: {module_name} (티어: {tier})")
        return False

    def _decrypt_module(self, encrypted_data: bytes) -> Optional[str]:
        """암호화된 모듈 복호화 (RAM에서만)"""
        if not HAS_CRYPTO or AES is None:
            logger.error("복호화 라이브러리 없음")
            return None

        try:
            # 1. Base64 디코딩
            combined = base64.b64decode(encrypted_data)

            # 2. IV와 암호문 분리
            iv = combined[:16]
            encrypted = combined[16:]

            # 3. AES 복호화
            key = get_encryption_key()
            from typing import cast
            cipher_engine = cast(Any, AES)
            cipher = cipher_engine.new(key, AES.MODE_CBC, iv)
            padded_data = cipher.decrypt(encrypted)
            unpad_func = cast(Any, unpad)
            compressed = unpad_func(padded_data, AES.block_size)

            # 4. gzip 압축 해제
            source_code = gzip.decompress(compressed).decode('utf-8')

            return source_code

        except Exception as e:
            logger.error(f"복호화 실패: {e}")
            return None

    def _download_from_server(self, module_name: str) -> Optional[bytes]:
        """서버에서 암호화된 모듈 다운로드"""
        if self.license_guard is None or not hasattr(self.license_guard, 'token'):
            logger.warning("라이선스 토큰 없음 - 서버 다운로드 건너뜀")
            return None

        try:
            headers = {
                'Authorization': f'Bearer {self.license_guard.token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(
                self._module_server_url,
                json={'module': module_name},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('encrypted_module'):
                    logger.info(f"서버에서 {module_name} 다운로드 성공")
                    return data['encrypted_module'].encode('utf-8')
                else:
                    logger.warning(f"서버 응답 오류: {data.get('error', 'Unknown')}")
            else:
                logger.warning(f"서버 응답 코드: {response.status_code}")

        except requests.RequestException as e:
            logger.warning(f"서버 연결 실패: {e}")

        return None

    def _load_from_local(self, module_name: str) -> Optional[bytes]:
        """로컬에서 암호화된 모듈 로드"""
        enc_path = ENCRYPTED_DIR / f"{module_name}.enc"

        if not enc_path.exists():
            logger.warning(f"로컬 파일 없음: {enc_path}")
            return None

        try:
            with open(enc_path, 'rb') as f:
                encrypted_data = f.read()
            logger.info(f"로컬에서 {module_name} 로드 성공")
            return encrypted_data
        except Exception as e:
            logger.error(f"로컬 파일 읽기 실패: {e}")
            return None

    def _create_module(self, module_name: str, source_code: str) -> Optional[types.ModuleType]:
        """소스 코드로 모듈 객체 생성"""
        try:
            # 모듈 객체 생성
            module = types.ModuleType(module_name)
            module.__file__ = f"<encrypted:{module_name}>"
            # __loader__는 타입 호환성 문제로 설정하지 않음

            # 글로벌 네임스페이스 설정
            module.__dict__['__builtins__'] = __builtins__

            # 코드 실행
            exec(compile(source_code, f"<encrypted:{module_name}>", 'exec'), module.__dict__)

            # sys.modules에 등록
            sys.modules[module_name] = module

            logger.info(f"모듈 생성 완료: {module_name}")
            return module

        except SyntaxError as e:
            logger.error(f"구문 오류 ({module_name}): {e}")
            return None
        except Exception as e:
            logger.error(f"모듈 생성 실패 ({module_name}): {e}")
            return None

    def load_module(self, module_name: str, force_reload: bool = False) -> Optional[types.ModuleType]:
        """
        암호화된 모듈 로드

        Args:
            module_name: 모듈 이름 (예: 'strategy_core', 'optimizer')
            force_reload: 강제 재로드 여부

        Returns:
            로드된 모듈 또는 None
        """
        # 이미 로드된 경우
        if not force_reload and module_name in self._loaded_modules:
            return self._loaded_modules[module_name]

        # 권한 확인
        if not self._check_permission(module_name):
            return None

        encrypted_data = None

        # 1. 서버에서 다운로드 시도
        encrypted_data = self._download_from_server(module_name)

        # 2. 서버 실패 시 로컬 폴백
        if encrypted_data is None:
            encrypted_data = self._load_from_local(module_name)

        # 3. 둘 다 실패
        if encrypted_data is None:
            logger.error(f"모듈 로드 실패: {module_name}")
            return None

        # 4. 복호화
        source_code = self._decrypt_module(encrypted_data)
        if source_code is None:
            return None

        # 5. 모듈 생성
        module = self._create_module(module_name, source_code)
        if module is not None:
            self._loaded_modules[module_name] = module

        return module

    def get_loaded_modules(self) -> list[str]:
        """로드된 모듈 목록"""
        return list(self._loaded_modules.keys())

    def unload_module(self, module_name: str) -> bool:
        """모듈 언로드 (메모리에서 제거)"""
        if module_name in self._loaded_modules:
            del self._loaded_modules[module_name]
            if module_name in sys.modules:
                del sys.modules[module_name]
            logger.info(f"모듈 언로드: {module_name}")
            return True
        return False

    def unload_all(self):
        """모든 모듈 언로드"""
        for module_name in list(self._loaded_modules.keys()):
            self.unload_module(module_name)


# 전역 로더 인스턴스 (싱글톤)
_global_loader: Optional[SecureModuleLoader] = None


def get_loader(license_guard: Optional[Any] = None) -> SecureModuleLoader:
    """
    전역 로더 인스턴스 가져오기

    Args:
        license_guard: LicenseGuard 또는 LicenseManager 인스턴스
                       None이면 자동으로 LicenseManager 시도

    Returns:
        SecureModuleLoader 인스턴스
    """
    global _global_loader

    # license_guard가 없으면 LicenseManager 자동 로드 시도
    if license_guard is None:
        try:
            from license_manager import get_license_manager
            license_guard = get_license_manager()
            logger.info("LicenseManager 자동 연동")
        except ImportError:
            logger.warning("LicenseManager 미설치 - 개발 모드")

    if _global_loader is None:
        _global_loader = SecureModuleLoader(license_guard)
    elif license_guard is not None:
        _global_loader.license_guard = license_guard
    return _global_loader


def load_secure_module(module_name: str) -> Optional[types.ModuleType]:
    """편의 함수: 모듈 로드"""
    return get_loader().load_module(module_name)
