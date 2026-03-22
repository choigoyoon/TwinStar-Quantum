@echo off
REM Bybit Bot Background Runner
REM 백그라운드로 봇을 실행합니다

echo ====================================
echo Bybit Trading Bot
echo Starting in background mode...
echo ====================================
echo.

REM Start bot in background (minimized)
start /min "" "dist\BybitBot.exe"

echo Bot started!
echo.
echo To stop: Open Task Manager and end "BybitBot.exe"
echo Log file: bot_bybit.log
echo.
pause
