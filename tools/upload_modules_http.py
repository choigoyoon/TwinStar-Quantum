"""
HTTP를 통한 모듈 업로드 스크립트

서버에 임시 업로드 엔드포인트가 있을 경우 사용
또는 FTP 정보를 사용하여 업로드

사용법:
    python tools/upload_modules_http.py
"""

import os
import sys
import ftplib
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 서버 설정
FTP_HOST = "youngstreet.co.kr"
FTP_USER = "hakiosae"
REMOTE_DIR = "/public_html/secure_modules"

# 로컬 설정
LOCAL_ENC_DIR = PROJECT_ROOT / "encrypted_modules"


def get_ftp_password():
    """FTP 비밀번호 입력 받기"""
    import getpass
    return getpass.getpass(f"FTP 비밀번호 ({FTP_USER}@{FTP_HOST}): ")


def upload_with_ftp(password: str) -> bool:
    """FTP로 파일 업로드"""

    # .enc 파일 목록
    enc_files = list(LOCAL_ENC_DIR.glob("*.enc"))

    if not enc_files:
        print(f"[X] {LOCAL_ENC_DIR}에 .enc 파일이 없습니다.")
        return False

    print(f"\n업로드할 파일: {len(enc_files)}개")
    for f in enc_files:
        print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

    print(f"\nFTP 서버: {FTP_USER}@{FTP_HOST}")
    print(f"원격 경로: {REMOTE_DIR}")

    try:
        # FTP 연결
        print("\n[1/3] FTP 연결 중...")
        ftp = ftplib.FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, password)
        print(f"  [OK] FTP 연결 성공")
        print(f"  현재 디렉토리: {ftp.pwd()}")

        # 원격 디렉토리 이동
        print(f"\n[2/3] 디렉토리 이동...")
        try:
            ftp.cwd(REMOTE_DIR)
            print(f"  [OK] 디렉토리 이동: {REMOTE_DIR}")
        except ftplib.error_perm:
            # 디렉토리 생성 시도
            print(f"  디렉토리 생성 중: {REMOTE_DIR}")
            ftp.mkd(REMOTE_DIR)
            ftp.cwd(REMOTE_DIR)
            print(f"  [OK] 디렉토리 생성 및 이동 완료")

        # 파일 업로드
        print(f"\n[3/3] 파일 업로드 중...")
        uploaded = 0
        failed = []

        for local_file in enc_files:
            try:
                with open(local_file, 'rb') as f:
                    ftp.storbinary(f'STOR {local_file.name}', f)
                print(f"  [OK] {local_file.name}")
                uploaded += 1
            except Exception as e:
                print(f"  [X] {local_file.name}: {e}")
                failed.append(local_file.name)

        # 업로드된 파일 확인
        print(f"\n원격 파일 목록:")
        files = ftp.nlst()
        for f in files:
            if f.endswith('.enc'):
                print(f"  - {f}")

        # FTP 종료
        ftp.quit()

        # 결과 요약
        print(f"\n{'='*50}")
        print(f"업로드 완료: {uploaded}/{len(enc_files)} 파일")
        if failed:
            print(f"실패: {failed}")

        return uploaded == len(enc_files)

    except ftplib.error_perm as e:
        print(f"\n[X] FTP 권한 오류: {e}")
        return False
    except Exception as e:
        print(f"\n[X] FTP 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 함수"""
    print("=" * 50)
    print("  TwinStar-Quantum 모듈 FTP 업로드")
    print("=" * 50)

    # 비밀번호 입력
    password = get_ftp_password()

    if not password:
        print("[X] 비밀번호가 필요합니다.")
        return False

    # 업로드 실행
    success = upload_with_ftp(password)

    if success:
        print("\n[OK] 모든 파일 업로드 완료!")
        print("\n다음 단계:")
        print("  1. 서버에서 파일 권한 설정:")
        print("     chmod 600 /home/hakiosae/web/youngstreet.co.kr/public_html/secure_modules/*.enc")
        print("\n  2. 서버에서 체크섬 업데이트:")
        print("     cd /home/hakiosae/web/youngstreet.co.kr/public_html/api/modules")
        print("     php update_module_checksums.php")
        print("\n  3. 로컬에서 통합 테스트:")
        print("     python tools/test_server_integration.py")
    else:
        print("\n[X] 업로드 실패. 위 오류를 확인하세요.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
