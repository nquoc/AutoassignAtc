# -*- coding: utf-8 -*-
"""
sc_renew_monitor.py - Tự động quét và thông báo Ticket mới từ Team Tái Ký (Contract Renewal)
trong hàng đợi SC Group (View 20322) lên Google Chat.
"""

import os
import sys
import re
import json
import time
import html as html_lib
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import crm_api

# Danh sách nhân sự Team Tái Ký (Contract Renewal)
RENEW_CREATORS = [
    "Đặng Thị Thu",
    "Đặng Vân Anh",
    "Nguyễn Thị Mỹ Lãnh",
    "Nguyễn Thị Thanh Hoa",
    "Phạm Thị Kim Yến",
    "Phạm Thị Vân Anh",
    "Phan Trường Giang",
    "Trầm Hồng Ngọc"
]

SEEN_FILE = os.path.join(BASE_DIR, "sc_renew_seen_tickets.json")

def get_headers():
    cookie_str, _ = crm_api.get_session()
    return {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

def is_renew_creator(creator_name: str) -> bool:
    """
    Kiểm tra xem người tạo có thuộc Team Tái Ký hay không.
    """
    if not creator_name:
        return False
    c_norm = creator_name.lower().strip()
    for name in RENEW_CREATORS:
        if name.lower() in c_norm:
            return True
    # Kiểm tra theo title bộ phận nếu có
    if "contract renewal" in c_norm or "tái ký" in c_norm:
        return True
    return False

def load_seen_tickets() -> set:
    """
    Đọc danh sách Record ID các Ticket đã từng quét / thông báo.
    """
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(str(x) for x in data)
                elif isinstance(data, dict):
                    return set(str(x) for x in data.get("seen_ids", []))
        except Exception as e:
            print(f"⚠️ [SC Renew] Lỗi đọc seen_tickets: {e}", flush=True)
    return set()

def save_seen_tickets(seen_set: set):
    """
    Lưu danh sách Record ID đã xử lý vào file JSON.
    """
    try:
        seen_list = list(seen_set)[-500:] # Giữ tối đa 500 ID gần nhất
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "seen_ids": seen_list,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ [SC Renew] Lỗi lưu seen_tickets: {e}", flush=True)

def get_ticket_detail(rid: str, headers=None) -> dict:
    """
    Bóc tách chi tiết 1 Ticket từ HelpDesk DetailView.
    """
    if headers is None:
        headers = get_headers()
    url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rid}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            dt_html = resp.read().decode('utf-8', errors='ignore')

        m_tno = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticket_no["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        tno = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_tno.group(1)).strip()) if m_tno else rid
        
        m_cf_web = re.search(r'id=["\']HelpDesk_detailView_fieldValue_cf_website["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        store = ""
        if m_cf_web:
            m_sel = re.search(r'<option[^>]*selected[^>]*>(.*?)</option>', m_cf_web.group(1), re.DOTALL)
            store = html_lib.unescape(m_sel.group(1)).strip() if m_sel else ""
            if not store:
                m_sp = re.search(r'<span[^>]*class=["\']value["\'][^>]*>(.*?)</span>', m_cf_web.group(1), re.DOTALL)
                store = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_sp.group(1) if m_sp else m_cf_web.group(1))).strip()
        
        m_contact = re.search(r'id=["\']HelpDesk_detailView_fieldValue_contact_id["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        contact = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_contact.group(1)).strip()) if m_contact else ""
        if not store: store = contact
        
        m_ret = re.search(r'id=["\']HelpDesk_detailView_fieldValue_retailer_id["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        ret = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ret.group(1)).strip()) if m_ret else ""
        
        m_title = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticket_title["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        title = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_title.group(1)).strip()) if m_title else ""

        m_desc = re.search(r'id=["\']HelpDesk_detailView_fieldValue_description["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        if m_desc:
            raw_desc = m_desc.group(1)
            raw_desc = re.sub(r'<br\s*/?>', '\n', raw_desc, flags=re.I)
            raw_desc = re.sub(r'</p>|</div>', '\n', raw_desc, flags=re.I)
            desc = html_lib.unescape(re.sub(r'<[^>]+>', '', raw_desc)).strip()
            desc = re.sub(r'\n{3,}', '\n\n', desc)
        else:
            desc = ""

        m_crt_time = re.search(r'Thời gian tạo.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        crt_time = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_crt_time.group(1)).strip()) if m_crt_time else ""

        m_crt_by = re.search(r'Người tạo.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
        crt_by = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_crt_by.group(1)).strip()) if m_crt_by else ""

        m_phones = re.findall(r'(?:0|\+84)\d{9,10}', desc)
        phone = m_phones[0] if m_phones else ""

        return {
            "record_id": rid,
            "ticket_no": tno,
            "store": store,
            "contact": contact,
            "retailer_id": ret,
            "phone": phone,
            "title": title,
            "desc": desc,
            "created_time": crt_time,
            "created_by": crt_by,
            "crm_url": url
        }
    except Exception as e:
        print(f"⚠️ [SC Renew] Lỗi bóc tách Ticket {rid}: {e}", flush=True)
        return None

def send_gchat_renew(ticket_info: dict, dry_run=False) -> bool:
    """
    Gửi thông báo có Ticket mới từ Team Tái Ký lên Google Chat Webhook chuyên biệt.
    """
    try:
        config_file = os.path.join(BASE_DIR, "config.json")
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        webhook_url = cfg.get("gchat_webhook_renew") or cfg.get("gchat_webhook")
        if not webhook_url:
            print("❌ [SC Renew] Chưa có cấu hình gchat_webhook_renew trong config.json", flush=True)
            return False

        phone_str = f"• **SĐT**: `{ticket_info['phone']}`\n" if ticket_info.get("phone") else ""
        customer_str = f"• **Khách hàng**: {ticket_info['contact']}\n" if ticket_info.get("contact") else ""
        desc_clean = (ticket_info.get("desc") or "").strip()
        if len(desc_clean) > 800:
            desc_clean = desc_clean[:800] + "... (xem tiếp trên CRM)"

        gchat_text = (
            f"🚨 *CÓ TICKET MỚI TỪ TEAM TÁI KÝ!* #SC_Group #TaiKy\n\n"
            f"• **Mã Ticket**: `{ticket_info['ticket_no']}` (ID: `{ticket_info['record_id']}`)\n"
            f"• **Tên gian hàng (Tên GH)**: `{ticket_info['store']}`\n"
            f"• **Retailer ID**: `{ticket_info['retailer_id']}`\n"
            f"{customer_str}"
            f"• **Người tạo**: *{ticket_info['created_by']}*\n"
            f"• **Thời gian tạo**: `{ticket_info['created_time']}`\n"
            f"• **Tiêu đề**: *{ticket_info['title']}*\n"
            f"{phone_str}"
            f"• **Mô tả (Description)**:\n{desc_clean}\n\n"
            f"👉 [Bấm xem chi tiết Ticket trên CRM]({ticket_info['crm_url']})"
        )

        if dry_run:
            print("[DRY-RUN GCHAT]:\n" + gchat_text, flush=True)
            return True

        payload = {"text": gchat_text}
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            success = (resp.status == 200)
            if success:
                print(f"🎉 [SC Renew] Đã bắn thông báo Ticket {ticket_info['ticket_no']} lên Google Chat thành công!", flush=True)
            return success
    except Exception as e:
        print(f"⚠️ [SC Renew] Lỗi gửi Google Chat: {e}", flush=True)
        return False

def scan_and_notify_sc_renew(is_warmup=False) -> int:
    """
    Quét View 20322 tìm Ticket mới từ Team Tái Ký và gửi thông báo.
    Nếu is_warmup=True: nạp toàn bộ ticket hiện có vào seen_tickets mà không bắn thông báo.
    Trả về số lượng ticket mới đã được thông báo.
    """
    headers = get_headers()
    url_view = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&viewname=20322"
    
    seen_ids = load_seen_tickets()
    current_ids = []
    
    # Quét trang 1 (và tối đa trang 2 nếu cần)
    for page in range(1, 3):
        p_url = f"{url_view}&page={page}"
        req = urllib.request.Request(p_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                p_html = resp.read().decode('utf-8', errors='ignore')
            matches = re.findall(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>', p_html)
            if not matches:
                break
            for mid in matches:
                if mid not in current_ids:
                    current_ids.append(str(mid))
        except Exception as e:
            print(f"⚠️ [SC Renew] Lỗi tải View 20322 trang {page}: {e}", flush=True)
            break

    if is_warmup or not seen_ids:
        # Lần đầu tiên chạy: lưu toàn bộ ticket hiện tại vào seen để không bị spam thông báo cũ
        for rid in current_ids:
            seen_ids.add(rid)
        save_seen_tickets(seen_ids)
        print(f"✅ [SC Renew Warm-up] Đã khởi tạo bộ nhớ với {len(current_ids)} ticket hiện tại trong SC Group.", flush=True)
        return 0

    # Lọc ra các ticket mới xuất hiện
    new_ids = [rid for rid in current_ids if rid not in seen_ids]
    if not new_ids:
        return 0

    print(f"🔔 [SC Renew] Phát hiện {len(new_ids)} Ticket mới trong SC Group! Đang kiểm tra người tạo...", flush=True)
    
    notified_count = 0
    with ThreadPoolExecutor(max_workers=min(4, len(new_ids))) as ex:
        details = list(ex.map(lambda r: get_ticket_detail(r, headers), new_ids))

    for d in details:
        if not d:
            continue
        rid = d["record_id"]
        seen_ids.add(rid) # Luôn đánh dấu đã xem để không kiểm tra lại
        
        creator = d.get("created_by", "")
        if is_renew_creator(creator):
            print(f"🎯 [SC Renew] Ticket {d['ticket_no']} do '{creator}' (Tái Ký) tạo ➔ Đang bắn Google Chat...", flush=True)
            sent = send_gchat_renew(d)
            if sent:
                notified_count += 1
        else:
            print(f"ℹ️ [SC Renew] Bỏ qua Ticket {d['ticket_no']} do '{creator}' tạo (Không thuộc Team Tái Ký).", flush=True)

    save_seen_tickets(seen_ids)
    return notified_count

def sc_renew_monitor_loop(interval_seconds=180):
    """
    Vòng lặp chạy ngầm vĩnh viễn quét mỗi interval_seconds (Mặc định 3 phút = 180s).
    """
    print(f"🚀 [SC Renew Monitor] Khởi động luồng quét tự động Ticket Tái Ký (Chu kỳ: {interval_seconds}s)...", flush=True)
    # Warm up lần đầu nếu file chưa tồn tại
    if not os.path.exists(SEEN_FILE):
        scan_and_notify_sc_renew(is_warmup=True)

    while True:
        try:
            time.sleep(interval_seconds)
            scan_and_notify_sc_renew(is_warmup=False)
        except Exception as e:
            print(f"⚠️ [SC Renew Monitor] Lỗi trong chu kỳ quét: {e}", flush=True)
            time.sleep(10)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["test", "dry", "check"]:
        print("🔍 Đang chạy kiểm tra quét thử Ticket SC Group Tái Ký...")
        headers = get_headers()
        url_view = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&viewname=20322"
        req = urllib.request.Request(url_view, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            p_html = resp.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>', p_html)
        print(f"Tìm thấy {len(matches)} ticket trong SC Group.")
        for mid in matches:
            dt = get_ticket_detail(mid, headers)
            if dt and is_renew_creator(dt.get("created_by", "")):
                print(f"👉 Tìm thấy ticket Tái Ký: {dt['ticket_no']} do '{dt['created_by']}' tạo.")
                if "--send" in sys.argv:
                    print("Bắn thử thông báo...")
                    send_gchat_renew(dt)
                else:
                    send_gchat_renew(dt, dry_run=True)
                break
    else:
        sc_renew_monitor_loop(180)
