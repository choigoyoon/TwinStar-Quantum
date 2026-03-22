@echo off
chcp 65001
echo ==========================================
echo       StarU Trading Bot Builder
echo ==========================================

echo 1. 기존 빌드 정리 중...
rmdir /s /q build
rmdir /s /q dist

echo 2. GUI Asset 폴더 확인...
if not exist "GUI\assets" mkdir "GUI\assets"

echo 3. EXE 빌드 시작...
pyinstaller staru.spec --clean --noconfirm

echo ==========================================
if exist "dist\StarU_Bot\StarU_Bot.exe" (
    echo ✅ 빌드 성공!
    echo 파일 위치: dist\StarU_Bot\StarU_Bot.exe
    start dist\StarU_Bot
) else (
    echo ❌ 빌드 실패. 에러 로그를 확인하세요.
    pause
)
echo ==========================================
pause
