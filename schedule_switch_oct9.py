"""
schedule_switch_oct9.py
Lên lịch chuyển Online CSKH OI lúc 5:00 AM ngày 09/10/2026 cho 3 ATC:
- 109179271 (Ret: 500864900 - Bạc Liêu)
- 109094914 (Ret: 500848837 - Bạc Liêu)
- 109004475 (Ret: 500458813 - Hậu Giang)
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
    {"id": "109179271", "ret": "500864900", "name": "Ấp Khúc Tréo A, Xã Tân Phong, TX. Giá Rai, Bạc Liêu"},
    {"id": "109094914", "ret": "500848837", "name": "Khóm 2, P. Láng Tròn, TX. Giá Rai, T. Bạc Liêu"},
    {"id": "109004475", "ret": "500458813", "name": "Đường Hùng Vương, TT. Ngã Sáu, Châu Thành, Hậu Giang"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct9.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg("=== BẮT ĐẦU CHUYỂN CSKH OI CHO 3 ATC THEO YÊU CẦU ANH QUỐC ===")
    success_cnt = 0
    fail_cnt = 0
    for item in TARGETS_OI:
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "OI")
            if success:
                success_cnt += 1
                log_msg(f"✅ Thành công: ATC {rec_id} (Ret: {item['ret']}) -> {group_label}")
            else:
                fail_cnt += 1
                log_msg(f"❌ Thất bại: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            fail_cnt += 1
            log_msg(f"❌ Ngoại lệ ATC {atc_id}: {e}")
        time.sleep(1)

    log_msg(f"=== HOÀN TẤT: Thành công {success_cnt}/{len(TARGETS_OI)}, Thất bại {fail_cnt} ===")

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
        print(f"Danh sách 3 ATC sẽ chuyển CSKH OI lúc 5:00 AM:")
        for t in TARGETS_OI:
            print(f"  - ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct9.py --wait : Chờ đến 5:00 AM sáng mai tự động chạy")
        print("  python schedule_switch_oct9.py --now  : Chạy ngay lập tức")
