import sys
import os
import urllib.request
import json
import time

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"

sys.stdout.reconfigure(encoding='utf-8')

print("🧹 CLEANING TELEGRAM WEBHOOK & PREVIOUS BOT PROCESSES...", flush=True)

try:
    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True"
    with urllib.request.urlopen(del_url) as resp:
        print("  ✅ Telegram webhook cleaned successfully!", flush=True)
except Exception as e:
    print(f"  ⚠️ Webhook clean error: {e}", flush=True)

print("🚀 100% PURE AGENTIC PASS-THROUGH TUNNEL IS RUNNING 24/7...", flush=True)

offset = 0

while True:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
        for result in data.get("result", []):
            offset = result["update_id"] + 1
            msg = result.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            
            if chat_id and text:
                print(f"\n📩 INCOMING TELEGRAM PROMPT FOR ANTIGRAVITY AI AGENT:\nChat ID: {chat_id}\nPrompt: {text}\n", flush=True)
                
                # Write to latest_tele_prompt.json
                out_path = r"C:\Users\quoc\.gemini\antigravity\brain\9086a38a-1395-4d47-86c0-de965c60c864\scratch\latest_tele_prompt.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump({"chat_id": chat_id, "text": text, "timestamp": time.time(), "processed": False}, f, ensure_ascii=False, indent=2)

    except Exception as e:
        if "Conflict" in str(e):
            print("⚠️ Conflict detected, retrying in 2 seconds...", flush=True)
            time.sleep(2)
        else:
            print(f"Tunnel err: {e}", flush=True)
            time.sleep(1)
