"""
schedule_switch_oct11.py
Lên lịch chuyển Online CSKH OI lúc 5:00 AM ngày 11/10/2026 cho 10 ATC từ View 17559:
- 109309215 (Ret: 500360005 - Cà Mau)
- 109309191 (Ret: 980051 - Gia Lai)
- 109309178 (Ret: 500933026 - Gia Lai)
- 108917756 (Ret: 500641392 - Gia Lai)
- 108917754 (Ret: 500938433 - Đồng Tháp)
- 108917734 (Ret: 500950691 - Cần Thơ)
- 108917602 (Ret: 500344570 - Gia Lai)
- 108917567 (Ret: 501128829 - Gia Lai)
- 108888955 (Ret: 500808193 - Gia Lai)
- 108888950 (Ret: 500402017 - Gia Lai)
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
    {"id": "109309215", "ret": "500360005", "name": "chợ năm căn, Cà Mau"},
    {"id": "109309191", "ret": "980051",    "name": "Thôn Hàm Rồng, Xã Ia Păn, Huyện Đắc Đoa, Gia Lai"},
    {"id": "109309178", "ret": "500933026", "name": "Đường Trần Khánh Dư, Xã Chư Sê, Tỉnh Gia Lai"},
    {"id": "108917756", "ret": "500641392", "name": "Hoa Lư Nối Dài, Phường Quy Nhơn, Tỉnh Gia Lai"},
    {"id": "108917754", "ret": "500938433", "name": "Ấp An Phú, xã An Long, tỉnh Đồng Tháp"},
    {"id": "108917734", "ret": "500950691", "name": "Ấp ninh thới xã thới an hội thành phố cần thơ"},
    {"id": "108917602", "ret": "500344570", "name": "Lô A43 44 Điện Biên Phủ, Phường Quy Nhơn Đông, Gia Lai"},
    {"id": "108917567", "ret": "501128829", "name": "Tổ 2 Khu Vực 5, Phường Quy Nhơn Bắc, Gia Lai"},
    {"id": "108888955", "ret": "500808193", "name": "Thôn Hàm Rồng thuộc xã Ia Băng, huyện Đắk Đoa, Gia Lai"},
    {"id": "108888950", "ret": "500402017", "name": "Tổ 1 Đống Đa, Thành phố Pleiku, Gia Lai"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct11.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg("=== BẮT ĐẦU CHUYỂN CSKH OI CHO 10 ATC (NGÀY 11/10) ===")
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
        print(f"Danh sách 10 ATC sẽ chuyển CSKH OI lúc 5:00 AM:")
        for t in TARGETS_OI:
            print(f"  - ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct11.py --wait : Chờ đến 5:00 AM sáng mai tự động chạy")
        print("  python schedule_switch_oct11.py --now  : Chạy ngay lập tức")
