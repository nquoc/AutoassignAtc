import os
import sys
import json
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from crm_api import get_region_summary

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "assignment_history.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
REGIONS_FILE = os.path.join(BASE_DIR, "regions.json")
STAFF_FILE = os.path.join(BASE_DIR, "staff.json")

def log_assignment(region_name, coacher, staff_id, staff_name, quantity):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
            
    today_str = time.strftime("%Y-%m-%d")
    record = {
        "timestamp": time.time(),
        "time": time.strftime("%H:%M:%S"),
        "date": today_str,
        "region_name": region_name,
        "coacher": coacher,
        "staff_id": staff_id,
        "staff_name": staff_name,
        "quantity": quantity
    }
    history.append(record)
    
    # Keep only last 30 days of history
    cutoff = time.time() - (86400 * 30)
    history = [h for h in history if h.get("timestamp", 0) > cutoff]
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi ghi history: {e}")

def get_today_assignments():
    today_str = time.strftime("%Y-%m-%d")
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            pass
    return [h for h in history if h.get("date") == today_str]

def generate_daily_report_text(log_callback=None):
    def update(msg):
        if log_callback: log_callback(msg)
        else: print(msg)

    update("⏳ Đang tổng hợp báo cáo ngày...")
    today_items = get_today_assignments()
    
    staff_totals = {}
    for item in today_items:
        c_key = item.get("coacher", "quoc")
        s_name = item.get("staff_name", item.get("staff_id"))
        qty_raw = item.get("quantity", 0)
        try:
            qty = int(qty_raw)
        except (ValueError, TypeError):
            qty = 0
        
        if " - " in s_name:
            parts = s_name.split(" - ")
            short_s_name = f"{parts[0]} - {parts[1]}"
        else:
            short_s_name = s_name
            
        key = (c_key, short_s_name)
        staff_totals[key] = staff_totals.get(key, 0) + qty

    # Part 1: Staff Assigned Today (Coacher Quốc)
    part1_lines = []
    quoc_today_staff = [k for k in staff_totals if k[0] == "quoc"]
    total_assigned_today = sum(staff_totals[k] for k in quoc_today_staff)
    
    if quoc_today_staff:
        for _, s_name in sorted(quoc_today_staff, key=lambda x: staff_totals[x], reverse=True):
            part1_lines.append(f"  - {s_name}: `{staff_totals[('quoc', s_name)]}` data")
    else:
        part1_lines.append("  - _Hôm nay chưa có dữ liệu phân công mới._")

    # Part 2 & Part 3: Scan concurrently (View 20154 single fetch + Regions)
    update("⏳ Đang quét dữ liệu ATC nhân sự & tồn đọng khu vực Coacher Quốc...")
    
    all_staff_tasks = []
    if os.path.exists(STAFF_FILE):
        try:
            with open(STAFF_FILE, "r", encoding="utf-8") as f:
                s_dict = json.load(f)
                all_staff_tasks = s_dict.get("quoc", [])
        except:
            pass

    regions_list = []
    if os.path.exists(REGIONS_FILE):
        try:
            with open(REGIONS_FILE, "r", encoding="utf-8") as f:
                raw_regions = json.load(f)
                regions_list = [r for r in raw_regions if r.get("coacher") == "quoc"]
        except:
            pass

    # 1. Pre-flight check & single fetch for View 20154
    view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"
    import crm_api
    
    view_20154_rows = None
    for attempt in range(2):
        view_20154_rows = crm_api.fetch_crm_export(view_url, force_refresh=(attempt > 0))
        if view_20154_rows and len(view_20154_rows) > 0 and "Retailer ID" in view_20154_rows[0]:
            break
        time.sleep(2)

    staff_holding_results = []
    if view_20154_rows and len(view_20154_rows) > 1:
        headers = view_20154_rows[0]
        o_idx = headers.index("Người xử lý") if "Người xử lý" in headers else 13
        staff_counts = {s["short_id"]: 0 for s in all_staff_tasks}
        for r in view_20154_rows[1:]:
            if len(r) > o_idx:
                owner_val = r[o_idx].strip()
                for s in all_staff_tasks:
                    if s["short_id"] in owner_val:
                        staff_counts[s["short_id"]] += 1
                        break
        for s in all_staff_tasks:
            s_name = s["name"]
            short_name = f"{s_name.split(' - ')[0]} - {s_name.split(' - ')[1]}" if " - " in s_name else s_name
            staff_holding_results.append((short_name, staff_counts.get(s["short_id"], 0)))
    else:
        for s in all_staff_tasks:
            s_name = s["name"]
            short_name = f"{s_name.split(' - ')[0]} - {s_name.split(' - ')[1]}" if " - " in s_name else s_name
            staff_holding_results.append((short_name, 0))

    def scan_one(region):
        for retry in range(2):
            try:
                summary = get_region_summary(region["url"])
                if summary is not None:
                    return region["name"], summary.get("total_unassigned", 0)
            except Exception:
                pass
            time.sleep(1)
        return region["name"], 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        region_futures = [executor.submit(scan_one, r) for r in regions_list]
        scan_results = [f.result() for f in region_futures]

    staff_holding_results.sort(key=lambda x: x[1], reverse=True)
    counts = [c for _, c in staff_holding_results]
    max_count = max(counts) if counts else -1
    min_count = min(counts) if counts else -1

    part2_quoc = []
    for s_name, count in staff_holding_results:
        if count == max_count and max_count > min_count:
            icon = "🔴"
            tag = " *(Cao nhất)*"
        elif count == min_count and max_count > min_count:
            icon = "🟢"
            tag = " *(Thấp nhất)*"
        else:
            icon = "🟡"
            tag = ""
        line = f"  - {icon} {s_name}: `{count}` ATC treo{tag}"
        part2_quoc.append(line)

    total_staff_holding = sum(counts)

    # Emergency check: If holding returned 0 for all staff, retry with forced refresh once
    if total_staff_holding == 0 and len(all_staff_tasks) > 0:
        try:
            print("⚠️ Cảnh báo: Dữ liệu View 20154 trả về 0 toàn bộ, đang làm mới phiên và quét lại...", flush=True)
            retry_rows = crm_api.fetch_crm_export(view_url, force_refresh=True)
            if retry_rows and len(retry_rows) > 1 and "Retailer ID" in retry_rows[0]:
                headers = retry_rows[0]
                o_idx = headers.index("Người xử lý") if "Người xử lý" in headers else 13
                staff_counts = {s["short_id"]: 0 for s in all_staff_tasks}
                for r in retry_rows[1:]:
                    if len(r) > o_idx:
                        owner_val = r[o_idx].strip()
                        for s in all_staff_tasks:
                            if s["short_id"] in owner_val:
                                staff_counts[s["short_id"]] += 1
                                break
                staff_holding_results = []
                for s in all_staff_tasks:
                    s_name = s["name"]
                    short_name = f"{s_name.split(' - ')[0]} - {s_name.split(' - ')[1]}" if " - " in s_name else s_name
                    staff_holding_results.append((short_name, staff_counts.get(s["short_id"], 0)))
                staff_holding_results.sort(key=lambda x: x[1], reverse=True)
                counts = [c for _, c in staff_holding_results]
                max_count = max(counts) if counts else -1
                min_count = min(counts) if counts else -1
                part2_quoc = []
                for s_name, count in staff_holding_results:
                    if count == max_count and max_count > min_count:
                        icon = "🔴"
                        tag = " *(Cao nhất)*"
                    elif count == min_count and max_count > min_count:
                        icon = "🟢"
                        tag = " *(Thấp nhất)*"
                    else:
                        icon = "🟡"
                        tag = ""
                    part2_quoc.append(f"  - {icon} {s_name}: `{count}` ATC treo{tag}")
                total_staff_holding = sum(counts)
        except Exception as e:
            print(f"Error during emergency holding retry: {e}", flush=True)

    part3_quoc = []
    total_remaining = 0
    
    for r_name, total in scan_results:
        total_remaining += total
        icon = "🟢" if total > 0 else "🔴"
        line = f"  - {icon} *{r_name}*: `{total}` data"
        part3_quoc.append(line)

    grand_total = total_staff_holding + total_remaining

    report_text = (
        f"📊 *BÁO CÁO THỐNG KÊ PHÂN CÔNG ATC - COACHER QUỐC*\n"
        f"⏰ *Thời gian xuất báo cáo*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        f"💼 *1. TỔNG SỐ ATC TREO HIỆN TẠI TỪNG NHÂN SỰ ĐANG GIỮ (Tổng: `{total_staff_holding}` ATC treo):*\n"
        + "\n".join(part2_quoc) + "\n\n"
        f"📍 *2. TỔNG HỢP DATA CÁC TỈNH CÒN TỒN ĐỌNG (Tổng: `{total_remaining}` data):*\n"
        + "\n".join(part3_quoc) + "\n\n"
        f"🔥 *TỔNG CỘNG TẤT CẢ DATA TREO & TỒN ĐỌNG: `{grand_total}` data*\n\n"
        f"🤖 _Báo cáo tự động được gửi từ hệ thống Bot AutoassignAtc vào lúc 18h00 hàng ngày._"
    )
    return report_text

def send_google_chat_report(webhook_url=None, log_callback=None):
    def update(msg):
        if log_callback: log_callback(msg)
        else: print(msg)

    if not webhook_url:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    webhook_url = cfg.get("gchat_webhook")
            except:
                pass

    if not webhook_url:
        update("❌ Chưa cấu hình URL Google Chat Webhook.")
        return False, "Chưa cấu hình Google Chat Webhook."

    try:
        text = generate_daily_report_text(log_callback=update)
        payload = {"text": text}
        
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                update("🎉 Đã gửi báo cáo thành công lên Google Chat Space!")
                return True, text
            else:
                update(f"❌ Lỗi gửi Google Chat: Status {resp.status}")
                return False, f"Lỗi HTTP Status {resp.status}"
    except Exception as e:
        update(f"❌ Lỗi kết nối Google Chat: {e}")
        return False, str(e)
