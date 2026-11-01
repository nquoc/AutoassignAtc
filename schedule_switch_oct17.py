"""
schedule_switch_oct17.py
Lên lịch chuyển Online CSKH OI lúc 5:00 AM ngày 17/10/2026 cho toàn bộ 24 ATC từ View 17559 (QUỐC ÔM OFFline).
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
    {"id": "109403891", "ret": "501161315", "name": "8 Trần Hưng Đạo, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403881", "ret": "500460759", "name": "120/31 Nguyễn Thiện Thuật, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403875", "ret": "501085000", "name": "110 Nguyễn Thiện Thuật, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403827", "ret": "500818308", "name": "Vinpearl - Nha Trang - Khánh Hòa"},
    {"id": "109403824", "ret": "501018562", "name": "42/TT2 - Khu K98 ACC - Trần Nhật Duật, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403811", "ret": "500921134", "name": "74 đường Vân Đồn, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403808", "ret": "501029639", "name": "28A Ngô Thời Nhiệm, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403802", "ret": "500638113", "name": "29 đường 2/4, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403798", "ret": "921295", "name": "20 Đinh Tiên Hoàng, Phường Lộc Thọ, Nha Trang, Khánh Hòa"},
    {"id": "109403662", "ret": "500799567", "name": "102 Hùng Vương, Lộc Thọ, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403661", "ret": "500842213", "name": "114 Hồng Bàng, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403658", "ret": "501008709", "name": "23B Biệt Thự, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403654", "ret": "910754", "name": "20 Hai Bà Trưng, Xương Huân, Nha Trang, Khánh Hòa"},
    {"id": "109403550", "ret": "500355569", "name": "100a12 Trần Phú, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403548", "ret": "501118531", "name": "65 Trịnh Phong, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403467", "ret": "501011114", "name": "84 Hoàng Văn Thụ, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403463", "ret": "501167070", "name": "98 Nguyễn Thiện Thuật, Tân Lập, Nha Trang, Khánh Hòa"},
    {"id": "109403460", "ret": "501183930", "name": "49 Lê Đại Hành, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403454", "ret": "500550124", "name": "111/10 Hùng Vương, Phường Nha Trang, Khánh Hòa"},
    {"id": "109045820", "ret": "500233342", "name": "Ấp Thị Tứ, Xã Phong Điền, Thành phố Cần Thơ"},
    {"id": "109028878", "ret": "500178589", "name": "Lô F19, Điện Biên Phủ, Phường Quy Nhơn Đông, Tỉnh Gia Lai"},
    {"id": "109004547", "ret": "455889", "name": "Khu QHDC Phía Đông Đường Nguyễn Trọng Trì, Phường Quy Nhơn Đông, Tỉnh Gia Lai"},
    {"id": "108960152", "ret": "500505644", "name": "Tổ 2, Ia Kring, Thành phố Pleiku, Gia Lai"},
    {"id": "108823019", "ret": "1508447", "name": "Số nhà 83 đường Nguyễn Mân, Phường Nhơn Bình, TP Quy Nhơn, Tỉnh Gia Lai"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct17.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg(f"=== BẮT ĐẦU CHUYỂN CSKH OI CHO TOÀN BỘ {len(TARGETS_OI)} ATC (NGÀY 17/10/2026) ===")
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
    target = datetime.datetime(2026, 10, 17, 5, 0, 0)
    
    # If already past 5am on 17/10, target tomorrow 5am
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
        
    log_msg("Đã đến 5:00 AM ngày 17/10! Bắt đầu thực thi chuyển online...")
    run_switch()

if __name__ == "__main__":
    if "--now" in sys.argv:
        run_switch()
    elif "--wait" in sys.argv:
        wait_until_5am()
    else:
        print(f"Danh sách {len(TARGETS_OI)} ATC sẽ chuyển CSKH OI lúc 5:00 AM ngày 17/10/2026:")
        for idx, t in enumerate(TARGETS_OI, 1):
            print(f"  {idx:2d}. ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct17.py --wait : Chờ đến 5:00 AM 17/10 tự động chạy")
        print("  python schedule_switch_oct17.py --now  : Chạy ngay lập tức")
