import sys
import os
import json
import urllib.request

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"
chat_id = sys.argv[1] if len(sys.argv) > 1 else "1415966017"
reply_text = sys.argv[2] if len(sys.argv) > 2 else "Dạ em nghe đây ạ!"

sys.stdout.reconfigure(encoding='utf-8')

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": reply_text,
    "parse_mode": "Markdown"
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print(f"✅ Sent to Telegram chat {chat_id}: OK")
except Exception as e:
    payload["parse_mode"] = ""
    req_fb = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req_fb) as resp_fb:
            print(f"✅ Sent to Telegram chat {chat_id} (plain text fallback): OK")
    except Exception as ex:
        print(f"❌ Failed to send reply: {ex}")
