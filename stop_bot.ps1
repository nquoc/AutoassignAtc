$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*bot.py*" }
if ($procs) {
    foreach ($p in $procs) {
        Write-Host "Dang dung tien trinh PID: $($p.ProcessId)" -ForegroundColor Yellow
        Stop-Process -Id $p.ProcessId -Force
    }
    Write-Host "[OK] Da dung Bot thanh cong!" -ForegroundColor Green
} else {
    Write-Host "Khong tim thay tien trinh bot.py nao dang chay." -ForegroundColor Cyan
}
