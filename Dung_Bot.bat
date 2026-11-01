@echo off
title Dung Bot Autoassign
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_bot.ps1"
echo.
pause
