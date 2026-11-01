"""
schedule_switch_5am.py
Lên lịch chuyển Online lúc 5:00 AM ngày 08/10/2026:
- STT 4, 5, 6, 7: 108960709, 108759434, 108754513, 108753876 -> CSKH OI (CSKHOI_DVKH)
- STT 8: 108180961 -> CSKH NA (CSKHNA_DVKH)
"""

import os
import sys
import time
import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from quick_action import do_switch_online

TARGETS_OI = [
    {"id": "108960709", "ret": "500831187", "name": "TTTM Thị trấn Cây Dương, Phụng Hiệp, Hậu Giang"},
    {"id": "108759434", "ret": "852756",    "name": "Lô 47 Võ Duy Dương, P. Quy Nhơn Nam, Gia Lai"},
    {"id": "108754513", "ret": "501045870", "name": "Lô 01, Tổ 16, KP 23, P. Quy Nhơn Nam, Gia Lai"},
    {"id": "108753876", "ret": "1488524",   "name": "KV8P Bùi Thị Xuân, Quy Nhơn, Gia Lai"}
]

TARGETS_NA = [
    {"id": "108180961", "ret": "501195055", "name": "164 Bùi Thị Xuân, P. An Khê, Gia Lai"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_5am.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg("=== BẮT ĐẦU CHUYỂN ONLINE THEO YÊU CẦU ANH QUỐC ===")
    
    # 1. Chuyển CSKH OI
    log_msg(f"--- 1. Chuyển {len(TARGETS_OI)} ATC sang CSKH OI ---")
    for item in TARGETS_OI:
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "OI")
            if success:
                log_msg(f"✅ Thành công CSKH OI: ATC {rec_id} (Ret: {item['ret']})")
            else:
                log_msg(f"❌ Thất bại CSKH OI: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            log_msg(f"❌ Ngoại lệ CSKH OI ATC {atc_id}: {e}")
        time.sleep(1)

    # 2. Chuyển CSKH NA
    log_msg(f"--- 2. Chuyển {len(TARGETS_NA)} ATC sang CSKH NA ---")
    for item in TARGETS_NA:
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "NA")
            if success:
                log_msg(f"✅ Thành công CSKH NA: ATC {rec_id} (Ret: {item['ret']})")
            else:
                log_msg(f"❌ Thất bại CSKH NA: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            log_msg(f"❌ Ngoại lệ CSKH NA ATC {atc_id}: {e}")
        time.sleep(1)

    log_msg("=== HOÀN TẤT BÀN GIAO CHUYỂN ONLINE ===")

def wait_until_5am():
    now = datetime.datetime.now()
    if now.hour < 5:
        target = now.replace(hour=5, minute=0, second=0, microsecond=0)
    else:
        target = (now + datetime.timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    
    diff = (target - now).total_seconds()
    log_msg(f"Đã lên lịch chờ đến: {target.strftime('%Y-%m-%d %H:%M:%S')} (còn {int(diff)} giây, ~{diff/3600:.2f} giờ)")
    
    while True:
        now = datetime.datetime.now()
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            break
        sleep_dur = min(remaining, 60)
        time.sleep(sleep_dur)
        
    log_msg("Đã đến 5:00 AM! Bắt đầu thực thi chuyển online...")
    run_switch()

if __name__ == "__main__":
    if "--now" in sys.argv:
        run_switch()
    elif "--wait" in sys.argv:
        wait_until_5am()
    else:
        print("Lịch chuyển Online dự kiến:")
        print("1. Nhóm CSKH OI:")
        for t in TARGETS_OI:
            print(f"   - ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("2. Nhóm CSKH NA:")
        for t in TARGETS_NA:
            print(f"   - ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_5am.py --wait : Chờ đến 5:00 AM sáng mai tự động chạy")
        print("  python schedule_switch_5am.py --now  : Chạy ngay lập tức")
