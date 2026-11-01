@echo off
powershell -Command "Remove-Item '$env:LOCALAPPDATA\Checkvar_Chrome_Profile\Singleton*' -Force -ErrorAction SilentlyContinue"
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%LOCALAPPDATA%\Checkvar_Chrome_Profile" "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname=16309"
