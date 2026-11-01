import sys
import os
import urllib.request
import json
import subprocess
import time

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"

sys.stdout.reconfigure(encoding='utf-8')

print("🧹 KILLING ALL PREVIOUS DUPLICATE TELEGRAM BOT PROCESSES IN WINDOWS...", flush=True)

# Kill any running python script matching tele_ or agent_bridge
kill_cmd = (
    'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*tele_*" -or $_.CommandLine -like "*super_fast_agent_bridge*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }'
)

try:
    subprocess.run(["powershell", "-Command", kill_cmd], capture_output=True, text=True)
    print("  ✅ Killed all existing Telegram bot processes in Windows Task Manager!", flush=True)
except Exception as e:
    print(f"  ⚠️ Process kill warning: {e}", flush=True)

time.sleep(1)

print("🧹 CLEARING TELEGRAM WEBHOOK & RESETTING CONFLICTS...", flush=True)
try:
    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True"
    req = urllib.request.Request(del_url)
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f"  ✅ Webhook Delete Result: {res}", flush=True)
except Exception as e:
    print(f"  ⚠️ Webhook clean error: {e}", flush=True)

print("✨ RESET COMPLETE. READY FOR SINGLE DAEMON LAUNCH!", flush=True)
