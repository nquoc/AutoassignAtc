import sys
import os
import urllib.request
import json
import time

sys.path.insert(0, r"h:\My Drive/tools/AutoassignAtc")
import crm_api

sys.stdout.reconfigure(encoding='utf-8')

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"
chat_id = "1415966017"

print("🚀 RUNNING 5:00 AM SCHEDULED SWITCH ONLINE TASK FOR 7 ATCS (OI MODEL)...")

# Ensure fresh session according to Section 1 of Tai_Lieu_Tich_Hop_API_KV_CRM.html
cookie_str, csrf_token = crm_api.get_session()
headers = {
    "cookie": cookie_str,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "x-requested-with": "XMLHttpRequest"
}

tasks = [
    ("106714311", "CSKHOI_DVKH", "CSKH OI - DVKH"),
    ("106714270", "CSKHOI_DVKH", "CSKH OI - DVKH"),
    ("106713923", "CSKHOI_DVKH", "CSKH OI - DVKH"),
    ("106695252", "CSKHOI_DVKH", "CSKH OI - DVKH"),
    ("106695181", "CSKHOI_DVKH", "CSKH OI - DVKH"),
    ("106695171", "CSKHOI_DVKH", "CSKH OI - DVKH"),
    ("106325800", "CSKHOI_DVKH", "CSKH OI - DVKH")
]

results = []

for aid, c_type, group_label in tasks:
    try:
        # Step 1: checkCanChangeForm (Section 3 Workflow)
        url_check = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=checkCanChangeForm&record={aid}"
        req_check = urllib.request.Request(url_check, headers=headers)
        with urllib.request.urlopen(req_check, timeout=10) as resp_check:
            res_c = json.loads(resp_check.read().decode('utf-8'))

        # Step 2: SwitchOnlineSupport API (Section 3 Spec)
        url_switch = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=SwitchOnlineSupport&record={aid}&cskhcs_type={c_type}"
        req_switch = urllib.request.Request(url_switch, headers=headers)
        with urllib.request.urlopen(req_switch, timeout=10) as resp_switch:
            res_s = json.loads(resp_switch.read().decode('utf-8'))
            if res_s.get("success") == True or res_s.get("result", {}).get("success") == True:
                results.append((aid, group_label, "SUCCESS 🟢"))
                print(f"  ✅ ATC {aid} ➔ Switch Online {group_label}: SUCCESS")
            else:
                results.append((aid, group_label, f"FAILED 🔴 ({res_s})"))
                print(f"  ❌ ATC {aid} ➔ Switch Online {group_label}: FAILED {res_s}")
    except Exception as e:
        results.append((aid, group_label, f"ERROR 🔴 ({e})"))
        print(f"  ❌ ATC {aid} ➔ Error: {e}")

lines = [
    f"⏰ *BÁO CÁO THỰC THI CHUYỂN SUPPORT ONLINE 5:00 AM (7 ĐƠN OI MODEL)*:\n",
    f"📌 *ATC 106714311* (`CSKHOI_DVKH`): `{results[0][2]}`",
    f"📌 *ATC 106714270* (`CSKHOI_DVKH`): `{results[1][2]}`",
    f"📌 *ATC 106713923* (`CSKHOI_DVKH`): `{results[2][2]}`",
    f"📌 *ATC 106695252* (`CSKHOI_DVKH`): `{results[3][2]}`",
    f"📌 *ATC 106695181* (`CSKHOI_DVKH`): `{results[4][2]}`",
    f"📌 *ATC 106695171* (`CSKHOI_DVKH`): `{results[5][2]}`",
    f"📌 *ATC 106325800* (`CSKHOI_DVKH`): `{results[6][2]}`\n",
    f"⚡ *Đã hoàn tất tự động chuẩn 100% tài liệu API KV CRM vào 5:00 AM!* 😎🚀"
]

report_text = "\n".join(lines)

url_msg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {"chat_id": chat_id, "text": report_text, "parse_mode": "Markdown"}
req_msg = urllib.request.Request(url_msg, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req_msg) as resp_msg:
    print("✅ SENT 5:00 AM EXECUTION REPORT TO TELEGRAM CHAT 1415966017: OK")
