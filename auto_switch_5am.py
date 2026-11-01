"""
auto_switch_5am.py - Script tự động chuyển toàn bộ ATC trong view 17559 sang CSKH OI.
Hỗ trợ chạy ngay (--now) hoặc chờ đến đúng 5:00 AM sáng hôm sau (--wait).
"""

import os
import sys
import time
import datetime
import urllib.request
import json
import re
from bs4 import BeautifulSoup

# Ensure current dir is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from quick_action import do_switch_online, get_headers

TARGET_VIEW_URL = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=17559&orderby=&sortorder=&search_params=&search_key=summary&search_value="
KNOWN_TARGET_IDS = ['108483721', '108483717', '108483712', '108483706', '108483695', '108483451']

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    log_file = os.path.join(CURRENT_DIR, "auto_switch_5am.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def fetch_records_in_view():
    headers = get_headers()
    req = urllib.request.Request(TARGET_VIEW_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8')
    except Exception as e:
        log_msg(f"Lỗi fetch view 17559: {e}")
        return []
        
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr', class_='listViewEntries')
    rec_list = []
    for r in rows:
        rec_id = r.get('data-id')
        tds = [td.get_text(strip=True) for td in r.find_all('td')]
        ret_id = tds[1] if len(tds) > 1 else ''
        addr = tds[4] if len(tds) > 4 else ''
        rec_list.append({'id': rec_id, 'retailer_id': ret_id, 'address': addr})
    return rec_list

def run_switch():
    log_msg("=== BẮT ĐẦU CHUYỂN CSKH OI CHO VIEW 17559 ===")
    records = fetch_records_in_view()
    if not records:
        log_msg("Không tìm thấy dòng nào trong view 17559 qua HTML, kiểm tra danh sách mặc định đã lưu...")
        ids_to_switch = KNOWN_TARGET_IDS
    else:
        ids_to_switch = [r['id'] for r in records if r.get('id')]
        # Gộp thêm known IDs nếu chưa có
        for kid in KNOWN_TARGET_IDS:
            if kid not in ids_to_switch:
                ids_to_switch.append(kid)

    log_msg(f"Tổng số ATC cần chuyển: {len(ids_to_switch)}: {ids_to_switch}")
    
    success_count = 0
    fail_count = 0
    for atc_id in ids_to_switch:
        try:
            success, rec_id, group_label, raw_res = do_switch_online(atc_id, "OI")
            if success:
                success_count += 1
                log_msg(f"✅ Thành công: ATC {rec_id} -> {group_label}")
            else:
                fail_count += 1
                log_msg(f"❌ Thất bại: ATC {rec_id} -> raw={raw_res}")
        except Exception as e:
            fail_count += 1
            log_msg(f"❌ Ngoại lệ khi chuyển ATC {atc_id}: {e}")
        time.sleep(1) # Nghỉ nhẹ giữa các request

    log_msg(f"=== KẾT THÚC: Thành công {success_count}/{len(ids_to_switch)}, Thất bại {fail_count} ===")

def wait_until_5am():
    now = datetime.datetime.now()
    # Nếu hiện tại trước 5h sáng hôm nay, mục tiêu là 5h hôm nay.
    # Nếu đã qua 5h sáng (như hiện tại 20h), mục tiêu là 5h sáng ngày mai.
    if now.hour < 5:
        target = now.replace(hour=5, minute=0, second=0, microsecond=0)
    else:
        target = (now + datetime.timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    
    diff = (target - now).total_seconds()
    log_msg(f"Đã lên lịch chờ đến: {target.strftime('%Y-%m-%d %H:%M:%S')} (còn {int(diff)} giây, ~{diff/3600:.1f} giờ)")
    
    while True:
        now = datetime.datetime.now()
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            break
        # Sleep theo block tối đa 60 giây để có thể ngắt khi cần
        sleep_dur = min(remaining, 60)
        time.sleep(sleep_dur)
        
    log_msg("Đã đến 5:00 AM! Bắt đầu thực thi...")
    run_switch()

if __name__ == "__main__":
    if "--now" in sys.argv:
        run_switch()
    elif "--wait" in sys.argv:
        wait_until_5am()
    else:
        # Mặc định in hướng dẫn và kiểm tra danh sách
        recs = fetch_records_in_view()
        print(f"Danh sách hiện tại trong view 17559 ({len(recs)} ATC):")
        for r in recs:
            print(f"  - ATC {r['id']} (Retailer: {r['retailer_id']}) - {r['address'][:50]}")
        print("\nCú pháp sử dụng:")
        print("  python auto_switch_5am.py --wait  : Chờ đến đúng 5:00 AM sáng mai rồi tự động chuyển")
        print("  python auto_switch_5am.py --now   : Thực hiện chuyển ngay lập tức")
