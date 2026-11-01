@echo off
chcp 65001 > nul
echo ========================================================
echo   Đang cài đặt thư viện cần thiết cho Bot AutoassignAtc
echo ========================================================
python -m pip install -r requirements.txt
echo.
echo ========================================================
echo   Đã cài đặt xong! Bạn có thể chạy file Chay_Bot.bat
echo ========================================================
pause
