"""
서버에 암호화된 모듈 업로드 스크립트

SFTP를 사용하여 encrypted_modules/*.enc 파일을
서버의 /home/hakiosae/web/youngstreet.co.kr/public_html/secure_modules/에 업로드

사용법:
    python tools/upload_modules_to_server.py

필요 패키지:
    pip install paramiko
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import paramiko
except ImportError:
    print("paramiko 설치 필요: pip install paramiko")
    sys.exit(1)

# 서버 설정
SERVER_HOST = "youngstreet.co.kr"
SERVER_USER = "hakiosae"
SERVER_PORT = 22
REMOTE_DIR = "/home/hakiosae/web/youngstreet.co.kr/public_html/secure_modules"

# 로컬 설정
LOCAL_ENC_DIR = PROJECT_ROOT / "encrypted_modules"


def get_ssh_password():
    """SSH 비밀번호 입력 받기"""
    import getpass
    return getpass.getpass(f"SSH 비밀번호 ({SERVER_USER}@{SERVER_HOST}): ")


def upload_with_sftp(password: str) -> bool:
    """SFTP로 파일 업로드"""

    # .enc 파일 목록
    enc_files = list(LOCAL_ENC_DIR.glob("*.enc"))

    if not enc_files:
        print(f"[X] {LOCAL_ENC_DIR}에 .enc 파일이 없습니다.")
        return False

    print(f"\n업로드할 파일: {len(enc_files)}개")
    for f in enc_files:
        print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

    print(f"\n서버: {SERVER_USER}@{SERVER_HOST}")
    print(f"원격 경로: {REMOTE_DIR}")

    try:
        # SSH 연결
        print("\n[1/4] SSH 연결 중...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=SERVER_HOST,
            port=SERVER_PORT,
            username=SERVER_USER,
            password=password,
            timeout=30
        )
        print("  [OK] SSH 연결 성공")

        # SFTP 세션 열기
        print("\n[2/4] SFTP 세션 열기...")
        sftp = ssh.open_sftp()
        print("  [OK] SFTP 세션 열림")

        # 원격 디렉토리 확인/생성
        print(f"\n[3/4] 원격 디렉토리 확인...")
        try:
            sftp.stat(REMOTE_DIR)
            print(f"  [OK] 디렉토리 존재: {REMOTE_DIR}")
        except FileNotFoundError:
            print(f"  디렉토리 생성 중: {REMOTE_DIR}")
            sftp.mkdir(REMOTE_DIR)
            print(f"  [OK] 디렉토리 생성됨")

        # 파일 업로드
        print(f"\n[4/4] 파일 업로드 중...")
        uploaded = 0
        failed = []

        for local_file in enc_files:
            remote_path = f"{REMOTE_DIR}/{local_file.name}"
            try:
                sftp.put(str(local_file), remote_path)
                # 권한 설정 (600 = owner read/write only)
                sftp.chmod(remote_path, 0o600)
                print(f"  [OK] {local_file.name} -> {remote_path}")
                uploaded += 1
            except Exception as e:
                print(f"  [X] {local_file.name}: {e}")
                failed.append(local_file.name)

        # 결과 요약
        print(f"\n{'='*50}")
        print(f"업로드 완료: {uploaded}/{len(enc_files)} 파일")
        if failed:
            print(f"실패: {failed}")

        # SFTP/SSH 종료
        sftp.close()
        ssh.close()

        return uploaded == len(enc_files)

    except paramiko.AuthenticationException:
        print("\n[X] 인증 실패: 비밀번호를 확인하세요.")
        return False
    except paramiko.SSHException as e:
        print(f"\n[X] SSH 오류: {e}")
        return False
    except Exception as e:
        print(f"\n[X] 오류: {e}")
        return False


def main():
    """메인 함수"""
    print("=" * 50)
    print("  TwinStar-Quantum 모듈 서버 업로드")
    print("=" * 50)

    # 비밀번호 입력
    password = get_ssh_password()

    if not password:
        print("[X] 비밀번호가 필요합니다.")
        return False

    # 업로드 실행
    success = upload_with_sftp(password)

    if success:
        print("\n[OK] 모든 파일 업로드 완료!")
        print("\n다음 단계:")
        print("  1. 서버에서 체크섬 업데이트:")
        print("     cd /home/hakiosae/web/youngstreet.co.kr/public_html/api/modules")
        print("     php update_module_checksums.php")
        print("\n  2. 로컬에서 통합 테스트:")
        print("     python tools/test_server_integration.py")
    else:
        print("\n[X] 업로드 실패. 위 오류를 확인하세요.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
