"""
schedule_switch_oct21.py
Lên lịch chuyển Online lúc 5:00 AM ngày 21/10/2026:
- 2 ATC sang CSKH OI:
  1. 109450235 (Ret: 500565265 - 08 Lê Chân, Nha Trang)
  2. 109404911 (Ret: 500736927 - 10 Hai Bà Trưng, P. Nha Trang)
- 8 ATC sang CSKH T15 (CSKHOI_T15_DVKH):
  3. 109451241 (Ret: 501204281 - 284 Nguyễn Thị Minh Khai)
  4. 109451096 (Ret: 501201280 - 86 Trần Phú)
  5. 109450908 (Ret: 501216685 - 202 Ngô Gia Tự)
  6. 109450299 (Ret: 501108270 - Đảo Hòn Tre)
  7. 109450245 (Ret: 501212282 - 83 Hùng Vương)
  8. 109450237 (Ret: 501216956 - 178 Nguyễn Thị Minh Khai)
  9. 109404099 (Ret: 501215466 - 135A - 137 Hoàng Văn Thụ)
  10. 109403652 (Ret: 501214694 - 271 Nguyễn Thiện Thuật)
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
    {"id": "109450235", "ret": "500565265", "name": "08 Lê Chân, Nha Trang, Khánh Hòa (SĐT: 0344677960)"},
    {"id": "109404911", "ret": "500736927", "name": "10 Hai Bà Trưng, Phường Nha Trang, Khánh Hòa (SĐT: 0935046378)"}
]

TARGETS_T15 = [
    {"id": "109451241", "ret": "501204281", "name": "284 Nguyễn Thị Minh Khai, Phường Nha Trang, Khánh Hòa (SĐT: 0796060679)"},
    {"id": "109451096", "ret": "501201280", "name": "86 Trần Phú, Phường Nha Trang, Khánh Hòa (SĐT: 0342588998)"},
    {"id": "109450908", "ret": "501216685", "name": "202 Ngô Gia Tự, Phường Nha Trang, Khánh Hòa (SĐT: 0868154029)"},
    {"id": "109450299", "ret": "501108270", "name": "Đảo Hòn Tre, Phường Nha Trang, Khánh Hòa (SĐT: 0984544333)"},
    {"id": "109450245", "ret": "501212282", "name": "83 Hùng Vương, Phường Nha Trang, Khánh Hòa (SĐT: 0987578675)"},
    {"id": "109450237", "ret": "501216956", "name": "178 Nguyễn Thị Minh Khai, Phường Nha Trang, Khánh Hòa (SĐT: 0981184294)"},
    {"id": "109404099", "ret": "501215466", "name": "135A - 137- 137A Hoàng Văn Thụ, Phường Nha Trang, Khánh Hòa (SĐT: 0975688881)"},
    {"id": "109403652", "ret": "501214694", "name": "271 Nguyễn Thiện Thuật, Phường Nha Trang, Khánh Hòa (SĐT: 0942878486)"}
]

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "schedule_switch_oct21.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def run_switch():
    total_targets = len(TARGETS_OI) + len(TARGETS_T15)
    log_msg(f"=== BẮT ĐẦU CHUYỂN ONLINE CHO {total_targets} ATC (NGÀY 21/10/2026) ===")
    
    success_cnt = 0
    fail_cnt = 0

    # 1. Chuyển CSKH OI (2 ATC)
    log_msg(f"--- BƯỚC 1: CHUYỂN {len(TARGETS_OI)} ATC SANG CSKH OI ---")
    for idx, item in enumerate(TARGETS_OI, 1):
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "OI")
            if success:
                success_cnt += 1
                log_msg(f"✅ [OI {idx}/{len(TARGETS_OI)}] Thành công: ATC {rec_id} (Ret: {item['ret']}) -> {group_label}")
            else:
                fail_cnt += 1
                log_msg(f"❌ [OI {idx}/{len(TARGETS_OI)}] Thất bại: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            fail_cnt += 1
            log_msg(f"❌ [OI {idx}/{len(TARGETS_OI)}] Ngoại lệ ATC {atc_id}: {e}")
        time.sleep(1)

    # 2. Chuyển CSKH T15 (8 ATC)
    log_msg(f"--- BƯỚC 2: CHUYỂN {len(TARGETS_T15)} ATC SANG CSKH T15 ---")
    for idx, item in enumerate(TARGETS_T15, 1):
        atc_id = item["id"]
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "T15")
            if success:
                success_cnt += 1
                log_msg(f"✅ [T15 {idx}/{len(TARGETS_T15)}] Thành công: ATC {rec_id} (Ret: {item['ret']}) -> {group_label}")
            else:
                fail_cnt += 1
                log_msg(f"❌ [T15 {idx}/{len(TARGETS_T15)}] Thất bại: ATC {rec_id} - raw={raw_res}")
        except Exception as e:
            fail_cnt += 1
            log_msg(f"❌ [T15 {idx}/{len(TARGETS_T15)}] Ngoại lệ ATC {atc_id}: {e}")
        time.sleep(1)

    log_msg(f"=== HOÀN TẤT: Thành công {success_cnt}/{total_targets}, Thất bại {fail_cnt} ===")

def wait_until_5am():
    now = datetime.datetime.now()
    target = datetime.datetime(2026, 10, 21, 5, 0, 0)
    
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
        
    log_msg("Đã đến 5:00 AM ngày 21/10! Bắt đầu thực thi chuyển online...")
    run_switch()

if __name__ == "__main__":
    if "--now" in sys.argv:
        run_switch()
    elif "--wait" in sys.argv:
        wait_until_5am()
    else:
        print(f"Lên lịch chuyển Online lúc 5:00 AM ngày 21/10/2026:")
        print(f"\n1. Nhóm CSKH OI ({len(TARGETS_OI)} ATC):")
        for idx, t in enumerate(TARGETS_OI, 1):
            print(f"   {idx}. ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print(f"\n2. Nhóm CSKH T15 ({len(TARGETS_T15)} ATC):")
        for idx, t in enumerate(TARGETS_T15, 1):
            print(f"   {idx}. ATC {t['id']} (Ret: {t['ret']}) - {t['name']}")
        print("\nCú pháp:")
        print("  python schedule_switch_oct21.py --wait : Chờ đến 5:00 AM 21/10 tự động chạy")
        print("  python schedule_switch_oct21.py --now  : Chạy ngay lập tức")
