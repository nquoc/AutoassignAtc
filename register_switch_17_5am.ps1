$action = New-ScheduledTaskAction -Execute 'C:\Users\quoc\AppData\Local\Programs\Python\Python311\python.exe' -Argument '"h:\My Drive\tools\AutoassignAtc\scheduled_switch_17_online_5am.py"' -WorkingDirectory 'h:\My Drive\tools\AutoassignAtc'
$trigger = New-ScheduledTaskTrigger -Daily -At '05:00'
$settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'KiotViet_Switch_17_Online_5AM' -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Task KiotViet_Switch_17_Online_5AM registered successfully."
