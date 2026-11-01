@echo off
title KiotViet CRM to Google Sheets Sync Hub
cd /d "%~dp0"

echo ======================================================================
echo    KHOI CHAY KIOTVIET CRM TO GOOGLE SHEETS SYNC HUB
echo ======================================================================

if exist "KiotViet_CRM_Sync.exe" (
    echo [1/1] Dang khoi chay qua file KiotViet_CRM_Sync.exe...
    start "" "KiotViet_CRM_Sync.exe"
    exit /b 0
)

echo Khong tim thay KiotViet_CRM_Sync.exe, chuyen sang chay qua Python...
set PYTHONUTF8=1
python gui_crm_tool.py
if %errorlevel% neq 0 (
    echo.
    echo Co loi xay ra khi chay qua Python!
    echo Neu may chua cai thu vien, vui long chay file: Cai_Dat_Moi_Truong_Python.bat
    pause
)
