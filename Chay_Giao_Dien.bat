@echo off
title KiotViet CRM to Google Sheets GUI
cd /d "%~dp0"
set PYTHONUTF8=1
echo ======================================================================
echo    KHOI CHAY GIAO DIEN DONG BO KIOTVIET CRM RA GOOGLE SHEETS
echo ======================================================================
python gui_crm_tool.py
if %errorlevel% neq 0 (
    echo.
    echo Co loi xay ra khi chay ung dung!
    pause
)
