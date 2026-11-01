import sys
import os
import urllib.request
import json
import time

sys.path.insert(0, r"h:\My Drive\tools\AutoassignAtc")
import crm_api

sys.stdout.reconfigure(encoding='utf-8')

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"
chat_id = "1415966017"

print("🚀 RUNNING 5:00 AM SCHEDULED SWITCH ONLINE TASK FOR 17 ATCS (CSKH OI)...")

# Ensure fresh session
cookie_str, csrf_token = crm_api.get_session()
if not cookie_str:
    try:
        from extract_crm_cookie import extract_kiotviet_cookies
        cookie_str = extract_kiotviet_cookies()
    except Exception:
        pass
if not cookie_str:
    cookie_str, csrf_token = crm_api.acquire_session_via_selenium()

headers = {
    "cookie": cookie_str or "",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-requested-with": "XMLHttpRequest"
}

tasks = [
    "108771949", "108754148", "108754130", "108739942", "108739695",
    "108739440", "108723354", "108723352", "108722899", "108682836",
    "108682719", "108682682", "108594606", "108593659", "108483800",
    "108483670", "108451622"
]

results = []
c_type = "CSKHOI_DVKH"
group_label = "CSKH OI - DVKH"

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "switch_17_online_5am.log")
with open(log_file, "a", encoding="utf-8") as f_log:
    f_log.write(f"\n=== BẮT ĐẦU CHẠY LÚC {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")

for idx, aid in enumerate(tasks, start=1):
    try:
        # Step 1: checkCanChangeForm
        url_check = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=checkCanChangeForm&record={aid}"
        req_check = urllib.request.Request(url_check, headers=headers)
        with urllib.request.urlopen(req_check, timeout=10) as resp_check:
            res_c = json.loads(resp_check.read().decode('utf-8'))

        # Step 2: SwitchOnlineSupport
        url_switch = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=SwitchOnlineSupport&record={aid}&cskhcs_type={c_type}"
        req_switch = urllib.request.Request(url_switch, headers=headers)
        with urllib.request.urlopen(req_switch, timeout=10) as resp_switch:
            res_s = json.loads(resp_switch.read().decode('utf-8'))
            if res_s.get("success") is True or res_s.get("result", {}).get("success") is True:
                results.append((aid, group_label, "SUCCESS 🟢"))
                log_line = f"[{idx}/17] ✅ ATC {aid} ➔ Switch Online {group_label}: SUCCESS\n"
            else:
                results.append((aid, group_label, f"FAILED 🔴 ({res_s})"))
                log_line = f"[{idx}/17] ❌ ATC {aid} ➔ Switch Online {group_label}: FAILED {res_s}\n"
    except Exception as e:
        results.append((aid, group_label, f"ERROR 🔴 ({e})"))
        log_line = f"[{idx}/17] ❌ ATC {aid} ➔ Error: {e}\n"

    print(log_line.strip())
    with open(log_file, "a", encoding="utf-8") as f_log:
        f_log.write(log_line)

# Report
success_count = sum(1 for r in results if "SUCCESS" in r[2])
lines = [
    f"⏰ *BÁO CÁO THỰC THI CHUYỂN ONLINE CSKH OI LÚC 5:00 AM*:",
    f"🎯 *Kết quả*: Thành công `{success_count}/17` ATC\n"
]
for idx, (aid, grp, st) in enumerate(results, start=1):
    lines.append(f"{idx}. ATC `{aid}` ➔ `{st}`")

lines.append(f"\n⚡ *Đã hoàn tất tự động vào lúc 5:00 AM!* 🚀")
report_text = "\n".join(lines)

# Send Telegram
try:
    url_msg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": report_text, "parse_mode": "Markdown"}
    req_msg = urllib.request.Request(url_msg, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_msg, timeout=10) as resp_msg:
        print("✅ SENT 5:00 AM EXECUTION REPORT TO TELEGRAM: OK")
except Exception as e:
    print(f"⚠️ Telegram notification error: {e}")
