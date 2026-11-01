@echo off
title Cai dat moi truong Python
cd /d "%~dp0"

echo ======================================================================
echo    CAI DAT THU VIEN CHO TOOL KIOTVIET CRM SYNC (PYTHON)
echo ======================================================================
echo.
echo Dang kiem tra Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] May ban chua cai Python!
    echo Vui long chay truc tiep file: KiotViet_CRM_Sync.exe (Khong can cai Python)
    echo Hoac cai dat Python 3.10+ tai: https://www.python.org/downloads/ (nho tich Add Python to PATH)
    pause
    exit /b 1
)

echo [+] Da tim thay Python. Dang cai dat cac thu vien can thiet...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [!] Co loi khi cai dat thu vien. Vui long kiem tra ket noi mang.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo [OK] DA CAI DAT XONG TAT CA THU VIEN!
echo Ban co the chay file: Chay_Tool.bat de su dung.
echo ======================================================================
pause
