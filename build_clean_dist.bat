@echo off
REM StarU 클린 배포 EXE 빌드 스크립트
REM API 키, 수집 데이터, 사용자 설정 제외

echo ========================================
echo StarU Clean Distribution Builder
echo ========================================
echo.

REM 기존 빌드 정리
echo [1/4] 기존 빌드 정리...
if exist "dist\StarU_Bot_Clean" rmdir /s /q "dist\StarU_Bot_Clean"
if exist "build\StarU_Bot_Clean" rmdir /s /q "build\StarU_Bot_Clean"

REM PyInstaller 실행
echo [2/4] PyInstaller 빌드 중...
pyinstaller --clean --noconfirm staru_clean.spec

REM 빈 폴더 구조 생성
echo [3/4] 사용자 폴더 구조 생성...
mkdir "dist\StarU_Bot\config" 2>nul
mkdir "dist\StarU_Bot\config\presets" 2>nul
mkdir "dist\StarU_Bot\data\cache" 2>nul
mkdir "dist\StarU_Bot\user\exchanges" 2>nul
mkdir "dist\StarU_Bot\user\backup" 2>nul
mkdir "dist\StarU_Bot\logs" 2>nul

REM 템플릿 복사
echo [4/4] 템플릿 파일 복사...
copy "api_key_config_template.json" "dist\StarU_Bot\config\api_keys_template.json" >nul

echo.
echo ========================================
echo 빌드 완료!
echo ========================================
echo.
echo 배포 폴더: dist\StarU_Bot
echo.
echo 포함된 것:
echo   - 실행 파일 (StarU_Bot.exe)
echo   - GUI 모듈
echo   - 핵심 전략 모듈
echo.
echo 제외된 것:
echo   - API 키 (사용자가 직접 입력)
echo   - 수집 데이터 (사용자가 직접 다운로드)
echo   - 로그 파일
echo   - 개발용 파일
echo.
pause
