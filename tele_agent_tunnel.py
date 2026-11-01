import sys
import os
import urllib.request
import json
import time

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"

sys.stdout.reconfigure(encoding='utf-8')

log_path = r"C:\Users\quoc\.gemini\antigravity\brain\9086a38a-1395-4d47-86c0-de965c60c864\scratch\latest_agent_task.json"

print("🚀 AGENTIC REASONING PASSTHROUGH TUNNEL IS ACTIVE...", flush=True)

def record_user_task(chat_id, prompt):
    print(f"\n🧠 FORWARDING TELEGRAM PROMPT TO ANTIGRAVITY AI AGENT:\n  • Chat ID: {chat_id}\n  • Prompt: {prompt}\n", flush=True)
    task_data = {
        "chat_id": chat_id,
        "prompt": prompt,
        "timestamp": time.time(),
        "status": "pending_ai_processing"
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        record_user_task(sys.argv[1], sys.argv[2])
