"""
schedule_switch_oct18.py
Lên lịch chuyển Online CSKH OI lúc 5:00 AM ngày 18/10/2026 cho toàn bộ 6 ATC Bạc Liêu từ View 17559 (QUỐC ÔM OFFline).
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
    {
        "id": "109544288",
        "ret": "1402397",
        "name": "Khóm 1, Phường 1, Thị Xã Giá Rai, Bạc Liêu (SĐT: 0974378783)"
    },
    {
        "id": "109337583",
        "ret": "500503636",
        "name": "Khu Đô Thị Hoàng Phát, Phường 1, Thành phố Bạc Liêu (SĐT: 0945399410)"
    },
    {
        "id": "109283096",
        "ret": "500168444",
        "name": "Khóm 1, Phường 1, Thị xã Giá Rai, Tỉnh Bạc Liêu (SĐT: 0918396576)"
    },
    {
        "id": "109221213",
        "ret": "500872621",
        "name": "Ấp Khúc Tréo A, Tân Phong, Giá Rai, Bạc Liêu (SĐT: 0917464247)"
    },
    {
        "id": "109028760",
        "ret": "500823651",
        "name": "Hà Huy Tập, Phường 3, Thành phố Bạc Liêu (SĐT: 0946555599)"
    },
    {
        "id": "108918403",
        "ret": "500164045",
        "name": "KDC Hoàng Phát đường Nguyễn Văn Cừ, Phường 1, TP Bạc Liêu (SĐT: 0948644688)"
    }
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct18.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg(f"=== BẮT ĐẦU CHUYỂN CSKH OI CHO {len(TARGETS_OI)} ATC BẠC LIÊU (NGÀY 18/10/2026) ===")
    success_cnt = 0
    fail_cnt = 0
    for idx, item in enumerate(TARGETS_OI, 1):
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "OI")
            if success:
                success_cnt += 1
                log_msg(f"✅ [{idx}/{len(TARGETS_OI)}] Thành công: ATC {rec_id} (Ret: {item['ret']}) -> {group_label}")
            else:
                fail_cnt += 1
                log_msg(f"❌ [{idx}/{len(TARGETS_OI)}] Thất bại: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            fail_cnt += 1
            log_msg(f"❌ [{idx}/{len(TARGETS_OI)}] Ngoại lệ ATC {atc_id}: {e}")
        time.sleep(1)

    log_msg(f"=== HOÀN TẤT: Thành công {success_cnt}/{len(TARGETS_OI)}, Thất bại {fail_cnt} ===")

def wait_until_5am():
    now = datetime.datetime.now()
    target = datetime.datetime(2026, 10, 18, 5, 0, 0)
    
    # If already past 5am on 18/10, target tomorrow 5am
    if now >= target:
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
        
    log_msg("Đã đến 5:00 AM ngày 18/10! Bắt đầu thực thi chuyển online...")
    run_switch()

if __name__ == "__main__":
    if "--now" in sys.argv:
        run_switch()
    elif "--wait" in sys.argv:
        wait_until_5am()
    else:
        print(f"Danh sách {len(TARGETS_OI)} ATC sẽ chuyển CSKH OI lúc 5:00 AM ngày 18/10/2026:")
        for idx, t in enumerate(TARGETS_OI, 1):
            print(f"  {idx:2d}. ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct18.py --wait : Chờ đến 5:00 AM 18/10 tự động chạy")
        print("  python schedule_switch_oct18.py --now  : Chạy ngay lập tức")
