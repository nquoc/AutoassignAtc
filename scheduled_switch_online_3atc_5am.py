import sys
import os
import urllib.request
import json
import time
import datetime

sys.path.insert(0, r"h:\My Drive\tools\AutoassignAtc")
import crm_api

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"
chat_id = "1415966017"

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduled_switch_online_3atc_5am.log")

def log(msg):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now_str}] {msg}"
    print(line)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

log("🚀 STARTING 5:00 AM SCHEDULED SWITCH ONLINE FOR 3 ATCS (CSKH OI)...")

cookie_str, csrf_token = crm_api.get_session()
headers = {
    "cookie": cookie_str,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-requested-with": "XMLHttpRequest"
}

tasks = [
    ("107672641", "CSKHOI_DVKH", "CSKH OI - DVKH", "500668446", "thư cà phê (0974983044)"),
    ("105251881", "CSKHOI_DVKH", "CSKH OI - DVKH", "500420219", "N3 Anh Khoa Cafe Ola (ument)"),
    ("105251566", "CSKHOI_DVKH", "CSKH OI - DVKH", "500524977", "Nguyễn Chí Ân (hkdnbphuong)")
]

results = []

for aid, c_type, group_label, ret_id, store_label in tasks:
    try:
        # Step 1: checkCanChangeForm (Section 3 Workflow)
        url_check = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=checkCanChangeForm&record={aid}"
        req_check = urllib.request.Request(url_check, headers=headers)
        with urllib.request.urlopen(req_check, timeout=15) as resp_check:
            res_c = json.loads(resp_check.read().decode('utf-8'))
        log(f"Check checkCanChangeForm ATC {aid}: {res_c}")

        # Step 2: SwitchOnlineSupport API (Section 3 Spec)
        url_switch = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=SwitchOnlineSupport&record={aid}&cskhcs_type={c_type}"
        req_switch = urllib.request.Request(url_switch, headers=headers)
        with urllib.request.urlopen(req_switch, timeout=15) as resp_switch:
            res_s = json.loads(resp_switch.read().decode('utf-8'))
            if res_s.get("success") is True or res_s.get("result", {}).get("success") is True:
                results.append((aid, ret_id, store_label, group_label, "SUCCESS 🟢", res_s))
                log(f"  ✅ ATC {aid} ({ret_id} - {store_label}) ➔ Switch Online {group_label}: SUCCESS")
            else:
                results.append((aid, ret_id, store_label, group_label, f"FAILED 🔴 ({res_s})", res_s))
                log(f"  ❌ ATC {aid} ({ret_id} - {store_label}) ➔ Switch Online {group_label}: FAILED {res_s}")
    except Exception as e:
        results.append((aid, ret_id, store_label, group_label, f"ERROR 🔴 ({e})", str(e)))
        log(f"  ❌ ATC {aid} ({ret_id} - {store_label}) ➔ Error: {e}")

# Telegram report
lines = [
    "⏰ *BÁO CÁO THỰC THI CHUYỂN SUPPORT ONLINE 5:00 AM (3 ATC)*:\n"
]
for aid, ret_id, store_label, group_label, status_str, _ in results:
    lines.append(f"📌 *ATC {aid}* (Retailer `{ret_id}` - {store_label}): `{status_str}` ({group_label})")

lines.append("\n⚡ *Đã hoàn tất tự động chuyển CSKH OI theo lịch hẹn 5:00 AM!* 😎🚀")

report_text = "\n".join(lines)

try:
    url_msg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": report_text, "parse_mode": "Markdown"}
    req_msg = urllib.request.Request(url_msg, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req_msg, timeout=10) as resp_msg:
        log("✅ SENT 5:00 AM EXECUTION REPORT TO TELEGRAM CHAT 1415966017: OK")
except Exception as ex_tele:
    log(f"⚠️ Failed to send Telegram report: {ex_tele}")

log("🎉 COMPLETED 5:00 AM SWITCH ONLINE TASK.")
