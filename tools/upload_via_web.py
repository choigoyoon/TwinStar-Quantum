"""
웹 업로드 인터페이스를 통한 모듈 업로드

서버의 upload_module.php 엔드포인트를 사용하여 .enc 파일 업로드

사용법:
    python tools/upload_via_web.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests

# 설정
UPLOAD_URL = "https://youngstreet.co.kr/api/modules/upload_module.php"
LOCAL_ENC_DIR = PROJECT_ROOT / "encrypted_modules"

# 업로드 키 (서버의 upload_module.php에 설정된 키)
UPLOAD_KEY = "TwinStar2026SecureUpload"


def upload_modules() -> bool:
    """모든 .enc 파일 업로드"""

    enc_files = list(LOCAL_ENC_DIR.glob("*.enc"))

    if not enc_files:
        print(f"[X] {LOCAL_ENC_DIR}에 .enc 파일이 없습니다.")
        return False

    print(f"업로드할 파일: {len(enc_files)}개")
    for f in enc_files:
        print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

    print(f"\n업로드 URL: {UPLOAD_URL}")
    print("-" * 50)

    uploaded = 0
    failed = []

    for enc_file in enc_files:
        module_name = enc_file.stem  # .enc 제거

        try:
            with open(enc_file, 'rb') as f:
                files = {'module_file': (enc_file.name, f, 'application/octet-stream')}
                data = {
                    'upload_key': UPLOAD_KEY,
                    'module_name': module_name
                }

                response = requests.post(
                    UPLOAD_URL,
                    files=files,
                    data=data,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print(f"[OK] {enc_file.name}")
                        uploaded += 1
                    else:
                        print(f"[X] {enc_file.name}: {result.get('error', 'Unknown error')}")
                        failed.append(enc_file.name)
                else:
                    print(f"[X] {enc_file.name}: HTTP {response.status_code}")
                    print(f"    {response.text[:200]}")
                    failed.append(enc_file.name)

        except Exception as e:
            print(f"[X] {enc_file.name}: {e}")
            failed.append(enc_file.name)

    # 결과 요약
    print("-" * 50)
    print(f"업로드 완료: {uploaded}/{len(enc_files)}")

    if failed:
        print(f"실패: {failed}")
        return False

    return True


def main():
    print("=" * 50)
    print("  TwinStar-Quantum 웹 업로드")
    print("=" * 50)

    success = upload_modules()

    if success:
        print("\n[OK] 모든 파일 업로드 완료!")
        print("\n다음 단계:")
        print("  1. 서버에서 업로드 인터페이스 비활성화:")
        print("     php toggle_upload.php off")
        print("\n  2. 로컬에서 통합 테스트:")
        print("     python tools/test_server_integration.py")
    else:
        print("\n[X] 일부 파일 업로드 실패")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
