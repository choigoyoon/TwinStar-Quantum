"""
encrypt_module.py - 핵심 모듈 암호화 도구

기능:
- Python 소스 파일을 AES-256-CBC로 암호화
- encrypted_modules/ 폴더에 .enc 파일 생성
- --all 옵션으로 전체 핵심 모듈 일괄 암호화
- --verify 옵션으로 암호화/복호화 검증

암호화 방식:
    원본 .py -> gzip 압축 -> AES-256-CBC (IV 16바이트) -> Base64 인코딩 -> .enc

사용법:
    python tools/encrypt_module.py core/strategy_core.py
    python tools/encrypt_module.py --all
    python tools/encrypt_module.py --verify
"""

import os
import sys
import gzip
import base64
import argparse
from pathlib import Path
from typing import Optional

# pycryptodome
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Random import get_random_bytes
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("[ERROR] pycryptodome 필요: pip install pycryptodome")
    sys.exit(1)

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
ENCRYPTED_DIR = PROJECT_ROOT / "encrypted_modules"

# 암호화 키 (32바이트, 환경 변수에서 로드)
def get_encryption_key() -> bytes:
    """암호화 키 가져오기 (환경 변수 또는 기본값)

    키 형식 지원:
    - Base64 (44자, '='로 끝남): Base64 디코딩 → 32바이트
    - Hex (64자): Hex 디코딩 → 32바이트
    - Raw (32자): UTF-8 인코딩 → 32바이트
    """
    key = os.environ.get("MODULE_ENCRYPTION_KEY")
    if key:
        # Base64 형식 감지 (44자, '='로 끝남)
        if len(key) == 44 and key.endswith('='):
            try:
                key_bytes = base64.b64decode(key)
                if len(key_bytes) == 32:
                    print(f"[INFO] Base64 키 사용 (32바이트)")
                    return key_bytes
            except Exception:
                pass

        # Hex 형식 감지 (64자)
        if len(key) == 64:
            try:
                key_bytes = bytes.fromhex(key)
                if len(key_bytes) == 32:
                    print(f"[INFO] Hex 키 사용 (32바이트)")
                    return key_bytes
            except ValueError:
                pass

        # Raw UTF-8 형식
        key_bytes = key.encode('utf-8')
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b'\0')
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        print(f"[INFO] Raw 키 사용 ({len(key_bytes)}바이트)")
        return key_bytes
    else:
        # 기본 키 (개발용, 프로덕션에서는 반드시 환경 변수 사용)
        print("[WARNING] MODULE_ENCRYPTION_KEY 환경 변수 미설정 - 기본 키 사용")
        return b'TwinStar_Quantum_Secret_Key_32!!'


# 보호 대상 핵심 모듈 목록
CORE_MODULES = [
    "core/strategy_core.py",
    "core/optimizer.py",
    "core/signal_processor.py",
    "core/order_executor.py",
    "core/position_manager.py",
    "core/meta_optimizer.py",
    "core/coarse_to_fine_optimizer.py",
    "utils/indicators.py",
    "strategies/wm_pattern_strategy.py",
    "strategies/base_strategy.py",
]


def encrypt_file(source_path: Path, output_path: Optional[Path] = None) -> bool:
    """
    파일 암호화

    Args:
        source_path: 원본 .py 파일 경로
        output_path: 출력 .enc 파일 경로 (None이면 자동 생성)

    Returns:
        성공 여부
    """
    if not source_path.exists():
        print(f"[ERROR] 파일 없음: {source_path}")
        return False

    # 출력 경로 결정
    if output_path is None:
        # core/strategy_core.py -> encrypted_modules/strategy_core.enc
        module_name = source_path.stem
        output_path = ENCRYPTED_DIR / f"{module_name}.enc"

    # 출력 디렉토리 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 1. 원본 파일 읽기
        with open(source_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # 2. gzip 압축
        compressed = gzip.compress(source_code.encode('utf-8'))

        # 3. AES-256-CBC 암호화
        key = get_encryption_key()
        iv = get_random_bytes(16)  # 초기화 벡터
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_data = pad(compressed, AES.block_size)
        encrypted = cipher.encrypt(padded_data)

        # 4. IV + 암호문 결합 후 Base64 인코딩
        combined = iv + encrypted
        encoded = base64.b64encode(combined)

        # 5. 파일 저장
        with open(output_path, 'wb') as f:
            f.write(encoded)

        print(f"[OK] {source_path.name} -> {output_path.name} ({len(source_code):,} bytes -> {len(encoded):,} bytes)")
        return True

    except Exception as e:
        print(f"[ERROR] 암호화 실패 ({source_path}): {e}")
        return False


def decrypt_file(enc_path: Path) -> Optional[str]:
    """
    암호화된 파일 복호화 (검증용, 디스크에 저장하지 않음)

    Args:
        enc_path: .enc 파일 경로

    Returns:
        복호화된 소스 코드 (실패 시 None)
    """
    if not enc_path.exists():
        print(f"[ERROR] 파일 없음: {enc_path}")
        return None

    try:
        # 1. Base64 디코딩
        with open(enc_path, 'rb') as f:
            encoded = f.read()
        combined = base64.b64decode(encoded)

        # 2. IV와 암호문 분리
        iv = combined[:16]
        encrypted = combined[16:]

        # 3. AES 복호화
        key = get_encryption_key()
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_data = cipher.decrypt(encrypted)
        compressed = unpad(padded_data, AES.block_size)

        # 4. gzip 압축 해제
        source_code = gzip.decompress(compressed).decode('utf-8')

        return source_code

    except Exception as e:
        print(f"[ERROR] 복호화 실패 ({enc_path}): {e}")
        return None


def encrypt_all() -> tuple[int, int]:
    """
    전체 핵심 모듈 암호화

    Returns:
        (성공 수, 실패 수)
    """
    print(f"\n{'='*60}")
    print("핵심 모듈 암호화 시작")
    print(f"{'='*60}")
    print(f"대상 모듈: {len(CORE_MODULES)}개")
    print(f"출력 경로: {ENCRYPTED_DIR}")
    print(f"{'='*60}\n")

    success = 0
    failed = 0

    for module_path in CORE_MODULES:
        source_path = PROJECT_ROOT / module_path
        if encrypt_file(source_path):
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"완료: 성공 {success}개, 실패 {failed}개")
    print(f"{'='*60}")

    return success, failed


def verify_all() -> tuple[int, int]:
    """
    모든 .enc 파일 복호화 검증

    Returns:
        (성공 수, 실패 수)
    """
    print(f"\n{'='*60}")
    print("암호화 검증 시작")
    print(f"{'='*60}\n")

    if not ENCRYPTED_DIR.exists():
        print("[ERROR] encrypted_modules/ 폴더 없음")
        return 0, 0

    enc_files = list(ENCRYPTED_DIR.glob("*.enc"))
    if not enc_files:
        print("[WARNING] .enc 파일 없음")
        return 0, 0

    success = 0
    failed = 0

    for enc_path in enc_files:
        source = decrypt_file(enc_path)
        if source is not None:
            # 간단한 검증: Python 구문 체크
            try:
                compile(source, enc_path.name, 'exec')
                print(f"[OK] {enc_path.name}: 복호화 성공 ({len(source):,} bytes)")
                success += 1
            except SyntaxError as e:
                print(f"[ERROR] {enc_path.name}: 구문 오류 - {e}")
                failed += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"검증 완료: 성공 {success}개, 실패 {failed}개")
    print(f"{'='*60}")

    return success, failed


def main():
    parser = argparse.ArgumentParser(
        description="핵심 모듈 암호화 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python tools/encrypt_module.py core/strategy_core.py   # 단일 파일 암호화
  python tools/encrypt_module.py --all                    # 전체 모듈 암호화
  python tools/encrypt_module.py --verify                 # 암호화 검증
  python tools/encrypt_module.py --list                   # 대상 모듈 목록
        """
    )

    parser.add_argument('file', nargs='?', help='암호화할 .py 파일 경로')
    parser.add_argument('--all', action='store_true', help='전체 핵심 모듈 암호화')
    parser.add_argument('--verify', action='store_true', help='암호화 검증')
    parser.add_argument('--list', action='store_true', help='대상 모듈 목록 표시')

    args = parser.parse_args()

    # 모듈 목록 표시
    if args.list:
        print("\n보호 대상 핵심 모듈:")
        print("-" * 40)
        for i, module in enumerate(CORE_MODULES, 1):
            exists = (PROJECT_ROOT / module).exists()
            status = "OK" if exists else "없음"
            print(f"  {i:2}. {module} [{status}]")
        print("-" * 40)
        return

    # 전체 암호화
    if args.all:
        success, failed = encrypt_all()
        sys.exit(0 if failed == 0 else 1)

    # 검증
    if args.verify:
        success, failed = verify_all()
        sys.exit(0 if failed == 0 else 1)

    # 단일 파일 암호화
    if args.file:
        source_path = Path(args.file)
        if not source_path.is_absolute():
            source_path = PROJECT_ROOT / source_path

        success = encrypt_file(source_path)
        sys.exit(0 if success else 1)

    # 인자 없으면 도움말
    parser.print_help()


if __name__ == "__main__":
    main()
