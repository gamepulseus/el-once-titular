@echo off
title GamePulse Telegram Auto-Publisher
cd /d "%~dp0"
echo ==================================================
echo   ⚡ Starting GamePulse Telegram Auto-Publisher ⚡
echo   Channels: @GamePulseES & @GamePulseUS
echo ==================================================
echo.
python main.py
pause
