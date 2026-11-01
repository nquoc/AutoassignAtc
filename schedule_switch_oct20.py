"""
schedule_switch_oct20.py
Lên lịch chuyển Online CSKH OI lúc 5:00 AM ngày 20/10/2026 cho toàn bộ 18 ATC Khánh Hòa (Nha Trang) từ View 17559 (QUỐC ÔM OFFline).
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
    {"id": "109404775", "ret": "500827372", "name": "Số 33 Phan Chu Trinh, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404708", "ret": "500132281", "name": "8 Đống Đa, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404668", "ret": "501022967", "name": "51 Hồng Bàng, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109404665", "ret": "500136726", "name": "23 Đinh Lễ, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109404657", "ret": "500882801", "name": "173/2 Bạch Đằng, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404651", "ret": "500491747", "name": "130 Bạch Đằng, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404643", "ret": "500867056", "name": "43 đường Hùng Vương, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404618", "ret": "501060346", "name": "Lô 09, 64 Trần Phú, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109404580", "ret": "1487859", "name": "Đường Thích Quảng Đức, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404577", "ret": "500240201", "name": "3 Xương Huân, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109404576", "ret": "501158296", "name": "203 Nguyễn Thiện Thuật, Phường Nha Trang, Khánh Hòa"},
    {"id": "109404570", "ret": "500950834", "name": "32 Âu Cơ, Phường Nha Trang, Khánh Hoà"},
    {"id": "109404489", "ret": "500938805", "name": "29 đường 2/4, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109404486", "ret": "501088127", "name": "54 Nguyễn Hữu Huân, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109403944", "ret": "1435877", "name": "203 Lê Hồng Phong, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109403940", "ret": "501063688", "name": "16 Lê Quý Đôn, Phường Nha Trang, Tỉnh Khánh Hòa"},
    {"id": "109403913", "ret": "500451046", "name": "Shophouse SGA-08 vinpearl, Phường Nha Trang, Khánh Hòa"},
    {"id": "109403896", "ret": "501058024", "name": "21 Lý Tự Trọng, Phường Nha Trang, Tỉnh Khánh Hòa"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct20.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    log_msg(f"=== BẮT ĐẦU CHUYỂN CSKH OI CHO {len(TARGETS_OI)} ATC KHÁNH HÒA (NGÀY 20/10/2026) ===")
    success_cnt = 0
    fail_cnt = 0
    for idx, item in enumerate(TARGETS_OI, 1):
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "OI")
            if success:
                success_cnt += 1
                log_msg(f"✅ [{idx:2d}/{len(TARGETS_OI)}] Thành công: ATC {rec_id} (Ret: {item['ret']}) -> {group_label}")
            else:
                fail_cnt += 1
                log_msg(f"❌ [{idx:2d}/{len(TARGETS_OI)}] Thất bại: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            fail_cnt += 1
            log_msg(f"❌ [{idx:2d}/{len(TARGETS_OI)}] Ngoại lệ ATC {atc_id}: {e}")
        time.sleep(1)

    log_msg(f"=== HOÀN TẤT: Thành công {success_cnt}/{len(TARGETS_OI)}, Thất bại {fail_cnt} ===")

def wait_until_5am():
    now = datetime.datetime.now()
    target = datetime.datetime(2026, 10, 20, 5, 0, 0)
    
    # If already past 5am on 20/10, target tomorrow 5am
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
        
    log_msg("Đã đến 5:00 AM ngày 20/10! Bắt đầu thực thi chuyển online...")
    run_switch()

if __name__ == "__main__":
    if "--now" in sys.argv:
        run_switch()
    elif "--wait" in sys.argv:
        wait_until_5am()
    else:
        print(f"Danh sách {len(TARGETS_OI)} ATC sẽ chuyển CSKH OI lúc 5:00 AM ngày 20/10/2026:")
        for idx, t in enumerate(TARGETS_OI, 1):
            print(f"  {idx:2d}. ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct20.py --wait : Chờ đến 5:00 AM 20/10 tự động chạy")
        print("  python schedule_switch_oct20.py --now  : Chạy ngay lập tức")
