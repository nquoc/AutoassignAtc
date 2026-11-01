@echo off
title Kiem Tra Trang Thai Bot
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_status.ps1"
echo.
pause
