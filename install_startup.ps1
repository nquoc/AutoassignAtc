$ws = New-Object -ComObject WScript.Shell
$startup = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
$shortcut = $ws.CreateShortcut([System.IO.Path]::Combine($startup, "AutoassignBot.lnk"))
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$shortcut.TargetPath = [System.IO.Path]::Combine($scriptDir, "Chay_Bot_Ngam.vbs")
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = "shell32.dll,44"
$shortcut.Save()

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  [OK] CAI DAT TU KHOI DONG CUNG WINDOWS THANH CONG!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Loi tat da duoc tao tai:" -ForegroundColor Gray
Write-Host "-> $($shortcut.FullName)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Tu gio moi khi mo may tinh len, Bot se tu dong chay ngam 24/7." -ForegroundColor Green
Write-Host "Tat Antigravity bot van hoat dong binh thuong!" -ForegroundColor Green
