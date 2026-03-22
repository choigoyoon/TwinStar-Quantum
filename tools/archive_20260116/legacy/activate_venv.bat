@echo off
chcp 65001 >nul
cls

echo ============================================================
echo TwinStar-Quantum 가상 환경 활성화
echo ============================================================
echo.

REM 가상 환경 존재 확인
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] 가상 환경을 찾을 수 없습니다.
    echo.
    echo 가상 환경을 먼저 생성해주세요:
    echo   py -m venv venv
    echo   venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM 가상 환경 활성화
call venv\Scripts\activate.bat

REM 환경 확인 스크립트 실행
if exist "check_env.py" (
    python check_env.py
) else (
    echo [OK] 가상 환경이 활성화되었습니다.
    echo.
    echo Python 버전:
    python --version
    echo.
)

echo.
echo ============================================================
echo 사용 가능한 명령어:
echo ============================================================
echo   python main.py              - 메인 프로그램 실행
echo   python check_env.py         - 환경 확인
echo   pip list                    - 설치된 패키지 목록
echo   pip install [package]       - 패키지 설치
echo   deactivate                  - 가상 환경 종료
echo ============================================================
echo.
