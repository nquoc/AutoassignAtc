$procs = Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like "*\bot.py*" -or $_.CommandLine -like "* bot.py*") -and $_.CommandLine -notlike "*zalo*" }
if ($procs) {
    Write-Host "========================================================" -ForegroundColor Cyan
    Write-Host "  [OK] BOT DANG CHAY NGAM BINH THUONG!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Cyan
    $procs | Select-Object ProcessId, Name, CommandLine | Format-Table -AutoSize
} else {
    Write-Host "========================================================" -ForegroundColor Yellow
    Write-Host "  [!] BOT HIEN TAI KHONG CHAY!" -ForegroundColor Red
    Write-Host "========================================================" -ForegroundColor Yellow
    Write-Host "De bat bot chay ngam, hay nhap dup vao file: Chay_Bot_Ngam.vbs" -ForegroundColor Gray
}
