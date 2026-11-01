"""
schedule_switch_oct12.py
Lên lịch chuyển Online CSKH OI lúc 5:00 AM ngày 12/10/2026 cho 7 ATC từ View 17559:
- 108823238 (Ret: 500503470 - Lương Gia Hân)
- 108823211 (Ret: 500799478 - Doan Tram)
- 108823084 (Ret: 500183180 - nguyễn ngọc anh)
- 108821949 (Ret: 500608816 - đặc sản nhơn hải)
- 108773052 (Ret: 500780127 - Chị Thảo)
- 108772810 (Ret: 501086882 - Điện máy Hoàn Sáu)
- 108772418 (Ret: 500470066 - Lê Quốc Trạng)
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
    {"id": "108823238", "ret": "500503470", "name": "Lương Gia Hân - Tổ 8, KP 1, P. Quy Nhơn Bắc, Gia Lai"},
    {"id": "108823211", "ret": "500799478", "name": "Doan Tram - 898 Hùng Vương, TT. Chư Sê, Gia Lai"},
    {"id": "108823084", "ret": "500183180", "name": "nguyễn ngọc anh - 18/21 Hàn Mặc Tử, TP. Quy Nhơn, Bình Định"},
    {"id": "108821949", "ret": "500608816", "name": "đặc sản nhơn hải - P. Quy Nhơn Đông, Gia Lai"},
    {"id": "108773052", "ret": "500780127", "name": "Chị Thảo - 09 Trần Thị Kỷ, P. Quy Nhơn Nam, Gia Lai"},
    {"id": "108772810", "ret": "501086882", "name": "Điện máy Hoàn Sáu - Tổ dân phố Nhơn Thiện, An Nhơn Bắc, Gia Lai"},
    {"id": "108772418", "ret": "500470066", "name": "Lê Quốc Trạng - Tổ 6 KP 7, P. Trần Quang Diệu, TP. Quy Nhơn, Bình Định"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct12.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg("=== BẮT ĐẦU CHUYỂN CSKH OI CHO 7 ATC (NGÀY 12/10) ===")
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
        print(f"Danh sách 7 ATC sẽ chuyển CSKH OI lúc 5:00 AM ngày 12/10:")
        for t in TARGETS_OI:
            print(f"  - ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct12.py --wait : Chờ đến 5:00 AM sáng mai tự động chạy")
        print("  python schedule_switch_oct12.py --now  : Chạy ngay lập tức")
