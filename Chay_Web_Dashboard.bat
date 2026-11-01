@echo off
chcp 65001 >nul
title KiotViet CRM - Web Dashboard
set PYTHONUTF8=1
cd /d "%~dp0"
echo =====================================================================
echo    KIOTVIET CRM - KHOI DONG WEB DASHBOARD PHAN TICH NHAN SU
echo =====================================================================
echo.
echo [1/2] Dang kiem tra moi truong Python...
python -c "import sys; print('Python version: ' + sys.version)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren may cua ban!
    pause
    exit /b
)

echo [2/2] Dang khoi dong Web Server tai http://localhost:5050...
echo Trinh duyet se tu dong duoc mo sau giay lat.
echo.
python server_dashboard.py
if %errorlevel% neq 0 (
    echo.
    echo Co loi xay ra khi chay Web Server!
    pause
)
