import sys
import os
import urllib.request
import urllib.parse
import json
import re
import html as html_lib
import time
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crm_api

if hasattr(sys.stdout, 'reconfigure') and sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure') and sys.stderr is not None:
    sys.stderr.reconfigure(encoding='utf-8')

def _load_staff_map():
    staff_map = {
        "8482": ("12982", "Lê Đức Nhật - HUE"),
        "8457": ("12031", "Đặng Lê Tiến Thành - HPG"),
        "8486": ("12432", "Mai Đức Minh - DNG"),
        "8466": ("12147", "Lê Cao Minh Đức - CTO"),
        "8465": ("13410", "Hồ Ngọc Thiên Hy - NTG"),
        "8469": ("11670", "Nguyễn Hưng Hải - GLI"),
        "8470": ("12146", "Lương Trọng Đạo - CTO"),
        "8178": ("11212", "Phan Ngọc Nguyên - BĐH"),
        "8458": ("12032", "Đặng Duy Khương - CTO"),
        "8460": ("12080", "Lê Minh Hiển - CTO"),
        "8461": ("12079", "Trịnh Đức Phong - LĐG"),
        "8489": ("12464", "Nguyễn Hà Anh Vũ - LĐG"),
        "8484": ("13759", "Trần Thanh Nam - VTU"),
        "8231": ("7487", "Thượng Thái Hiếu - SGN"),
        "8437": ("11161", "Nguyễn Đoàn Hưng Phát - SGN"),
        "8440": ("11197", "Doãn Việt Tùng - SGN"),
        "8447": ("11196", "Võ Khánh Duy - SGN"),
        "8448": ("13457", "Nguyễn Đỗ Nhật Minh"),
        "8462": ("13488", "Nguyễn Hoàng Khang"),
        "8467": ("13456", "Nguyễn Thành Đạt"),
        "8456": ("12030", "Nguyễn Việt Anh - HNI"),
        "8280": ("10675", "Vũ Minh Đức - HNI"),
        "8246": ("6881", "Lê Văn Bách - HNI"),
        "8492": ("13460", "Nguyễn Thành Nam - HNI"),
        "8483": ("13740", "Ngô Trọng Nam Khánh - Customer Success"),
        "8201": ("11216", "Nguyễn Ái Quốc - Coacher"),
        "8845": ("8845", "SC Group"),
        "sc": ("8845", "SC Group"),
        "sc_group": ("8845", "SC Group")
    }
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staff_mapping_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                c_data = json.load(f)
                staff_entries = c_data.get("staff", {})
                for sid, sinfo in staff_entries.items():
                    staff_map[str(sid)] = (str(sinfo.get("internal_id")), sinfo.get("name", str(sid)))
        except Exception:
            pass
    return staff_map

STAFF_MAP = _load_staff_map()

def get_headers():
    c_str, _ = crm_api.get_session()
    return {
        "content-type": "application/x-www-form-urlencoded",
        "cookie": c_str or "",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

def resolve_record_id(query):
    query_str = str(query).strip()
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    
    def extract_entry_id(html_text):
        rows = re.findall(r'<tr[^>]*class=["\'][\w\s]*listViewEntries[\w\s]*["\'][^>]*>.*?</tr>', html_text, re.DOTALL)
        for r in rows:
            m = re.search(r'data-id=["\'](\d+)["\']', r) or re.search(r'record=(\d+)', r)
            if m:
                return m.group(1)
        return None

    # 1. Ticket No format (e.g. TT8802410)
    if "TT" in query_str.upper():
        m_code = re.search(r'TT\d+', query_str, re.IGNORECASE)
        code = m_code.group(0).upper() if m_code else query_str
        url = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&search_params=" + urllib.parse.quote(f'[[["ticket_no","c","{code}"]]]')
        try:
            req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            rec_id = extract_entry_id(html)
            if rec_id:
                return rec_id
        except Exception:
            pass

    # 2. Number string (Retailer ID or Record ID)
    if query_str.isdigit():
        # Search HelpDesk by retailer_id (newest first)
        url_hd = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&orderby=createdtime&sortorder=DESC&search_params=" + urllib.parse.quote(f'[[["retailer_id","c","{query_str}"]]]')
        try:
            req = urllib.request.Request(url_hd, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            rec_id = extract_entry_id(html)
            if rec_id:
                return rec_id
        except Exception:
            pass

        # If no HelpDesk found, search CSKHSC by retailer_id (newest first)
        url_sc = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&orderby=createdtime&sortorder=DESC&search_params=" + urllib.parse.quote(f'[[["retailer_id","c","{query_str}"]]]')
        try:
            req = urllib.request.Request(url_sc, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            rec_id = extract_entry_id(html)
            if rec_id:
                return rec_id
        except Exception:
            pass

        # If no search matches, it might be a direct record ID
        return query_str

    # 3. Text search by Store Name / Domain (e.g. 'nhanongcafe', newest first)
    for field in ["contact_id", "ticket_title", "description"]:
        url_t = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&orderby=createdtime&sortorder=DESC&search_params=" + urllib.parse.quote(f'[[["{field}","c","{query_str}"]]]')
        try:
            req = urllib.request.Request(url_t, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            rec_id = extract_entry_id(html)
            if rec_id:
                return rec_id
        except Exception:
            pass

    url_sc_t = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&orderby=createdtime&sortorder=DESC&search_params=" + urllib.parse.quote(f'[[["description","c","{query_str}"]]]')
    try:
        req = urllib.request.Request(url_sc_t, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        rec_id = extract_entry_id(html)
        if rec_id:
            return rec_id
    except Exception:
        pass

    raise ValueError(f"Không tìm thấy Ticket hoặc đơn ATC nào khớp với tên gian hàng '{query_str}' trên CRM!")

def get_fresh_csrf(rec_id):
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rec_id}"
    req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        m = re.search(r'csrfMagicToken\s*=\s*["\']([^"\']+)["\']', html) or re.search(r'name=["\']__vtrftk["\']\s+value=["\']([^"\']+)["\']', html)
        _, csrf_token = crm_api.get_session()
        return m.group(1) if m else csrf_token, html
    except Exception:
        _, csrf_token = crm_api.get_session()
        return csrf_token, ""

def extract_list_entry_ids(html_text):
    """
    Extracts true CRM record IDs from a ListView HTML page.
    Prevents capturing custom view dropdown IDs (e.g. 6583, 17346).
    """
    if not html_text:
        return []
    # 1. Match from <tr class="listViewEntries" data-id="...">
    tr_matches = re.findall(r'<tr[^>]*class=["\'][\w\s]*listViewEntries[\w\s]*["\'][^>]*data-id=["\'](\d{6,})["\']', html_text)
    if tr_matches:
        return list(dict.fromkeys(tr_matches))
        
    # 2. Match from detail links record=(\d+)
    link_matches = re.findall(r'(?:module=\w+&(?:amp;)?view=Detail&(?:amp;)?record=)(\d{6,})', html_text)
    if link_matches:
        return list(dict.fromkeys(link_matches))
            
    return []

def find_linked_atcs(ticket_no, retailer_id):
    atc_rec_ids = []
    queries = []
    headers = get_headers()
    cookie_str = headers.get("cookie", "")

    m_code = re.search(r'TT\d+', str(ticket_no), re.IGNORECASE)
    code = m_code.group(0).upper() if m_code else str(ticket_no)

    if code:
        queries.extend([
            f'[[["description","c","{code}"]]]',
            f'[[["ticket_no","c","{code}"]]]',
            f'[[["cskhsc_no","c","{code}"]]]'
        ])

    for q in queries:
        url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params=" + urllib.parse.quote(q)
        try:
            req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            for aid in extract_list_entry_ids(html):
                if aid not in atc_rec_ids:
                    atc_rec_ids.append(aid)
        except Exception:
            pass

    if not atc_rec_ids and retailer_id:
        url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&orderby=createdtime&sortorder=DESC&search_params=" + urllib.parse.quote(f'[[["retailer_id","c","{retailer_id}"]]]')
        try:
            req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            for aid in extract_list_entry_ids(html):
                if aid not in atc_rec_ids:
                    atc_rec_ids.append(aid)
        except Exception:
            pass

    return atc_rec_ids[:3]

def get_latest_atc_for_retailer(retailer_id):
    """
    Finds the most recent ATC record for a retailer on CRM.
    Returns dict with aid, no, status, assigned_user or None.
    """
    if not retailer_id:
        return None
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&orderby=createdtime&sortorder=DESC&search_params=" + urllib.parse.quote(f'[[["retailer_id","c","{retailer_id}"]]]')
    try:
        req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        entry_ids = extract_list_entry_ids(html)
        if not entry_ids:
            return None
            
        aid = entry_ids[0]
        details = get_atc_details(aid)
        
        return {
            "aid": aid,
            "no": details.get("no") or f"ATC-{aid}",
            "status": details.get("status") or "Chưa xác định",
            "assigned_user": details.get("assigned_user") or "Chưa có người nhận"
        }
    except Exception:
        return None

def extract_clean_field_value(html_text, field_id):
    pattern = rf'id=["\']\w+_detailView_fieldValue_{field_id}["\'][^>]*>(.*?)</td>'
    m_td = re.search(pattern, html_text, re.DOTALL)
    if not m_td:
        m_fallback = re.search(rf'{field_id}.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
        if not m_fallback:
            return ""
        raw = m_fallback.group(1)
    else:
        raw = m_td.group(1)
        
    m_val = re.search(r'<span[^>]*class=["\'][^"\']*value[^"\']*["\'][^>]*>(.*?)</span>', raw, re.DOTALL)
    if m_val:
        cleaned = m_val.group(1)
    else:
        cleaned = re.sub(r'<select.*?</select>', '', raw, flags=re.DOTALL)
    val = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cleaned)).strip()
    return re.sub(r'\s+', ' ', val)

def get_atc_status(atc_id):
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={atc_id}"
    try:
        req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        return extract_clean_field_value(html, "cskhcs_status")
    except Exception:
        return ""

def get_ticket_full_info(query):
    rec_id = resolve_record_id(query)
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    d_url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rec_id}"
    req = urllib.request.Request(d_url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    ticket_no = extract_clean_field_value(html, "ticket_no") or f"TT-{rec_id}"
    status = extract_clean_field_value(html, "ticketstatus")
    assigned_user = extract_clean_field_value(html, "assigned_user_id")
    retailer_id = extract_clean_field_value(html, "retailer_id")
    title = extract_clean_field_value(html, "ticket_title")

    atcs = find_linked_atcs(ticket_no, retailer_id)

    return {
        "rec_id": rec_id,
        "ticket_no": ticket_no,
        "status": status,
        "assigned_user": assigned_user,
        "retailer_id": retailer_id,
        "title": title,
        "atcs": atcs,
        "link": d_url
    }

def is_allowed_pool_owner(owner_name):
    """
    Checks if owner is in an unassigned queue / pool (SC group, Chăm sóc khách hàng trực tiếp).
    Returns True if allowed to transfer, False if already assigned to a specific staff member.
    """
    if not owner_name:
        return True
    owner_str = str(owner_name).strip()
    owner_lower = owner_str.lower()
    
    allowed_groups = [
        "chăm sóc khách hàng trực tiếp",
        "chăm sóc khách hàng hỗ trợ trực tiếp",
        "sc group",
        "sc_group",
        "nhóm sc",
        "sc-group",
        "hỗ trợ trực tiếp",
        "chăm sóc khách hàng",
        "cskh",
        "marketing group",
        "marketing_group"
    ]
    
    for g in allowed_groups:
        if g in owner_lower:
            return True
            
    # If owner has a staff code (e.g. 8178 - Phan Ngọc Nguyên, 8464, etc.) or any name -> Not allowed
    if re.search(r'^\d{4}\s*-\s*', owner_str) or re.search(r'\b(8\d{3}|1\d{4})\b', owner_str):
        return False
        
    return False

def get_atc_details(atc_id):
    """
    Fetches status and assigned owner for an ATC record.
    """
    if not atc_id or len(str(atc_id)) < 6:
        return {"status": "", "assigned_user": "", "retailer_id": "", "no": ""}
        
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={atc_id}"
    try:
        req = urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
        status = extract_clean_field_value(html, "cskhcs_status")
        assigned_user = extract_clean_field_value(html, "assigned_user_id")
        retailer_id = extract_clean_field_value(html, "retailer_id")
        atc_no = extract_clean_field_value(html, "cskhcs_no") or f"ATC-{atc_id}"
        
        return {"status": status, "assigned_user": assigned_user, "retailer_id": retailer_id, "no": atc_no}
    except Exception:
        return {"status": "", "assigned_user": "", "retailer_id": "", "no": ""}

def do_transfer(query, staff_code):
    """
    Transfers ticket or ATC and associated uncompleted records to staff_code.
    Enforces status protection and owner pool validation rules.
    """
    rec_id = resolve_record_id(query)
    staff_code_str = str(staff_code).strip()
    if staff_code_str not in STAFF_MAP:
        info = crm_api.get_staff_info(staff_code_str)
        if info and info.get("internal_id"):
            STAFF_MAP[staff_code_str] = (str(info["internal_id"]), info.get("name", staff_code_str))
        else:
            raise ValueError(f"Mã nhân viên {staff_code_str} không hợp lệ!")
    
    user_id, staff_name = STAFF_MAP[staff_code_str]
    csrf, html = get_fresh_csrf(rec_id)
    headers = get_headers()
    
    ticket_no = extract_clean_field_value(html, "ticket_no") or f"TT-{rec_id}"
    hd_status = extract_clean_field_value(html, "ticketstatus")
    hd_user = extract_clean_field_value(html, "assigned_user_id")
    
    url_post = "https://kvcrm.kiotviet.vn/index.php"

    # CASE A: If it's a HelpDesk ticket
    if hd_status:
        if any(k in hd_status.lower() for k in ["closed", "completed", "đã làm", "đã đóng", "hủy", "rejected"]):
            raise ValueError(f"Ticket {ticket_no} đang ở trạng thái '{hd_status}' (ĐÃ HOÀN THÀNH/HỦY) ➔ KHÔNG ĐƯỢC PHÉP CHUYỂN CHO NGUỜI KHÁC!")

        if not is_allowed_pool_owner(hd_user):
            if not (hd_user and str(staff_code_str) in hd_user):
                raise ValueError(f"Ticket {ticket_no} hiện ĐÃ CÓ NGƯỜI XỬ LÝ là '{hd_user}' ➔ Theo quy tắc KHÔNG ĐƯỢC CHUYỂN! Vui lòng kiểm tra lại.")

        retailer_id = extract_clean_field_value(html, "retailer_id")

        data_hd = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "HelpDesk", "action": "SaveAjax",
            "record": rec_id, "field": "assigned_user_id", "value": user_id
        }).encode('utf-8')
        try:
            with urllib.request.urlopen(urllib.request.Request(url_post, data=data_hd, headers=headers), timeout=10) as resp:
                resp_h = resp.read().decode('utf-8', errors='ignore')
                if '"success":false' in resp_h:
                    # Fallback to ChangeOwnerAction if SaveAjax was blocked by permissions
                    data_co = urllib.parse.urlencode({
                        "__vtrftk": csrf, "module": "HelpDesk", "action": "ChangeOwnerAction",
                        "changeOwnerId": user_id, "selected_ids[]": rec_id
                    }).encode('utf-8')
                    urllib.request.urlopen(urllib.request.Request(url_post, data=data_co, headers=headers), timeout=10)
        except Exception:
            data_co = urllib.parse.urlencode({
                "__vtrftk": csrf, "module": "HelpDesk", "action": "ChangeOwnerAction",
                "changeOwnerId": user_id, "selected_ids[]": rec_id
            }).encode('utf-8')
            try:
                urllib.request.urlopen(urllib.request.Request(url_post, data=data_co, headers=headers), timeout=10)
            except Exception:
                pass

        atcs = find_linked_atcs(ticket_no, retailer_id)[:3]
        transferred_atcs = []
        
        valid_aids = [aid for aid in atcs if aid and len(str(aid)) >= 6]
        atc_infos = []
        if valid_aids:
            with ThreadPoolExecutor(max_workers=min(len(valid_aids), 4)) as ex:
                atc_infos = list(ex.map(get_atc_details, valid_aids))

        for aid, atc_info in zip(valid_aids, atc_infos):
            atc_st = atc_info.get("status", "")
            atc_u = atc_info.get("assigned_user", "")
            atc_ret = atc_info.get("retailer_id", "")
            
            # Must be a valid ATC record with status or retailer_id
            if not atc_st and not atc_ret:
                continue
                
            if retailer_id and atc_ret and atc_ret != retailer_id:
                print(f"⚠️ Skip transfer for ATC {aid} because retailer mismatch ({atc_ret} != {retailer_id})!")
                continue

            if any(k in atc_st.lower() for k in ["completed", "closed", "đã làm", "đã đóng", "hủy", "cancelled"]):
                print(f"⚠️ Skip transfer for ATC {aid} because status is '{atc_st}' (ĐÃ LÀM)!")
                continue
                
            if not is_allowed_pool_owner(atc_u):
                print(f"⚠️ Skip transfer for ATC {aid} because already assigned to '{atc_u}'!")
                continue
                
            data_sc = urllib.parse.urlencode({
                "__vtrftk": csrf, "module": "CSKHSC", "action": "ChangeOwnerAction",
                "viewname": "", "excluded_ids[]": "", "changeOwnerId": user_id,
                "search_params": "[[]]", "selected_ids[]": aid
            }).encode('utf-8')
            urllib.request.urlopen(urllib.request.Request(url_post, data=data_sc, headers=headers))
            transferred_atcs.append(aid)

        latest_atc = get_latest_atc_for_retailer(retailer_id)
        description = extract_clean_field_value(html, "description")
        store_name = extract_clean_field_value(html, "cf_website") or extract_clean_field_value(html, "contact_id")
        if store_name:
            store_name = store_name.strip().splitlines()[0].strip()
            if " " in store_name:
                first_tok = store_name.split()[0].strip()
                if first_tok.lower() in store_name.lower():
                    store_name = first_tok
        return rec_id, ticket_no, retailer_id, transferred_atcs, latest_atc, description, store_name

    # CASE B: Direct CSKHSC record
    else:
        atc_info = get_atc_details(rec_id)
        atc_st = atc_info.get("status", "")
        atc_u = atc_info.get("assigned_user", "")
        retailer_id = atc_info.get("retailer_id", "")
        
        if any(k in atc_st.lower() for k in ["completed", "closed", "đã làm", "hủy", "cancelled"]):
            raise ValueError(f"Đơn ATC {rec_id} đang ở trạng thái '{atc_st}' (ĐÃ HOÀN THÀNH/HỦY) ➔ KHÔNG ĐƯỢC PHÉP CHUYỂN CHO NGUỜI KHÁC!")

        if not is_allowed_pool_owner(atc_u):
            raise ValueError(f"Đơn ATC {rec_id} hiện ĐÃ CÓ NGƯỜI XỬ LÝ là '{atc_u}' ➔ Theo quy tắc KHÔNG ĐƯỢC CHUYỂN! Vui lòng kiểm tra lại.")

        data_sc = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "CSKHSC", "action": "ChangeOwnerAction",
            "viewname": "", "excluded_ids[]": "", "changeOwnerId": user_id,
            "search_params": "[[]]", "selected_ids[]": rec_id
        }).encode('utf-8')
        urllib.request.urlopen(urllib.request.Request(url_post, data=data_sc, headers=headers))

        latest_atc = {"aid": rec_id, "no": f"ATC-{rec_id}", "status": atc_st, "assigned_user": f"{staff_code} - {staff_name}"}
        description = extract_clean_field_value(html, "description")
        store_name = extract_clean_field_value(html, "cf_website") or extract_clean_field_value(html, "retailer_name") or retailer_id
        if store_name:
            store_name = store_name.strip().splitlines()[0].strip()
            if " " in store_name:
                first_tok = store_name.split()[0].strip()
                if first_tok.lower() in store_name.lower():
                    store_name = first_tok
        return rec_id, f"ATC-{rec_id}", retailer_id, [rec_id], latest_atc, description, store_name

def do_reject(query, comment=None):
    """
    Rejects ticket, marks CSKHSC as Huy, appends comment and saves ModComment.
    """
    if not comment:
        comment = "khu vực không có SC"

    rec_id = resolve_record_id(query)
    csrf, html = get_fresh_csrf(rec_id)
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    
    hd_status = extract_clean_field_value(html, "ticketstatus")
    url_post = "https://kvcrm.kiotviet.vn/index.php"
    
    # CASE A: If HelpDesk record exists
    if hd_status:
        m_tno = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticket_no["\'][^>]*>(.*?)</td>', html, re.DOTALL) or re.search(r'TT\d+', html)
        ticket_no = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_tno.group(0)).strip()) if m_tno else f"TT-{rec_id}"
        retailer_id = extract_clean_field_value(html, "retailer_id")

        d1 = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "HelpDesk", "action": "SaveAjax",
            "record": rec_id, "field": "ticketdenyreason", "value": "Khách hàng hủy yêu cầu"
        }).encode('utf-8')
        urllib.request.urlopen(urllib.request.Request(url_post, data=d1, headers=headers))

        d2 = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "HelpDesk", "action": "SaveAjax",
            "record": rec_id, "field": "ticketstatus", "value": "Rejected"
        }).encode('utf-8')
        urllib.request.urlopen(urllib.request.Request(url_post, data=d2, headers=headers))

        if comment:
            d_cmt = urllib.parse.urlencode({
                "__vtrftk": csrf, "module": "ModComments", "action": "SaveAjax",
                "commentcontent": comment, "related_to": rec_id
            }).encode('utf-8')
            urllib.request.urlopen(urllib.request.Request(url_post, data=d_cmt, headers=headers))

        atcs = find_linked_atcs(ticket_no, retailer_id)
        for aid in atcs:
            data_sc = urllib.parse.urlencode({
                "__vtrftk": csrf, "module": "CSKHSC", "action": "SaveAjax",
                "record": aid, "field": "cskhcs_status", "value": "Huy"
            }).encode('utf-8')
            urllib.request.urlopen(urllib.request.Request(url_post, data=data_sc, headers=headers))

            if comment:
                try:
                    url_d = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={aid}"
                    req_d = urllib.request.Request(url_d, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req_d, timeout=8) as resp_d:
                        html_d = resp_d.read().decode('utf-8', errors='ignore')
                    m_desc = re.search(r'id=["\']CSKHSC_detailView_fieldValue_description["\'][^>]*>(.*?)</td>', html_d, re.DOTALL) or re.search(r'Mô tả.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html_d, re.IGNORECASE | re.DOTALL)
                    old_desc = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_desc.group(1)).strip()) if m_desc else ""
                    old_desc = re.sub(r'\s+', ' ', old_desc)
                    new_desc = f"{old_desc}\n - Lý do hủy: {comment}".strip() if old_desc else f"Lý do hủy: {comment}"
                    
                    data_desc = urllib.parse.urlencode({
                        "__vtrftk": csrf, "module": "CSKHSC", "action": "SaveAjax",
                        "record": aid, "field": "description", "value": new_desc
                    }).encode('utf-8')
                    urllib.request.urlopen(urllib.request.Request(url_post, data=data_desc, headers=headers))

                    # Also save ModComment to ATC
                    d_cmt_atc = urllib.parse.urlencode({
                        "__vtrftk": csrf, "module": "ModComments", "action": "SaveAjax",
                        "commentcontent": comment, "related_to": aid
                    }).encode('utf-8')
                    urllib.request.urlopen(urllib.request.Request(url_post, data=d_cmt_atc, headers=headers))
                except Exception as ex_desc:
                    print(f"⚠️ Error appending description/comment to ATC {aid}: {ex_desc}")

        return rec_id, ticket_no, retailer_id, atcs
    else:
        # CASE B: Direct CSKHSC record
        url_d = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={rec_id}"
        req_d = urllib.request.Request(url_d, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_d, timeout=8) as resp_d:
            html_d = resp_d.read().decode('utf-8', errors='ignore')
        m_c = re.search(r'csrfMagicToken\s*=\s*["\']([^"\']+)["\']', html_d) or re.search(r'name=["\']__vtrftk["\']\s+value=["\']([^"\']+)["\']', html_d)
        if m_c:
            csrf = m_c.group(1)
        retailer_id = extract_clean_field_value(html_d, "retailer_id")
        
        # 1. Update status to Huy
        data_sc = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "CSKHSC", "action": "SaveAjax",
            "record": rec_id, "field": "cskhcs_status", "value": "Huy"
        }).encode('utf-8')
        urllib.request.urlopen(urllib.request.Request(url_post, data=data_sc, headers=headers))

        # 2. Append description
        m_desc = re.search(r'id=["\']CSKHSC_detailView_fieldValue_description["\'][^>]*>(.*?)</td>', html_d, re.DOTALL) or re.search(r'Mô tả.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html_d, re.IGNORECASE | re.DOTALL)
        old_desc = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_desc.group(1)).strip()) if m_desc else ""
        old_desc = re.sub(r'\s+', ' ', old_desc)
        new_desc = f"{old_desc}\n - Lý do hủy: {comment}".strip() if old_desc else f"Lý do hủy: {comment}"

        data_desc = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "CSKHSC", "action": "SaveAjax",
            "record": rec_id, "field": "description", "value": new_desc
        }).encode('utf-8')
        urllib.request.urlopen(urllib.request.Request(url_post, data=data_desc, headers=headers))

        # 3. Add ModComment
        d_cmt = urllib.parse.urlencode({
            "__vtrftk": csrf, "module": "ModComments", "action": "SaveAjax",
            "commentcontent": comment, "related_to": rec_id
        }).encode('utf-8')
        urllib.request.urlopen(urllib.request.Request(url_post, data=d_cmt, headers=headers))

        return rec_id, f"ATC-{rec_id}", retailer_id, [rec_id]

def do_switch_online(query, support_type="CSKHOI_DVKH"):
    """
    Switches an ATC to online support (CSKHOI_DVKH, CSKHNA_DVKH, CSKHOI_T15_DVKH, CSKHNI_DVKH).
    """
    rec_id = resolve_record_id(query)
    st_clean = support_type.lower()
    if "t15" in st_clean:
        c_type = "CSKHOI_T15_DVKH"
        group_label = "CSKH T15 - DVKH"
    elif "na" in st_clean:
        c_type = "CSKHNA_DVKH"
        group_label = "CSKH NA - DVKH"
    elif "ni" in st_clean:
        c_type = "CSKHNI_DVKH"
        group_label = "CSKH NI - DVKH"
    else:
        c_type = "CSKHOI_DVKH"
        group_label = "CSKH OI - DVKH"
    
    headers = get_headers()
    headers["x-requested-with"] = "XMLHttpRequest"
    
    # 1. Check can change form
    url_check = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=checkCanChangeForm&record={rec_id}"
    req_check = urllib.request.Request(url_check, headers=headers)
    with urllib.request.urlopen(req_check, timeout=10) as resp_check:
        res_c = json.loads(resp_check.read().decode('utf-8'))
        
    # 2. Switch
    url_switch = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&action=SwitchOnlineSupport&record={rec_id}&cskhcs_type={c_type}"
    req_switch = urllib.request.Request(url_switch, headers=headers)
    with urllib.request.urlopen(req_switch, timeout=10) as resp_switch:
        res_s = json.loads(resp_switch.read().decode('utf-8'))
        success = (res_s.get("success") is True or res_s.get("result", {}).get("success") is True)
        
    return success, rec_id, group_label, res_s

def do_assign_region(region_name_or_id, quantity, staff_code, ward_filter=None):
    """
    Auto-assigns quantity data from region to staff_code.
    """
    from crm_assigner import assign_region_data
    from reporter import log_assignment

    regions_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regions.json")
    with open(regions_file, "r", encoding="utf-8") as f:
        regions = json.load(f)
        
    reg_clean = str(region_name_or_id).strip().lower()
    target_reg = next((r for r in regions if r["id"].lower() == reg_clean or reg_clean in r["name"].lower()), None)
    if not target_reg:
        raise ValueError(f"Không tìm thấy khu vực '{region_name_or_id}' trong regions.json!")

    staff_code_str = str(staff_code).strip()
    staff_info = STAFF_MAP.get(staff_code_str, (staff_code_str, staff_code_str))[1]
    
    if ward_filter is None:
        w_map = target_reg.get("ward_staff_map", {})
        if staff_code_str in w_map:
            val = w_map[staff_code_str]
            if isinstance(val, dict):
                primary_wards = val.get("primary", [])
                backup_wards = val.get("backup", [])
                qty_val = 999999 if str(quantity).lower() in ("all", "tatca", "tất cả") else int(quantity)
                if primary_wards:
                    # Thử lấy Phường chính trước
                    success, msg = assign_region_data(target_reg["url"], qty_val, staff_code_str, ward_filter=primary_wards)
                    if not success and ("Không tìm thấy data" in msg or "không tìm thấy record" in msg.lower()):
                        if backup_wards:
                            print(f"ℹ️ Phường chính không có data treo, tự động chuyển sang Phường Backup ({', '.join(backup_wards[:3])})...")
                            success, msg = assign_region_data(target_reg["url"], qty_val, staff_code_str, ward_filter=backup_wards)
                            if success:
                                msg = f"[Lấy từ Phường Backup] {msg}"
                elif backup_wards:
                    success, msg = assign_region_data(target_reg["url"], qty_val, staff_code_str, ward_filter=backup_wards)
                    if success:
                        msg = f"[Lấy từ Phường Backup] {msg}"
                else:
                    success, msg = assign_region_data(target_reg["url"], qty_val, staff_code_str, ward_filter=None)
                if success:
                    log_assignment(target_reg["name"], target_reg.get("coacher", "quoc"), staff_code_str, f"{staff_code_str} - {staff_info}", qty_val)
                return success, msg, target_reg["name"], staff_code_str, staff_info
            else:
                ward_filter = val

    qty_val = 999999 if str(quantity).lower() in ("all", "tatca", "tất cả") else int(quantity)
    success, msg = assign_region_data(target_reg["url"], qty_val, staff_code_str, ward_filter=ward_filter)
    if success:
        log_assignment(target_reg["name"], target_reg.get("coacher", "quoc"), staff_code_str, f"{staff_code_str} - {staff_info}", qty_val)
    return success, msg, target_reg["name"], staff_code_str, staff_info

def do_auto_assign_under_10(batch_size=8, threshold=10, dry_run=False, log_callback=None):
    """
    Tự động quét View 20154 và phân công thêm data (mặc định 8 data) cho nhân sự team Coacher Quốc đang giữ < 10 data.
    Khung giờ quét định kỳ: 06:30 sáng và 20:30 tối.
    Quy tắc phân bổ & ưu tiên khu vực:
      - 8460 (Hiển): Ưu tiên lấy từ kho Cà Mau (Camau) trước. Nếu Cà Mau thiếu, lấy bù từ Cần Thơ (Cantho).
      - 8470 (Đạo): Ưu tiên lấy từ kho Sóc Trăng (Soctrang) trước. Nếu Sóc Trăng thiếu, lấy bù từ Cần Thơ (Cantho).
      - 8178 (Nguyên): Lấy từ kho Quy Nhơn (Quynhon).
      - 8469 (Hải): Lấy từ kho Gia Lai (Gialai).
      - 8484 (Nam): Lấy từ kho Vũng Tàu (Vungtau).
      - Lâm Đồng (Lamdong - 8461 Phong, 8489 Vũ): Ưu tiên bạn đang giữ ít data hơn chia trước.
      - Cần Thơ (Cantho - 8458 Khương, 8466 Đức, và 8460/8470 nếu cần): Ưu tiên bạn đang giữ ít data nhất chia trước.
    """
    def log(m):
        if log_callback: log_callback(m)
        else: print(m, flush=True)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    staff_file = os.path.join(base_dir, "staff.json")
    regions_file = os.path.join(base_dir, "regions.json")

    with open(staff_file, "r", encoding="utf-8") as f:
        all_staff_cfg = json.load(f)
    quoc_staff = all_staff_cfg.get("quoc", [])

    with open(regions_file, "r", encoding="utf-8") as f:
        all_regions = json.load(f)
    reg_map = {r["id"].lower(): r for r in all_regions if r.get("coacher") == "quoc"}

    log("🔍 Đang quét View 20154 trên CRM để kiểm tra số lượng ATC treo của từng nhân sự...")
    view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"
    rows = crm_api.fetch_crm_export(view_url)
    if not rows or len(rows) < 1:
        err = "❌ Không thể tải dữ liệu từ View 20154 trên CRM."
        log(err)
        return False, err, []

    headers = rows[0]
    if "Người xử lý" not in headers:
        err = "❌ Cột 'Người xử lý' không tồn tại trong View 20154."
        log(err)
        return False, err, []

    o_idx = headers.index("Người xử lý")
    staff_counts = {s["short_id"]: 0 for s in quoc_staff}
    staff_name_map = {}
    for s in quoc_staff:
        sid = s["short_id"]
        sname = s["name"]
        if " - " in sname:
            parts = sname.split(" - ")
            sname = f"{parts[0]} - {parts[1]}"
        staff_name_map[sid] = sname

    for row in rows[1:]:
        if len(row) > o_idx:
            owner = row[o_idx].strip()
            for sid in staff_counts:
                if owner.startswith(sid):
                    staff_counts[sid] += 1
                    break

    qualifying_staff = {sid: staff_counts[sid] for sid in staff_counts if staff_counts[sid] < threshold}

    if not qualifying_staff:
        mode_str = " (THỬ NGHIỆM)" if dry_run else ""
        msg = (
            f"🤖 **BÁO CÁO TỰ ĐỘNG CHIA DATA (< {threshold} ATC){mode_str}**\n"
            f"⏰ *Thời gian*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            f"🎉 **Tất cả {len(quoc_staff)} nhân sự team Coacher Quốc đều đang có >= {threshold} data.** Không cần đẩy thêm!"
        )
        log(msg)
        return True, msg, []

    import crm_assigner
    import reporter

    region_cache = {}
    def get_avail_count(reg_id):
        reg = reg_map.get(reg_id.lower())
        if not reg: return 0
        if reg_id.lower() not in region_cache:
            summary = crm_api.get_region_summary(reg["url"])
            region_cache[reg_id.lower()] = summary.get("total_unassigned", 0) if summary else 0
        return region_cache[reg_id.lower()]

    def consume_avail(reg_id, qty):
        if reg_id.lower() in region_cache:
            region_cache[reg_id.lower()] = max(0, region_cache[reg_id.lower()] - qty)

    assigned_records = []
    assigned_so_far = {sid: 0 for sid in qualifying_staff}

    # Helper thực thi chia 1 mẻ data
    def assign_batch(sid, reg_id, needed):
        reg = reg_map.get(reg_id.lower())
        if not reg or needed <= 0: return 0
        if reg_id.lower() == "hcm":
            w_map = reg.get("ward_staff_map", {}).get(sid, {})
            primary = w_map.get("primary", [])
            backup = w_map.get("backup", [])
            if dry_run:
                summary = crm_api.get_region_summary(reg["url"])
                w_counts = summary.get("wards", {}) if summary else {}
                if not primary and not backup:
                    avail_sum = sum(w_counts.values())
                    take = min(needed, avail_sum)
                    used_type = "Kho chung"
                else:
                    p_avail = sum(cnt for w, cnt in w_counts.items() if any(pw.lower() in w.lower() for pw in primary))
                    take = min(needed, p_avail)
                    used_type = "Phường chính"
                    if take == 0 and backup:
                        b_avail = sum(cnt for w, cnt in w_counts.items() if any(bw.lower() in w.lower() for bw in backup))
                        take = min(needed, b_avail)
                        used_type = "Phường Backup"
                if take > 0:
                    assigned_so_far[sid] += take
                    assigned_records.append({"sid": sid, "reg_id": reg_id, "reg_name": f"{reg['name']} ({used_type})", "qty": take})
                    return take
                return 0
            else:
                try:
                    success, a_msg, r_name, _, _ = do_assign_region("hcm", needed, sid)
                    if success:
                        m = re.search(r'Đã chuyển \*\*(\d+)\*\*', a_msg)
                        take = int(m.group(1)) if m else needed
                        assigned_so_far[sid] += take
                        reg_tag = f"{r_name} (Backup)" if "[Lấy từ Phường Backup]" in a_msg else r_name
                        assigned_records.append({"sid": sid, "reg_id": reg_id, "reg_name": reg_tag, "qty": take})
                        return take
                except Exception as e:
                    print(f"Lỗi chia HCM cho {sid}: {e}")
                return 0
        elif dry_run:
            avail = get_avail_count(reg_id)
            take = min(needed, avail)
            if take > 0:
                assigned_so_far[sid] += take
                consume_avail(reg_id, take)
                assigned_records.append({"sid": sid, "reg_id": reg_id, "reg_name": reg["name"], "qty": take})
                return take
            return 0
        else:
            success, a_msg = crm_assigner.assign_region_data(reg["url"], needed, sid)
            if success:
                m = re.search(r'Đã chuyển \*\*(\d+)\*\*', a_msg)
                take = int(m.group(1)) if m else needed
                assigned_so_far[sid] += take
                reporter.log_assignment(reg["name"], "quoc", sid, staff_name_map.get(sid, sid), take)
                assigned_records.append({"sid": sid, "reg_id": reg_id, "reg_name": reg["name"], "qty": take})
                return take
            return 0

    # 1. Tỉnh độc quyền 1-1
    if "8178" in qualifying_staff:
        assign_batch("8178", "quynhon", batch_size - assigned_so_far["8178"])
    if "8469" in qualifying_staff:
        assign_batch("8469", "gialai", batch_size - assigned_so_far["8469"])
    if "8484" in qualifying_staff:
        assign_batch("8484", "vungtau", batch_size - assigned_so_far["8484"])

    # 2. Lâm Đồng (Lamdong - 8461 & 8489)
    lamdong_candidates = [sid for sid in ["8461", "8489"] if sid in qualifying_staff]
    if lamdong_candidates:
        lamdong_candidates.sort(key=lambda x: staff_counts[x])
        for sid in lamdong_candidates:
            assign_batch(sid, "lamdong", batch_size - assigned_so_far[sid])

    # 3. 8460 (Hiển): Ưu tiên Cà Mau (Camau) trước
    if "8460" in qualifying_staff:
        assign_batch("8460", "camau", batch_size - assigned_so_far["8460"])

    # 4. 8470 (Đạo): Ưu tiên Sóc Trăng (Soctrang) trước
    if "8470" in qualifying_staff:
        assign_batch("8470", "soctrang", batch_size - assigned_so_far["8470"])

    # 5. Cần Thơ (Cantho): Phục vụ các bạn cần Cần Thơ (8458, 8466, và 8460/8470 nếu chưa đủ 8)
    cantho_candidates = []
    for sid in ["8458", "8466", "8460", "8470"]:
        if sid in qualifying_staff and (batch_size - assigned_so_far[sid]) > 0:
            cantho_candidates.append(sid)

    if cantho_candidates:
        cantho_candidates.sort(key=lambda x: (staff_counts[x] + assigned_so_far[x]))
        for sid in cantho_candidates:
            needed = batch_size - assigned_so_far[sid]
            if needed > 0:
                assign_batch(sid, "cantho", needed)

    # 6. Đồng Nai (Dongnai - 8437 Phát)
    if "8437" in qualifying_staff and (batch_size - assigned_so_far["8437"]) > 0:
        assign_batch("8437", "dongnai", batch_size - assigned_so_far["8437"])

    # 7. Hồ Chí Minh (Hcm - 8231, 8447, 8440, 8448, 8467, 8462, 8437)
    hcm_candidates = [sid for sid in ["8231", "8447", "8440", "8448", "8467", "8462", "8437"] if sid in qualifying_staff and (batch_size - assigned_so_far[sid]) > 0]
    if hcm_candidates:
        hcm_candidates.sort(key=lambda x: (staff_counts[x] + assigned_so_far[x]))
        for sid in hcm_candidates:
            needed = batch_size - assigned_so_far[sid]
            if needed > 0:
                assign_batch(sid, "hcm", needed)

    mode_str = " (CHẾ ĐỘ THỬ NGHIỆM - DRY RUN)" if dry_run else ""
    lines = [
        f"🤖 **BÁO CÁO TỰ ĐỘNG CHIA DATA (< {threshold} ATC){mode_str}**",
        f"⏰ *Thời gian thực hiện*: {time.strftime('%H:%M:%S %d/%m/%Y')}",
        f"🎯 *Chính sách*: Dưới {threshold} data ➔ Tự động đẩy thêm {batch_size} data\n",
        f"📍 **CHI TIẾT PHÂN CÔNG TỪNG NHÂN SỰ:**"
    ]

    total_assigned_sum = 0
    staff_action_count = 0

    for sid in sorted(qualifying_staff.keys(), key=lambda x: staff_counts[x]):
        init_c = staff_counts[sid]
        added = assigned_so_far.get(sid, 0)
        sname = staff_name_map.get(sid, sid)
        sub_items = [item for item in assigned_records if item["sid"] == sid]
        if sub_items:
            staff_action_count += 1
            total_assigned_sum += added
            detail_strs = [f"+{it['qty']} từ {it['reg_name']}" for it in sub_items]
            lines.append(
                f"• 👤 **{sname}**:\n"
                f"  - Ban đầu: `{init_c}` ATC treo\n"
                f"  - Đã cấp thêm: **+{added} data** ({', '.join(detail_strs)})\n"
                f"  - Tổng hiện tại: `{init_c + added}` ATC treo"
            )
        else:
            lines.append(
                f"• 👤 **{sname}**:\n"
                f"  - Ban đầu: `{init_c}` ATC treo\n"
                f"  - ⚠️ Không thể cấp thêm: Các kho khu vực tương ứng đã hết data treo!"
            )

    lines.append(f"\n📊 **TỔNG KẾT:**")
    lines.append(f"• Số nhân sự dưới ngưỡng (< {threshold}): `{len(qualifying_staff)}` nhân sự")
    lines.append(f"• Số nhân sự đã được cấp data: `{staff_action_count}` nhân sự")
    lines.append(f"• Tổng số data đã chia: `{total_assigned_sum}` data")

    full_report = "\n".join(lines)
    log(full_report)
    return True, full_report, assigned_records

def do_check_coacher_quoc():
    """
    Generates real-time holding & region summary report for Coacher Quốc.
    """
    import reporter
    return reporter.generate_daily_report_text()

def do_check_store_address(start_date, end_date):
    """
    Checks view 17629 and compares actual vs OTP contract addresses.
    """
    import check_store_address
    return check_store_address.check_address_by_date_range(start_date, end_date)

def do_check_sla(min_days=10, coacher="quoc"):
    """
    Scans all regions and staff for SLA breaches (>= min_days).
    """
    import datetime
    base_dir = os.path.dirname(os.path.abspath(__file__))
    regions_file = os.path.join(base_dir, "regions.json")
    staff_file = os.path.join(base_dir, "staff.json")
    
    with open(regions_file, "r", encoding="utf-8") as f:
        all_regions = json.load(f)
    with open(staff_file, "r", encoding="utf-8") as f:
        all_staff = json.load(f)
        
    target_regions = [r for r in all_regions if coacher == "all" or r.get("coacher") == coacher]
    target_staff = all_staff.get(coacher, []) if coacher != "all" else (all_staff.get("quoc", []) + all_staff.get("vietanh", []))
    now = datetime.datetime.now()

    def parse_retailer_id(raw):
        m = re.findall(r'\d{5,}', str(raw))
        return m[-1] if m else str(raw)

    def scan_region_sla(region):
        items = []
        rows = crm_api.fetch_crm_export(region['url'])
        if not rows or len(rows) < 2: return items
        headers = rows[0]
        try:
            r_idx = headers.index('Retailer ID')
            t_idx = headers.index('Thời gian tạo')
            c_idx = headers.index('Tỉnh/Thành phố')
            w_idx = headers.index('Xã/Phường/Thị trấn')
            o_idx = headers.index('Người xử lý')
        except: return items
        for row in rows[1:]:
            if len(row) <= max(r_idx, t_idx, c_idx, w_idx, o_idx): continue
            r_id = parse_retailer_id(row[r_idx])
            c_str = row[t_idx].strip()
            try:
                date_str = c_str.split()[0]
                c_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                sla_days = (now - c_date).days
                fmt_date = c_date.strftime('%d/%m/%Y')
            except: continue
            if sla_days >= int(min_days):
                items.append({
                    'retailer_id': r_id,
                    'created_time': c_str,
                    'fmt_date': fmt_date,
                    'city': row[c_idx].strip(),
                    'ward': row[w_idx].strip(),
                    'sla_days': sla_days,
                    'owner': row[o_idx].strip(),
                    'source': region['name']
                })
        return items

    def scan_staff_sla(staff_item):
        items = []
        staff_full_name = staff_item['name']
        short_name = staff_full_name
        if ' - ' in staff_full_name:
            parts = staff_full_name.split(' - ')
            short_name = f"{parts[0]} - {parts[1]}"
        encoded_name = urllib.parse.quote(staff_full_name)
        staff_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154&orderby=&sortorder=&search_params=%5B%5B%5B%22assigned_user_id%22%2C%22c%22%2C%22{encoded_name}%22%5D%5D%5D"
        rows = crm_api.fetch_crm_export(staff_url)
        if not rows or len(rows) < 2: return items
        headers = rows[0]
        try:
            r_idx = headers.index('Retailer ID')
            t_idx = headers.index('Thời gian tạo')
            c_idx = headers.index('Tỉnh/Thành phố')
            w_idx = headers.index('Xã/Phường/Thị trấn')
            o_idx = headers.index('Người xử lý')
        except: return items
        for row in rows[1:]:
            if len(row) <= max(r_idx, t_idx, c_idx, w_idx, o_idx): continue
            r_id = parse_retailer_id(row[r_idx])
            c_str = row[t_idx].strip()
            try:
                date_str = c_str.split()[0]
                c_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                sla_days = (now - c_date).days
                fmt_date = c_date.strftime('%d/%m/%Y')
            except: continue
            if sla_days >= int(min_days):
                items.append({
                    'retailer_id': r_id,
                    'created_time': c_str,
                    'fmt_date': fmt_date,
                    'city': row[c_idx].strip(),
                    'ward': row[w_idx].strip(),
                    'sla_days': sla_days,
                    'owner': short_name,
                    'source': short_name
                })
        return items

    with ThreadPoolExecutor(max_workers=8) as executor:
        r_results = list(executor.map(scan_region_sla, target_regions))
        s_results = list(executor.map(scan_staff_sla, target_staff))

    all_region_sla = [item for sub in r_results for item in sub]
    all_staff_sla = [item for sub in s_results for item in sub]

    total_region_count = len(all_region_sla)
    total_staff_count = len(all_staff_sla)
    grand_total_sla = total_region_count + total_staff_count

    staff_groups = {}
    for item in all_staff_sla:
        owner = item['owner']
        if owner not in staff_groups: staff_groups[owner] = []
        staff_groups[owner].append(item)

    sorted_staff = sorted(staff_groups.items(), key=lambda x: len(x[1]), reverse=True)

    part_staff_lines = []
    for owner, items_list in sorted_staff:
        items_list.sort(key=lambda x: x['sla_days'], reverse=True)
        part_staff_lines.append(f"👤 **{owner}** (Trễ `{len(items_list)}` đơn):")
        for it in items_list[:5]:
            part_staff_lines.append(f"  • Retailer ID: `{it['retailer_id']}` | **{it['fmt_date']} ({it['sla_days']} ngày)** | {it['city']} - {it['ward']}")
        if len(items_list) > 5:
            part_staff_lines.append(f"  _... và {len(items_list)-5} đơn trễ SLA khác_")
        part_staff_lines.append("")

    region_groups = {}
    for item in all_region_sla:
        reg_name = item['source']
        if reg_name not in region_groups: region_groups[reg_name] = []
        region_groups[reg_name].append(item)

    sorted_regions = sorted(region_groups.items(), key=lambda x: len(x[1]), reverse=True)

    part_region_lines = []
    for reg_name, items_list in sorted_regions:
        items_list.sort(key=lambda x: x['sla_days'], reverse=True)
        part_region_lines.append(f"📍 **{reg_name}** (Trễ `{len(items_list)}` data chưa chia):")
        for it in items_list[:5]:
            part_region_lines.append(f"  • Retailer ID: `{it['retailer_id']}` | **{it['fmt_date']} ({it['sla_days']} ngày)** | {it['city']} - {it['ward']}")
        if len(items_list) > 5:
            part_region_lines.append(f"  _... và {len(items_list)-5} data trễ SLA chưa chia khác_")
        part_region_lines.append("")

    report_text = (
        f"🚨 **BÁO CÁO CẢNH BÁO TRỄ SLA (>= {min_days} NGÀY)**\n"
        f"⏰ *Thời gian quét:* {now.strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        f"💼 **1. ĐƠN TREO CỦA NHÂN SỰ TRỄ SLA (Tổng: `{total_staff_count}` đơn):**\n"
        + ("\n".join(part_staff_lines) if part_staff_lines else "  _Không có nhân sự nào có đơn trễ SLA._\n") + "\n"
        f"📍 **2. DATA TỒN ĐỌNG CÁC TỈNH TRỄ SLA CHƯA CHIA (Tổng: `{total_region_count}` data):**\n"
        + ("\n".join(part_region_lines) if part_region_lines else "  _Không có khu vực nào trễ SLA chưa chia._\n") + "\n"
        f"🔥 **TỔNG CỘNG TẤT CẢ DATA TRỄ SLA:** `{grand_total_sla}` data\n"
    )
    return report_text

def do_check_tickets(viewname="17811", is_gchat=False):
    """
    Scans HelpDesk View 17811 ('Quốc SC treo - team') and View 20322 ('SC group treo').
    If is_gchat=True, injects <users/{gid}> mentions from gchat_user_map.json.
    """
    cookie_str, _ = crm_api.get_session()
    headers = {"cookie": cookie_str, "user-agent": "Mozilla/5.0"}
    
    gchat_map = {}
    if is_gchat:
        map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gchat_user_map.json")
        if os.path.exists(map_path):
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    gchat_map = json.load(f)
            except Exception:
                gchat_map = {}

    team_tickets = []
    for page in range(1, 10):
        url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&viewname=17811&page={page}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            h = resp.read().decode('utf-8', errors='ignore')
        rows = re.findall(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>(.*?)</tr>', h, re.DOTALL)
        if not rows:
            break
        for rec_id, row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
            if len(cells) > 14:
                t_no = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[1]))).strip()
                gh_name = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[5]))).strip()
                ret_id = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[8]))).strip()
                st = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[13]))).strip()
                owner = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[14]))).strip() or "Chưa phân công"
                team_tickets.append({
                    "rec_id": rec_id,
                    "ticket_no": t_no,
                    "gh_name": gh_name,
                    "retailer_id": ret_id,
                    "status": st,
                    "owner": owner
                })

    staff_tickets = {}
    for t in team_tickets:
        u = t["owner"]
        if " - " in u:
            parts = u.split(" - ")
            short_u = f"{parts[0]} - {parts[1]}"
        else:
            short_u = u
        staff_tickets.setdefault(short_u, []).append(t)

    sorted_staff = sorted(staff_tickets.items(), key=lambda x: len(x[1]), reverse=True)
    total_team_tk = len(team_tickets)

    part1_lines = []
    counts = [len(v) for _, v in sorted_staff]
    max_c = max(counts) if counts else -1
    min_c = min(counts) if counts else -1

    for s_name, t_list in sorted_staff:
        count = len(t_list)
        if count == max_c and max_c > min_c:
            icon = "🔴"
            tag = " *(Nhiều nhất - Cần xử lý gấp)*"
        elif count == min_c and max_c > min_c:
            icon = "🟢"
            tag = ""
        else:
            icon = "🟡"
            tag = ""
        
        m_code = re.search(r'(\d{4})', s_name)
        code = m_code.group(1) if m_code else ""
        if is_gchat and code and code in gchat_map and gchat_map[code].get("gchat_id"):
            gid = gchat_map[code]["gchat_id"]
            user_label = f"*{code}* - <users/{gid}>"
        else:
            user_label = f"**{s_name}**"

        part1_lines.append(f"{icon} {user_label}: `{count}` Ticket{tag}")
        for t in t_list:
            gh_info = f"`{t['gh_name']}`" if t['gh_name'] else f"`{t['retailer_id']}`"
            part1_lines.append(f"   ▫️ {t['ticket_no']} | GH: {gh_info} | TT: {t['status']}")

    unassigned_tickets = []
    for page in range(1, 10):
        url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&viewname=20322&page={page}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            h = resp.read().decode('utf-8', errors='ignore')
        rows = re.findall(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>(.*?)</tr>', h, re.DOTALL)
        if not rows:
            break
        for rec_id, row_html in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
            if len(cells) > 1:
                t_no = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[1])).strip())
                unassigned_tickets.append(t_no)

    unassigned_count = len(unassigned_tickets)
    grand_total = total_team_tk + unassigned_count

    report_text = (
        f"🚨 *BÁO CÁO THỐNG KÊ TICKET (TK) TREO - COACHER QUỐC* 🚨\n"
        f"⏰ *Thời gian xuất báo cáo*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        f"📢 *YÊU CẦU TOÀN TEAM SC LƯU Ý:*\n"
        f"👉 **Ai xử lý xong thì ĐÓNG TICKET NGAY, tuyệt đối không để treo!**\n"
        f"👉 **Trường hợp chưa xử lý xong BẮT BUỘC PHẢI VÀO CMT cập nhật tiến độ/lý do.**\n"
        f"⚠️ **OM đang kiểm tra chất lượng rất gắt và BẮT PHẠT RẤT NẶNG các trường hợp để treo không cmt!**\n\n"
        f"💼 *1. DANH SÁCH NHÂN SỰ ĐANG GIỮ TICKET TREO (Tổng: `{total_team_tk}` TK treo):*\n"
        + ("\n".join(part1_lines) if part1_lines else "  - _Hiện không có Ticket treo._") + "\n\n"
        f"📍 *2. TICKET CHƯA PHÂN CÔNG (SC Group treo):* `{unassigned_count}` Ticket\n\n"
        f"🔥 *TỔNG CỘNG TẤT CẢ TICKET (TK) TREO: `{grand_total}` Ticket*\n\n"
        f"⚡ _Các bạn được tag đích danh ở trên chủ động vào kiểm tra xử lý ngay nhé!_"
    )
    return report_text

def do_send_ticket_gchat():
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    webhook_url = cfg.get("gchat_webhook")
    if not webhook_url:
        return False, "Chưa cấu hình Google Chat Webhook."
    
    text = do_check_tickets(is_gchat=True)
    
    def send_chunk(chunk):
        payload = {"text": chunk}
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
            
    try:
        if len(text) > 4000:
            mid = text[:4000].rfind('\n\n')
            if mid == -1: mid = 3900
            send_chunk(text[:mid])
            time.sleep(1)
            send_chunk(text[mid:])
        else:
            send_chunk(text)
        return True, text
    except Exception as e:
        return False, f"Lỗi gửi Google Chat: {e}"

def send_transfer_gchat(rec_id, ticket_no, store_name, retailer_id, staff_code, staff_info, atcs, latest_atc=None, description="", dry_run=False):
    """
    Sends a real-time notification to Google Chat when a Ticket/ATC transfer succeeds,
    tagging the assigned staff member via <users/{gid}> if mapped in gchat_user_map.json.
    """
    try:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if not os.path.exists(config_file):
            return False, "config.json không tồn tại"
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        webhook_url = cfg.get("gchat_webhook")
        if not webhook_url:
            return False, "Chưa cấu hình gchat_webhook trong config.json"

        gchat_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gchat_user_map.json")
        gchat_map = {}
        if os.path.exists(gchat_map_file):
            try:
                with open(gchat_map_file, "r", encoding="utf-8") as f:
                    gchat_map = json.load(f)
            except:
                gchat_map = {}

        staff_code_str = str(staff_code).strip()
        user_mention = ""
        user_display = f"*{staff_code_str} - {staff_info}*"
        
        # Check mapping for Google Chat ID
        if staff_code_str in gchat_map and gchat_map[staff_code_str].get("gchat_id"):
            gid = str(gchat_map[staff_code_str]["gchat_id"]).strip()
            if gid:
                user_mention = f"<users/{gid}>"
                user_display = f"{user_mention} (*{staff_code_str} - {staff_info}*)"

        # Format ATC section
        if atcs:
            atc_part = f"• *ATC liên quan*: `{', '.join(atcs)}` (Đã chuyển sang {staff_code_str})"
        else:
            atc_part = "• *ATC liên quan*: Không có ATC liên quan ở SC GROUP"
            if latest_atc and isinstance(latest_atc, dict):
                atc_part += f"\n• *ATC gần nhất*: `{latest_atc.get('no', '')}` (Trạng thái: `{latest_atc.get('status', '')}`, Người xử lý: `{latest_atc.get('assigned_user', '')}`)"
            else:
                atc_part += "\n• *ATC gần nhất*: _Không tìm thấy ATC nào trên hệ thống_"

        # Format Description section
        desc_part = ""
        if description and str(description).strip():
            d_clean = str(description).strip()
            if len(d_clean) > 800:
                d_clean = d_clean[:800] + "..."
            desc_part = f"\n• *Mô tả (Description)*:\n```\n{d_clean}\n```"

        store_str = f"`{store_name}`" if store_name else "_Chưa xác định_"
        ret_str = f"`{retailer_id}`" if retailer_id else "_Chưa xác định_"
        tag_header = f"🔔 {user_mention} *Bạn có Ticket / ATC mới được bàn giao!*\n\n" if user_mention else ""

        gchat_text = (
            f"✅ *BÀN GIAO THÀNH CÔNG* #Ticket\n\n"
            f"{tag_header}"
            f"• *Mã Ticket/Gốc*: `{ticket_no}` (ID: `{rec_id}`)\n"
            f"• *Tên gian hàng (Tên GH)*: {store_str}\n"
            f"• *Retailer ID*: {ret_str}\n"
            f"• *Nhân sự nhận*: {user_display}\n"
            f"{atc_part}"
            f"{desc_part}\n\n"
            f"⚡ *Thời gian hoàn thành*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n"
            f"#Ticket"
        )

        if dry_run:
            return True, gchat_text

        payload = {"text": gchat_text}
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=UTF-8"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            success = (resp.status == 200)
            if success:
                print(f"🎉 [GChat Transfer] Đã bắn thông báo bàn giao {ticket_no} -> {staff_code_str} lên Google Chat thành công!", flush=True)
            return success, gchat_text
    except Exception as e:
        err_msg = f"Lỗi gửi Google Chat: {e}"
        print(f"⚠️ [GChat Transfer] {err_msg}", flush=True)
        return False, err_msg

def do_check_sc_group(full_desc=False):
    """
    Scans View 20322 ('SC group treo') and returns a formatted report with Creator (Người tạo), Store, Retailer, Phone, Title, Time, Owner, and Description.
    """
    headers = get_headers()
    url_view = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&viewname=20322"
    
    rec_ids = []
    for page in range(1, 10):
        p_url = f"{url_view}&page={page}"
        req = urllib.request.Request(p_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                p_html = resp.read().decode('utf-8', errors='ignore')
            matches = re.findall(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>', p_html)
            if not matches:
                break
            for mid in matches:
                if mid not in rec_ids:
                    rec_ids.append(mid)
        except Exception:
            break

    if not rec_ids:
        return "🎉 Hiện tại hàng đợi SC Group (View 20322) KHÔNG CÓ TICKET TREO NÀO!"

    def get_detail(rid):
        url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rid}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
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
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        details = list(ex.map(get_detail, rec_ids))
    details = [d for d in details if d is not None]

    lines = [
        f"🎯 *DANH SÁCH {len(details)} TICKET TREO Ở SC GROUP (VIEW 20322):*\n"
    ]
    for i, d in enumerate(details, 1):
        phone_str = f" | **SĐT**: `{d['phone']}`" if d['phone'] else ""
        if full_desc:
            desc_formatted = "\n".join(f"     > {line}" for line in d['desc'].splitlines() if line.strip())
            desc_block = f"   • **Mô tả chi tiết**:\n{desc_formatted}\n"
        else:
            first_line = d['desc'].splitlines()[0] if d['desc'] else ""
            desc_short = (first_line[:150] + "...") if len(first_line) > 150 else first_line
            desc_block = f"   • **Mô tả**: `{desc_short}`\n"

        lines.append(
            f"{i}. **[{d['ticket_no']}]({d['crm_url']})**\n"
            f"   • **Tên GH**: `{d['store']}` *(Retailer ID: `{d['retailer_id']}`)*\n"
            f"   • **Khách hàng**: {d['contact']}{phone_str}\n"
            f"   • **Người tạo**: **{d['created_by']}**\n"
            f"   • **Thời gian tạo**: {d['created_time']}\n"
            f"   • **Tiêu đề**: {d['title']}\n"
            f"{desc_block}"
        )
    return "\n".join(lines)

def do_check_store(store_query):
    """
    Super-fast parallel search across HelpDesk, CSKHSC, Contacts, and Potentials for any store name or retailer ID.
    """
    from concurrent.futures import ThreadPoolExecutor
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    q = str(store_query).strip()
    
    retailer_ids = []
    if q.isdigit() and len(q) >= 6:
        retailer_ids.append(q)
        
    tickets_found = []
    atcs_found = []

    def search_hd_desc():
        url = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&search_params=" + urllib.parse.quote(f'[[["description","c","{q}"]]]')
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r:
                return list(dict.fromkeys(re.findall(r'module=HelpDesk&view=Detail&record=(\d+)', r.read().decode('utf-8', errors='ignore'))))
        except: return []

    def search_hd_title():
        url = "https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&search_params=" + urllib.parse.quote(f'[[["ticket_title","c","{q}"]]]')
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r:
                return list(dict.fromkeys(re.findall(r'module=HelpDesk&view=Detail&record=(\d+)', r.read().decode('utf-8', errors='ignore'))))
        except: return []

    def search_sc_desc():
        url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params=" + urllib.parse.quote(f'[[["description","c","{q}"]]]')
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r:
                return list(dict.fromkeys(re.findall(r'module=CSKHSC&view=Detail&record=(\d+)', r.read().decode('utf-8', errors='ignore'))))
        except: return []

    def search_contacts():
        url = "https://kvcrm.kiotviet.vn/index.php?module=Contacts&view=List&search_params=" + urllib.parse.quote(f'[[["cf_retailer_name","c","{q}"]]]')
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r:
                return list(dict.fromkeys(re.findall(r'module=Contacts&view=Detail&record=(\d+)', r.read().decode('utf-8', errors='ignore'))))
        except: return []

    with ThreadPoolExecutor(max_workers=4) as ex:
        f_hd_desc = ex.submit(search_hd_desc)
        f_hd_title = ex.submit(search_hd_title)
        f_sc_desc = ex.submit(search_sc_desc)
        f_cont = ex.submit(search_contacts)
        
        hd_ids = list(dict.fromkeys(f_hd_desc.result() + f_hd_title.result()))
        sc_ids = f_sc_desc.result()
        cont_ids = f_cont.result()

    # Extract details for HelpDesk tickets
    for hid in hd_ids:
        u = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={hid}"
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r_h:
                h_d = r_h.read().decode('utf-8', errors='ignore')
            m_no = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticket_no["\'][^>]*>(.*?)</td>', h_d, re.DOTALL)
            m_ret = re.search(r'id=["\']HelpDesk_detailView_fieldValue_retailer_id["\'][^>]*>(.*?)</td>', h_d, re.DOTALL)
            m_st = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticketstatus["\'][^>]*>(.*?)</td>', h_d, re.DOTALL)
            m_ow = re.search(r'id=["\']HelpDesk_detailView_fieldValue_assigned_user_id["\'][^>]*>(.*?)</td>', h_d, re.DOTALL)
            m_c = re.search(r'id=["\']HelpDesk_detailView_fieldValue_createdtime["\'][^>]*>(.*?)</td>', h_d, re.DOTALL)
            m_desc = re.search(r'id=["\']HelpDesk_detailView_fieldValue_description["\'][^>]*>(.*?)</td>', h_d, re.DOTALL)

            r_id = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ret.group(1)).strip()) if m_ret else ""
            if r_id: retailer_ids.append(r_id)

            tickets_found.append({
                "rec_id": hid,
                "ticket_no": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_no.group(1)).strip()) if m_no else hid,
                "retailer_id": r_id,
                "status": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_st.group(1)).strip()) if m_st else "",
                "owner": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ow.group(1)).strip()) if m_ow else "",
                "created_time": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_c.group(1)).strip()) if m_c else "",
                "desc": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_desc.group(1)).strip()) if m_desc else "",
                "link": u
            })
        except: pass

    # If retailer_ids found, search CSKHSC by retailer_id
    retailer_ids = list(dict.fromkeys(retailer_ids))
    for rid in retailer_ids:
        url_sc_ret = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params=" + urllib.parse.quote(f'[[["retailer_id","c","{rid}"]]]')
        try:
            with urllib.request.urlopen(urllib.request.Request(url_sc_ret, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r_s:
                sc_ids.extend(re.findall(r'module=CSKHSC&view=Detail&record=(\d+)', r_s.read().decode('utf-8', errors='ignore')))
        except: pass

    sc_ids = list(dict.fromkeys(sc_ids))
    for aid in sc_ids:
        u = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={aid}"
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"}), timeout=8) as r_a:
                h_a = r_a.read().decode('utf-8', errors='ignore')
            m_no = re.search(r'id=["\']CSKHSC_detailView_fieldValue_cskhsc_no["\'][^>]*>(.*?)</td>', h_a, re.DOTALL)
            m_ret = re.search(r'id=["\']CSKHSC_detailView_fieldValue_retailer_id["\'][^>]*>(.*?)</td>', h_a, re.DOTALL)
            m_st = re.search(r'id=["\']CSKHSC_detailView_fieldValue_cskhcs_status["\'][^>]*>(.*?)</td>', h_a, re.DOTALL)
            m_ow = re.search(r'id=["\']CSKHSC_detailView_fieldValue_assigned_user_id["\'][^>]*>(.*?)</td>', h_a, re.DOTALL)
            m_c = re.search(r'id=["\']CSKHSC_detailView_fieldValue_createdtime["\'][^>]*>(.*?)</td>', h_a, re.DOTALL)
            m_desc = re.search(r'id=["\']CSKHSC_detailView_fieldValue_description["\'][^>]*>(.*?)</td>', h_a, re.DOTALL)

            atcs_found.append({
                "atc_id": aid,
                "atc_no": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_no.group(1)).strip()) if m_no else aid,
                "retailer_id": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ret.group(1)).strip()) if m_ret else "",
                "status": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_st.group(1)).strip()) if m_st else "",
                "owner": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ow.group(1)).strip()) if m_ow else "",
                "created_time": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_c.group(1)).strip()) if m_c else "",
                "desc": html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_desc.group(1)).strip()) if m_desc else "",
                "link": u
            })
        except: pass

    return {
        "store_query": q,
        "retailer_ids": retailer_ids,
        "tickets_count": len(tickets_found),
        "tickets": tickets_found,
        "atcs_count": len(atcs_found),
        "atcs": atcs_found
    }

def fetch_single_pot_info(query_str, headers):
    from bs4 import BeautifulSoup
    q_item = str(query_str).strip()
    if not q_item:
        return None

    pot_id = None
    # 1. Direct record ID check
    if q_item.isdigit() and len(q_item) >= 7 and int(q_item) > 50000000:
        url_check = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={q_item}"
        try:
            req = urllib.request.Request(url_check, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                h = resp.read().decode('utf-8', errors='ignore')
            if 'Potentials_detailView_fieldValue_potential_no' in h:
                pot_id = q_item
        except:
            pass

    # 2. Search Potentials if not direct ID
    if not pot_id:
        url_search = f"https://kvcrm.kiotviet.vn/index.php?module=Vtiger&view=BasicAjax&mode=showSearchResults&value={urllib.parse.quote(q_item)}"
        try:
            req = urllib.request.Request(url_search, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                h_s = resp.read().decode('utf-8', errors='ignore')
            
            soup_s = BeautifulSoup(h_s, 'html.parser')
            pot_rows = soup_s.find_all('tr', id=re.compile(r'Potentials_globalSearch'))
            candidates = []
            for tr in pot_rows:
                crmid = tr.get('data-crmid')
                tds = tr.find_all('td')
                if not crmid or not tds:
                    continue
                title = tds[0].get_text(separator=' ', strip=True) if len(tds) > 0 else ''
                status = tds[1].get_text(separator=' ', strip=True) if len(tds) > 1 else ''
                created_time = tds[3].get_text(separator=' ', strip=True) if len(tds) > 3 else ''
                candidates.append({
                    'crmid': crmid,
                    'title': title,
                    'status': status,
                    'created_time': created_time
                })
            
            # Ưu tiên Hợp đồng có trạng thái 'Thành công' gần nhất (Closed Won)
            success_candidates = [
                c for c in candidates 
                if any(w in c['status'].lower() for w in ['thành công', 'thanh cong', 'closed won'])
            ]
            if success_candidates:
                success_candidates.sort(key=lambda x: x['created_time'], reverse=True)
                pot_id = success_candidates[0]['crmid']
            elif candidates:
                # Nếu không có HĐ Thành công, lấy HĐ mới nhất
                candidates.sort(key=lambda x: x['created_time'], reverse=True)
                pot_id = candidates[0]['crmid']
        except Exception:
            pass

    if not pot_id:
        return {
            "query": q_item,
            "pot_id": "N/A",
            "retailer_id": q_item if q_item.isdigit() else "N/A",
            "potential_name": "Không tìm thấy",
            "contact_name": "N/A",
            "phone": "N/A",
            "addr": "Không tìm thấy HĐ",
            "ward": "N/A",
            "city": "N/A",
            "email": "N/A",
            "passport": "N/A",
            "owner": "N/A",
            "status": "N/A",
            "created_time": "N/A",
            "link": ""
        }

    # Fetch detail
    url_d = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    try:
        req_d = urllib.request.Request(url_d, headers=headers)
        with urllib.request.urlopen(req_d, timeout=10) as resp_d:
            html_d = resp_d.read().decode('utf-8', errors='ignore')
    except Exception:
        html_d = ""

    soup = BeautifulSoup(html_d, 'html.parser')
    def get_f(fld):
        el = soup.find('td', id=f"Potentials_detailView_fieldValue_{fld}")
        return el.get_text(separator=' ', strip=True) if el else 'N/A'

    # KYC Data
    kyc_res = crm_api.get_kyc_data("Potentials", pot_id)
    kyc_info = kyc_res.get("result", {}) if kyc_res.get("success") else {}

    addr = kyc_info.get("addr") or get_f("cf_contact_street")
    phone = kyc_info.get("phone_not_hiden") or kyc_info.get("phone") or get_f("cf_mobile")
    email = kyc_info.get("email") or get_f("cf_email")
    passport = kyc_info.get("other_parsed", {}).get("passport") or get_f("cf_passport")

    return {
        "query": q_item,
        "pot_id": pot_id,
        "retailer_id": get_f("retailer_id"),
        "potential_name": get_f("potentialname"),
        "contact_name": get_f("contact_id"),
        "phone": phone,
        "addr": addr,
        "ward": get_f("cf_state"),
        "city": get_f("cf_city"),
        "email": email,
        "passport": passport if passport != "N/A" else "",
        "owner": get_f("assigned_user_id"),
        "status": get_f("sales_stage"),
        "created_time": get_f("createdtime"),
        "link": f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    }

def do_check_pot(query):
    """
    Search and fetch detailed information for Potentials (Opportunities / Hợp đồng) records,
    including decrypted KYC data (Address, Phone, Email, CCCD/Passport).
    Supports single or batch queries (comma-separated, multiple IDs, or path to txt/xlsx/csv file).
    Automatically exports batch results to potentials_kyc_export.xlsx.
    """
    import pandas as pd
    from concurrent.futures import ThreadPoolExecutor

    headers = get_headers()
    queries = []

    if isinstance(query, list):
        queries = [str(x).strip() for x in query if str(x).strip()]
    elif isinstance(query, str):
        query_str = query.strip()
        # Check if query is an existing file
        if os.path.exists(query_str):
            ext = os.path.splitext(query_str)[1].lower()
            try:
                if ext in ['.xlsx', '.xls']:
                    df_in = pd.read_excel(query_str)
                    col = None
                    for c in df_in.columns:
                        if any(k in str(c).lower() for k in ['retailer', 'pot', 'id', 'sdt', 'phone']):
                            col = c
                            break
                    if col is None: col = df_in.columns[0]
                    queries = [str(x).strip() for x in df_in[col].dropna() if str(x).strip()]
                elif ext == '.csv':
                    df_in = pd.read_csv(query_str)
                    col = df_in.columns[0]
                    queries = [str(x).strip() for x in df_in[col].dropna() if str(x).strip()]
                else:
                    with open(query_str, 'r', encoding='utf-8') as f:
                        queries = [line.strip() for line in f if line.strip()]
            except Exception as e:
                return f"⚠️ Lỗi đọc file {query_str}: {e}"
        else:
            # Split by comma, semicolon, space, newline
            parts = [p.strip() for p in re.split(r'[,;\s\n]+', query_str) if p.strip()]
            queries = parts

    if not queries:
        return "⚠️ Vui lòng cung cấp ít nhất 1 Retailer ID, mã Potentials hoặc SĐT để tra cứu."

    # Single mode
    if len(queries) == 1:
        item = fetch_single_pot_info(queries[0], headers)
        if not item or item.get("pot_id") == "N/A":
            return f"❌ Không tìm thấy Hợp đồng / Cơ hội (Potentials) nào với từ khóa: `{queries[0]}`"

        report = []
        report.append(f"🎯 **CHI TIẾT CƠ HỘI / HỢP ĐỒNG (POTENTIALS)**: `{item['pot_id']}`")
        report.append(f"• **Tên Hợp đồng**: {item['potential_name']}")
        report.append(f"• **Retailer ID**: `{item['retailer_id']}`")
        report.append(f"• **Khách hàng**: {item['contact_name']}")
        report.append(f"• **Người xử lý**: {item['owner']}")
        report.append(f"• **Tình trạng / Giai đoạn**: {item['status']}")
        report.append(f"• **Thời gian tạo**: {item['created_time']}")
        report.append(f"• **Tỉnh / Thành phố**: {item['city']}")
        report.append(f"• **Xã / Phường / Thị trấn**: {item['ward']}")
        report.append("---")
        report.append("🔓 **THÔNG TIN GIẢI MÃ KYC (CHI TIẾT BẢO MẬT)**:")
        report.append(f"• 📍 **Địa chỉ kinh doanh chi tiết**: **{item['addr']}**")
        report.append(f"• 📞 **Số điện thoại**: `{item['phone']}`")
        report.append(f"• ✉️ **Email**: `{item['email']}`")
        if item.get('passport'):
            report.append(f"• 🪪 **CCCD / Passport**: `{item['passport']}`")
        report.append(f"• 🔗 **Link CRM**: {item['link']}")
        return "\n".join(report)

    # Batch mode
    print(f"🚀 Đang tiến hành quét và giải mã KYC hàng loạt cho {len(queries)} bản ghi...")
    results = []
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_pot_info, q, headers) for q in queries]
        for f in futures:
            res_item = f.result()
            if res_item:
                results.append(res_item)
            completed += 1
            if completed % 25 == 0 or completed == len(queries):
                print(f"   ⏳ Đã hoàn thành: {completed}/{len(queries)}...")

    # Export to Excel
    export_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "potentials_kyc_export.xlsx")
    df = pd.DataFrame(results)
    col_mapping = {
        "query": "Từ khóa tìm kiếm",
        "retailer_id": "Retailer ID",
        "pot_id": "Mã HĐ (Potentials ID)",
        "potential_name": "Tên Hợp đồng",
        "contact_name": "Khách hàng",
        "phone": "Số điện thoại (KYC)",
        "addr": "Địa chỉ kinh doanh chi tiết (KYC)",
        "ward": "Xã / Phường",
        "city": "Tỉnh / Thành phố",
        "passport": "CCCD / Passport (KYC)",
        "email": "Email (KYC)",
        "owner": "Người xử lý",
        "status": "Giai đoạn",
        "created_time": "Ngày tạo",
        "link": "Link CRM"
    }
    df_export = df[[c for c in col_mapping.keys() if c in df.columns]].rename(columns=col_mapping)
    try:
        df_export.to_excel(export_path, index=False)
        export_msg = f"📁 **Đã xuất file Excel chi tiết**: `{export_path}`"
    except Exception as ex:
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"potentials_kyc_export_{ts}.xlsx")
            df_export.to_excel(alt_path, index=False)
            export_msg = f"📁 **Đã xuất file Excel (do file chính đang được mở trong máy)**: `{alt_path}`"
        except Exception:
            export_msg = f"⚠️ Không thể xuất file Excel: {ex}"

    # Build Markdown table
    lines = [
        f"📊 **BẢNG TỔNG HỢP GIẢI MÃ KYC HỢP ĐỒNG POTENTIALS ({len(results)} bản ghi)**:\n",
        "| STT | Retailer ID | Tên HĐ / Khách | SĐT (KYC) | Địa chỉ kinh doanh chi tiết (KYC) | Tỉnh / Thành phố | Người xử lý |",
        "| :---: | :---: | :--- | :---: | :--- | :--- | :--- |"
    ]
    for idx, r in enumerate(results, 1):
        ret_val = r.get('retailer_id', 'N/A')
        title_val = r.get('potential_name', 'N/A')[:35]
        phone_val = r.get('phone', 'N/A')
        addr_val = r.get('addr', 'N/A')
        city_val = r.get('city', 'N/A')
        owner_val = r.get('owner', 'N/A').split('-')[0].strip() if '-' in r.get('owner', '') else r.get('owner', 'N/A')[:20]
        lines.append(f"| {idx} | `{ret_val}` | {title_val} | `{phone_val}` | **{addr_val}** | {city_val} | {owner_val} |")

    lines.append("\n" + export_msg)
    return "\n".join(lines)

def fetch_single_invoice_info(query_item, headers):
    from bs4 import BeautifulSoup
    q_str = str(query_item).strip()
    pot_id = None
    
    # 1. URL with record=
    if "record=" in q_str:
        m = re.search(r'record=(\d+)', q_str)
        if m:
            pot_id = m.group(1)
    elif q_str.isdigit() and len(q_str) >= 8:
        url_test = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={q_str}"
        try:
            req_t = urllib.request.Request(url_test, headers=headers)
            with urllib.request.urlopen(req_t, timeout=6) as resp_t:
                html_t = resp_t.read().decode('utf-8', errors='ignore')
            if 'Potentials_detailView_fieldValue_potentialname' in html_t or 'Potentials_detailView_fieldValue_cf_pot_website' in html_t:
                pot_id = q_str
        except Exception:
            pass

    # 2. Search Potentials by keyword (Retailer ID, Phone, Store name)
    if not pot_id:
        url_search = f"https://kvcrm.kiotviet.vn/index.php?module=Home&view=UnifiedSearchAjax&search_module=Potentials&search_value={urllib.parse.quote(q_str)}"
        try:
            req_s = urllib.request.Request(url_search, headers=headers)
            with urllib.request.urlopen(req_s, timeout=8) as resp_s:
                h_s = resp_s.read().decode('utf-8', errors='ignore')
            soup_s = BeautifulSoup(h_s, 'html.parser')
            pot_rows = soup_s.find_all('tr', id=re.compile(r'Potentials_globalSearch'))
            candidates = []
            for tr in pot_rows:
                crmid = tr.get('data-crmid')
                tds = tr.find_all('td')
                if not crmid or not tds:
                    continue
                title = tds[0].get_text(separator=' ', strip=True) if len(tds) > 0 else ''
                status = tds[1].get_text(separator=' ', strip=True) if len(tds) > 1 else ''
                created_time = tds[3].get_text(separator=' ', strip=True) if len(tds) > 3 else ''
                candidates.append({
                    'crmid': crmid,
                    'title': title,
                    'status': status,
                    'created_time': created_time
                })
            
            # Ưu tiên Hợp đồng có trạng thái 'Thành công' gần nhất (Closed Won)
            success_candidates = [
                c for c in candidates 
                if any(w in c['status'].lower() for w in ['thành công', 'thanh cong', 'closed won'])
            ]
            if success_candidates:
                success_candidates.sort(key=lambda x: x['created_time'], reverse=True)
                pot_id = success_candidates[0]['crmid']
            elif candidates:
                candidates.sort(key=lambda x: x['created_time'], reverse=True)
                pot_id = candidates[0]['crmid']
        except Exception:
            pass

    if not pot_id:
        return {
            "query": q_str,
            "pot_id": "N/A",
            "retailer_id": q_str if q_str.isdigit() else "N/A",
            "store_name": "Không tìm thấy",
            "contract_no": "N/A",
            "company_name": "N/A",
            "tax_code": "N/A",
            "invoice_addr": "Không tìm thấy HĐ",
            "email": "N/A",
            "contact_name": "N/A",
            "phone": "N/A",
            "owner": "N/A",
            "status": "N/A",
            "created_time": "N/A",
            "link": ""
        }

    # Fetch detail
    url_d = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    try:
        req_d = urllib.request.Request(url_d, headers=headers)
        with urllib.request.urlopen(req_d, timeout=10) as resp_d:
            html_d = resp_d.read().decode('utf-8', errors='ignore')
    except Exception:
        html_d = ""

    soup = BeautifulSoup(html_d, 'html.parser')
    def get_f(fld):
        el = soup.find('td', id=f"Potentials_detailView_fieldValue_{fld}")
        if not el: return ""
        sel = el.find('option', selected=True)
        if sel:
            return sel.get_text(separator=' ', strip=True)
        span = el.find('span', class_='value')
        if span:
            return span.get_text(separator=' ', strip=True)
        for s in el.find_all('select'):
            s.decompose()
        return el.get_text(separator=' ', strip=True)

    # KYC Data (unmasks email, address, phone)
    kyc_res = crm_api.get_kyc_data("Potentials", pot_id)
    kyc_data = kyc_res.get("result", {}) if kyc_res.get("success") else {}
    other_p = kyc_data.get("other_parsed", {})

    store_name = get_f("cf_pot_website") or get_f("potentialname")
    contract_no = get_f("cf_pot_contractid") or get_f("potential_no")
    company_name = get_f("company_name")
    tax_code = get_f("tax_code")
    
    # Invoice address: other_parsed -> kyc addr -> detail view
    invoice_addr = other_p.get("cf_pot_diachich") or kyc_data.get("addr") or get_f("cf_pot_diachich")
    if invoice_addr == "********": 
        invoice_addr = kyc_data.get("addr", "")
    
    # Email: kyc email -> detail view
    email = kyc_data.get("email") or get_f("cf_email")
    if email == "********": 
        email = ""

    phone = kyc_data.get("phone_not_hiden") or kyc_data.get("phone") or get_f("cf_mobile")
    ret_id = get_f("retailer_id")
    contact_name = get_f("contact_id")
    owner = get_f("assigned_user_id")
    status = get_f("sales_stage")
    created_time = get_f("createdtime")

    return {
        "query": q_str,
        "pot_id": pot_id,
        "retailer_id": ret_id,
        "store_name": store_name,
        "contract_no": contract_no,
        "company_name": company_name,
        "tax_code": tax_code,
        "invoice_addr": invoice_addr,
        "email": email,
        "contact_name": contact_name,
        "phone": phone,
        "owner": owner,
        "status": status,
        "created_time": created_time,
        "link": f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    }

def do_check_invoice(query, as_email=False):
    """
    Fetch invoice information from Potentials:
    - Tên gian hàng (Store name)
    - Số hợp đồng (Contract No)
    - Tên công ty (Company Name)
    - Mã số thuế (Tax Code)
    - Địa chỉ xuất hóa đơn (Invoice Address - decrypted from KYC)
    - Primary Email (decrypted from KYC)
    Supports single or batch queries (URL, ID, comma-separated, or file).
    If as_email=True, formats as ready-to-send email to Accounting team.
    """
    import pandas as pd
    from concurrent.futures import ThreadPoolExecutor

    headers = get_headers()
    queries = []

    if isinstance(query, list):
        queries = [str(x).strip() for x in query if str(x).strip()]
    elif isinstance(query, str):
        query_str = query.strip()
        if os.path.exists(query_str):
            ext = os.path.splitext(query_str)[1].lower()
            try:
                if ext in ['.xlsx', '.xls']:
                    df_in = pd.read_excel(query_str)
                    col = None
                    for c in df_in.columns:
                        if any(k in str(c).lower() for k in ['retailer', 'pot', 'id', 'sdt', 'phone', 'url', 'link']):
                            col = c
                            break
                    if col is None: col = df_in.columns[0]
                    queries = [str(x).strip() for x in df_in[col].dropna() if str(x).strip()]
                elif ext == '.csv':
                    df_in = pd.read_csv(query_str)
                    col = df_in.columns[0]
                    queries = [str(x).strip() for x in df_in[col].dropna() if str(x).strip()]
                else:
                    with open(query_str, 'r', encoding='utf-8') as f:
                        queries = [line.strip() for line in f if line.strip()]
            except Exception as e:
                return f"⚠️ Lỗi đọc file {query_str}: {e}"
        else:
            parts = [p.strip() for p in re.split(r'[,;\s\n]+', query_str) if p.strip()]
            queries = parts

    if not queries:
        return "⚠️ Vui lòng cung cấp link Potentials, mã Record ID, Retailer ID hoặc file danh sách."

    # Single mode
    if len(queries) == 1:
        item = fetch_single_invoice_info(queries[0], headers)
        if not item or item.get("pot_id") == "N/A":
            return f"❌ Không tìm thấy thông tin Hợp đồng / Xuất hóa đơn nào với từ khóa: `{queries[0]}`"

        store = item['store_name'] or 'N/A'
        contract = item['contract_no'] or 'N/A'
        company = item['company_name'] or '(Cá nhân / Chưa nhập)'
        tax = item['tax_code'] or '(Chưa có)'
        addr = item['invoice_addr'] or '(Chưa có)'
        email = item['email'] or '(Chưa có)'

        ret_suffix = f" (Retailer ID: {item['retailer_id']})" if item.get('retailer_id') and item['retailer_id'] != 'N/A' else ""
        
        if as_email:
            email_lines = [
                f"Đề xuất, xuất HDDT phần cứng trước cho khách hàng ({contract})",
                "",
                "Dear P. Kế toán, anh Tuấn",
                "Hiện có khách hàng mua phần cứng của bên mình và cần hỗ trợ xuất hoá đơn trước thông tin gian hàng như sau ạ.",
                f"Tên gian hàng: {store}{ret_suffix}",
                f"Số hợp đồng: {contract}",
                f"Tên công ty: {company}",
                f"Mã số thuế: {tax}",
                f"Địa chỉ xuất hóa đơn: {addr}",
                f"Primary Email: {email}",
                "",
                "Nhờ anh Tuấn phê duyệt và phòng kế toán hỗ trợ cho khách hàng giúp em ạ.",
                "em cảm ơn",
                "--",
                "+84945 344 775",
                "Nguyễn Ái Quốc - CS Coacher",
                "Trân Trọng !"
            ]
            return "\n".join(email_lines)

        report = [
            f"Tên gian hàng: {store}{ret_suffix}",
            f"Số hợp đồng: {contract}",
            f"Tên công ty: {company}",
            f"Mã số thuế: {tax}",
            f"Địa chỉ xuất hóa đơn: {addr}",
            f"Primary Email: {email}"
        ]
        return "\n".join(report)

    # Batch mode
    print(f"Đang tiến hành lấy thông tin xuất hóa đơn hàng loạt cho {len(queries)} bản ghi...")
    results = []
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_invoice_info, q, headers) for q in queries]
        for f in futures:
            res_item = f.result()
            if res_item:
                results.append(res_item)
            completed += 1
            if completed % 20 == 0 or completed == len(queries):
                print(f"   Đã hoàn thành: {completed}/{len(queries)}...")

    # Export to Excel
    export_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invoice_info_export.xlsx")
    df = pd.DataFrame(results)
    col_mapping = {
        "query": "Từ khóa tìm kiếm",
        "retailer_id": "Retailer ID",
        "pot_id": "Potentials ID",
        "store_name": "Tên gian hàng",
        "contract_no": "Số hợp đồng",
        "company_name": "Tên công ty",
        "tax_code": "Mã số thuế",
        "invoice_addr": "Địa chỉ xuất hóa đơn",
        "email": "Primary Email",
        "contact_name": "Khách hàng / Đại diện",
        "phone": "Số điện thoại",
        "owner": "Người xử lý",
        "status": "Giai đoạn",
        "created_time": "Ngày tạo",
        "link": "Link CRM"
    }
    df_export = df[[c for c in col_mapping.keys() if c in df.columns]].rename(columns=col_mapping)
    try:
        df_export.to_excel(export_path, index=False)
        export_msg = f"Đã xuất file Excel chi tiết: {export_path}"
    except Exception as ex:
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"invoice_info_export_{ts}.xlsx")
            df_export.to_excel(alt_path, index=False)
            export_msg = f"Đã xuất file Excel (do file chính đang mở): {alt_path}"
        except Exception:
            export_msg = f"Không thể xuất file Excel: {ex}"

    # Build Markdown table
    lines = [
        f"BẢNG TỔNG HỢP THÔNG TIN XUẤT HÓA ĐƠN ({len(results)} bản ghi):\n",
        "| STT | Retailer ID | Tên gian hàng | Số hợp đồng | Tên công ty | Mã số thuế | Địa chỉ xuất hóa đơn | Primary Email |",
        "| :---: | :---: | :--- | :--- | :--- | :---: | :--- | :--- |"
    ]
    for idx, r in enumerate(results, 1):
        ret_val = r.get('retailer_id', 'N/A')
        store_val = r.get('store_name', 'N/A')[:25]
        contract_val = r.get('contract_no', 'N/A')
        company_val = r.get('company_name', '')[:25] or '(Cá nhân)'
        tax_val = r.get('tax_code', '') or '-'
        addr_val = r.get('invoice_addr', 'N/A')
        email_val = r.get('email', '') or '-'
        lines.append(f"| {idx} | {ret_val} | {store_val} | {contract_val} | {company_val} | {tax_val} | {addr_val} | {email_val} |")

    lines.append("\n" + export_msg)
    return "\n".join(lines)

def do_check_phone(phone_query, target_staff=None):
    """
    Check single or batch phone numbers on CRM Global Search for HelpDesk tickets.
    Extracts: Số TK, Thời gian chỉnh sửa, Mô tả, Trạng thái TK, Tiêu đề, Tên GH, Người xử lý.
    Filters by target_staff (e.g. '8222' or '8222 - Bùi Đăng Quang') if provided.
    """
    import re, html as html_lib, urllib.parse, urllib.request
    from concurrent.futures import ThreadPoolExecutor

    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    req_headers = {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }

    # Extract all phone numbers from string (10-11 digits)
    raw_text = str(phone_query)
    phones = re.findall(r'(?:0|\+84)\d{9,10}', raw_text)
    if not phones:
        # Fallback split by comma or space
        parts = [p.strip() for p in re.split(r'[,;\s\n]+', raw_text) if p.strip()]
        phones = [p for p in parts if p.isdigit() and len(p) >= 9]

    if not phones:
        return f"⚠️ Không tìm thấy số điện thoại hợp lệ nào trong chuỗi: '{phone_query}'"

    target_staff_str = str(target_staff).strip().lower() if target_staff else None

    all_matched_tickets = []
    
    for p in phones:
        # Global search for HelpDesk
        url_tk = f"https://kvcrm.kiotviet.vn/index.php?module=Vtiger&view=BasicAjax&mode=showSearchResults&value={urllib.parse.quote(p)}&searchModule=HelpDesk"
        try:
            req = urllib.request.Request(url_tk, headers=req_headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_html = resp.read().decode('utf-8', errors='ignore')
            rows = re.findall(r'<tr[^>]*data-crmid=["\'](\d+)["\'][^>]*>(.*?)</tr>', res_html, re.DOTALL)
        except Exception:
            rows = []

        rec_ids = [r[0] for r in rows if r[0]]

        def fetch_ticket_info(rid):
            url_dt = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rid}"
            try:
                r_dt = urllib.request.Request(url_dt, headers=req_headers)
                with urllib.request.urlopen(r_dt, timeout=8) as r_resp:
                    dt_html = r_resp.read().decode('utf-8', errors='ignore')

                # Owner
                m_owner = re.search(r'name=["\']assigned_user_id["\'][^>]*>.*?<option[^>]*value=["\'](\d+)["\'][^>]*selected[^>]*>(.*?)</option>', dt_html, re.DOTALL)
                if not m_owner:
                    m_owner = re.search(r'id=["\']HelpDesk_detailView_fieldValue_assigned_user_id["\'][^>]*>.*?<option[^>]*selected[^>]*>(.*?)</option>', dt_html, re.DOTALL)
                owner_name = html_lib.unescape(m_owner.group(2)).strip() if m_owner else "N/A"
                owner_name = re.sub(r'\s+', ' ', owner_name)

                # Ticket No
                m_tno = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticket_no["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                tno = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_tno.group(1)).strip()) if m_tno else f"Ticket_{rid}"
                tno = re.sub(r'\s+', ' ', tno)

                # Modified time
                m_mod = re.search(r'id=["\']HelpDesk_detailView_fieldValue_modifiedtime["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL) or re.search(r'Thời gian chỉnh sửa.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                mod_time = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_mod.group(1)).strip()) if m_mod else "N/A"
                mod_time = re.sub(r'\s+', ' ', mod_time)

                # Status
                m_st_td = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticketstatus["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                if m_st_td:
                    m_opt = re.search(r'<option[^>]*selected[^>]*>(.*?)</option>', m_st_td.group(1), re.DOTALL)
                    if m_opt:
                        status_val = html_lib.unescape(m_opt.group(1)).strip()
                    else:
                        m_sp = re.search(r'<span[^>]*class=["\']value["\'][^>]*>(.*?)</span>', m_st_td.group(1), re.DOTALL)
                        status_val = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_sp.group(1) if m_sp else m_st_td.group(1))).strip()
                else:
                    status_val = "N/A"
                status_val = re.sub(r'\s+', ' ', status_val)

                # Title
                m_tt = re.search(r'id=["\']HelpDesk_detailView_fieldValue_ticket_title["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                title_val = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_tt.group(1)).strip()) if m_tt else "N/A"
                title_val = re.sub(r'\s+', ' ', title_val)

                # Store Name (HelpDesk uses cf_website as primary store name, fallback to contact_id)
                m_cf_web = re.search(r'id=["\']HelpDesk_detailView_fieldValue_cf_website["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                store_val = ""
                if m_cf_web:
                    m_sel = re.search(r'<option[^>]*selected[^>]*>(.*?)</option>', m_cf_web.group(1), re.DOTALL)
                    store_val = html_lib.unescape(m_sel.group(1)).strip() if m_sel else ""
                    if not store_val:
                        m_sp = re.search(r'<span[^>]*class=["\']value["\'][^>]*>(.*?)</span>', m_cf_web.group(1), re.DOTALL)
                        store_val = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_sp.group(1) if m_sp else m_cf_web.group(1))).strip()
                if not store_val:
                    m_store = re.search(r'id=["\']HelpDesk_detailView_fieldValue_contact_id["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL) or re.search(r'id=["\']HelpDesk_detailView_fieldValue_parent_id["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                    store_val = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_store.group(1)).strip()) if m_store else "N/A"
                store_val = re.sub(r'\s+', ' ', store_val)

                # Description
                m_desc = re.search(r'id=["\']HelpDesk_detailView_fieldValue_description["\'][^>]*>(.*?)</td>', dt_html, re.DOTALL)
                desc_val = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_desc.group(1)).strip()) if m_desc else "N/A"
                desc_val = re.sub(r'\s+', ' ', desc_val)

                return {
                    "phone": p,
                    "record_id": rid,
                    "ticket_no": tno,
                    "modified_time": mod_time,
                    "status": status_val,
                    "title": title_val,
                    "store": store_val,
                    "owner": owner_name,
                    "description": desc_val,
                    "crm_url": f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rid}"
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            tickets = list(executor.map(fetch_ticket_info, rec_ids))

        for t in tickets:
            if not t:
                continue
            if target_staff_str:
                if target_staff_str not in t["owner"].lower():
                    continue
            all_matched_tickets.append(t)

    # Format report
    filter_label = f" (Người xử lý: `{target_staff}`)" if target_staff else ""
    report_lines = [
        f"📊 *BÁO CÁO TRA CỨU TICKET THEO SĐT*{filter_label}",
        f"📱 *Danh sách SĐT tra cứu ({len(phones)} SĐT)*: {', '.join(phones)}",
        f"🎯 *Tìm thấy*: `{len(all_matched_tickets)}` Ticket phù hợp\n"
    ]

    if not all_matched_tickets:
        report_lines.append("_Không tìm thấy Ticket nào khớp với điều kiện lọc trên CRM._")
    else:
        for idx, t in enumerate(all_matched_tickets, 1):
            report_lines.append(
                f"*{idx}. Ticket `{t['ticket_no']}`* *(SĐT: `{t['phone']}`)*\n"
                f"  • ⏰ *Thời gian chỉnh sửa*: `{t['modified_time']}`\n"
                f"  • 👤 *Người xử lý*: `{t['owner']}`\n"
                f"  • 📌 *Trạng thái TK*: `{t['status']}`\n"
                f"  • 📝 *Tiêu đề*: `{t['title']}`\n"
                f"  • 🏪 *Tên GH*: `{t['store']}`\n"
                f"  • 💬 *Mô tả*: _{t['description']}_\n"
                f"  • 🔗 [Link CRM]({t['crm_url']})\n"
            )

def do_check_single_ticket(ticket_query):
    """
    Super-fast lookup for a single HelpDesk Ticket by ticket_no (e.g. TT8883164 or 8883164).
    Returns formatted Markdown details including store, owner, description, and ModComments.
    """
    headers = get_headers()
    cookie_str = headers.get("cookie", "")
    t_q = str(ticket_query).strip()
    
    url_search = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&search_params=" + urllib.parse.quote(f'[[["ticket_no","c","{t_q}"]]]')
    try:
        with urllib.request.urlopen(urllib.request.Request(url_search, headers=headers), timeout=8) as resp:
            h = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Lỗi kết nối CRM: {e}"
        
    m = re.search(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>(.*?)</tr>', h, re.DOTALL)
    if not m:
        url_global = f"https://kvcrm.kiotviet.vn/index.php?module=Home&view=UnifiedSearch&query={t_q}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url_global, headers=headers), timeout=8) as resp2:
                h2 = resp2.read().decode('utf-8', errors='ignore')
            m = re.search(r'<tr[^>]+class=["\']listViewEntries["\'][^>]*data-id=["\'](\d+)["\'][^>]*>(.*?)</tr>', h2, re.DOTALL)
        except Exception:
            pass

    if not m:
        return f"❌ Không tìm thấy Ticket `{t_q}` trên CRM."

    rec_id, row_html = m.groups()
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
    
    t_no = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[1])).strip() if len(cells) > 1 else t_q
    title = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[2])).strip() if len(cells) > 2 else ""
    created_time = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[10])).strip() if len(cells) > 10 else ""
    status = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[4])).strip() if len(cells) > 4 else ""
    owner = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[7])).strip() if len(cells) > 7 else ""
    desc = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[8])).strip() if len(cells) > 8 else ""
    creator = html_lib.unescape(re.sub(r'<[^>]+>', ' ', cells[9])).strip() if len(cells) > 9 else ""
    
    detail_url = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=Detail&record={rec_id}"
    store_name = ""
    retailer_id = ""
    contact_name = ""
    full_desc = desc
    priority = ""
    
    try:
        with urllib.request.urlopen(urllib.request.Request(detail_url, headers=headers), timeout=8) as r_det:
            h_det = r_det.read().decode('utf-8', errors='ignore')
        
        rows_det = re.findall(r'<td[^>]*class=["\']fieldLabel[^>]*>(.*?)</td>\s*<td[^>]*class=["\']fieldValue[^>]*>(.*?)</td>', h_det, re.DOTALL)
        for lbl, val in rows_det:
            l_clean = html_lib.unescape(re.sub(r'<[^>]+>', ' ', lbl)).strip().lower()
            v_clean = html_lib.unescape(re.sub(r'<[^>]+>', ' ', val)).strip()
            if "select an option" in v_clean.lower():
                v_clean = re.split(r'select an option', v_clean, flags=re.IGNORECASE)[0].strip()
            if "tên gian hàng" in l_clean or "website" in l_clean:
                store_name = v_clean
                if store_name:
                    store_name = store_name.strip().splitlines()[0].strip()
                    if " " in store_name:
                        first_tok = store_name.split()[0].strip()
                        if first_tok.lower() in store_name.lower():
                            store_name = first_tok
            elif "retailer id" in l_clean:
                retailer_id = v_clean
            elif "khách hàng" in l_clean or "contact" in l_clean:
                contact_name = v_clean
            elif "mô tả" in l_clean or "description" in l_clean:
                full_desc = v_clean
            elif "ưu tiên" in l_clean or "priority" in l_clean:
                priority = v_clean
            elif "người tạo" in l_clean:
                creator = v_clean
            elif "thời gian tạo" in l_clean:
                created_time = v_clean
            elif "người xử lý" in l_clean:
                owner = v_clean
            elif "trạng thái" in l_clean:
                status = v_clean
            elif "tiêu đề" in l_clean:
                title = v_clean
    except Exception:
        pass

    comments = []
    comments_url = f"https://kvcrm.kiotviet.vn/index.php?module=ModComments&view=DetailAjax&record={rec_id}&relatedModule=HelpDesk&mode=showRelatedList"
    try:
        with urllib.request.urlopen(urllib.request.Request(comments_url, headers=headers), timeout=6) as r_c:
            h_c = r_c.read().decode('utf-8', errors='ignore')
        c_blocks = re.findall(r'<div[^>]*class=["\']commentDetails[^>]*>(.*?)</div>\s*</div>', h_c, re.DOTALL)
        for cb in c_blocks:
            c_text = re.sub(r'\s+', ' ', html_lib.unescape(re.sub(r'<[^>]+>', ' ', cb))).strip()
            comments.append(c_text)
    except Exception:
        pass

    res = (
        f"🎫 **CHI TIẾT TICKET [{t_no}]({detail_url})**\n"
        f"• 📝 **Tiêu đề**: `{title}`\n"
        f"• 🚦 **Trạng thái**: `{status}`\n"
        f"• 👤 **Người xử lý (Owner)**: `{owner}`\n"
        f"• ✍️ **Người tạo**: `{creator}` (Tạo: `{created_time}`)\n"
        f"• ⚡ **Ưu tiên**: `{priority or 'Normal'}`\n"
        f"• 🏪 **Tên gian hàng (cf_website)**: `{store_name or 'N/A'}` (Retailer ID: `{retailer_id or 'N/A'}`)\n"
        f"• 👤 **Khách hàng**: `{contact_name or 'N/A'}`\n"
        f"• 💬 **Lịch sử trao đổi (ModComments)**: `{len(comments)} comment`"
        + ("\n   " + "\n   ".join([f"- {c}" for c in comments[:3]]) if comments else "") + "\n"
        f"• 📄 **Mô tả yêu cầu**:\n"
        f"  _{full_desc}_\n"
    )
    return res

def find_pot_id_by_pxk(pxk_str, cookie_str=None):
    """
    Searches CRM Potentials list view by PXK contract ID (cf_pot_contractid)
    and returns the record ID (e.g. '110025563').
    """
    if not cookie_str:
        cookie_str, _ = crm_api.get_session()

    clean_pxk = re.sub(r'\s*/\s*', '/', str(pxk_str).strip())
    clean_pxk = re.sub(r'\s+', ' ', clean_pxk)

    headers = {"cookie": cookie_str, "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # 1. Search by cf_pot_contractid in Potentials List
    params = f'[[["cf_pot_contractid","c","{clean_pxk}"]]]'
    url_list = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=List&search_params={urllib.parse.quote(params)}"
    try:
        req = urllib.request.Request(url_list, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        m_ids = re.findall(r'tr[^>]*data-id=[\'"](\d+)[\'"]', html)
        if m_ids:
            return m_ids[0]
    except Exception:
        pass

    # 2. Fallback: search_key & search_value
    url_list2 = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=List&search_key=cf_pot_contractid&search_value={urllib.parse.quote(clean_pxk)}&operator=c"
    try:
        req2 = urllib.request.Request(url_list2, headers=headers)
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            html2 = resp2.read().decode('utf-8', errors='ignore')
        m_ids2 = re.findall(r'tr[^>]*data-id=[\'"](\d+)[\'"]', html2)
        if m_ids2:
            return m_ids2[0]
    except Exception:
        pass

    return None

def do_update_pot_by_pxk(pxk_input, note=None, target_stage="Chờ Xét Duyệt"):
    """
    Finds Potentials by PXK number, optionally adds note, and updates sales_stage to target_stage.
    Supports single or multiple PXK inputs.
    """
    pxk_list = []
    if isinstance(pxk_input, str):
        raw_items = [pxk_input]
    else:
        raw_items = list(pxk_input)

    for item in raw_items:
        for p in re.split(r'[,\n;\s]+', str(item)):
            p_clean = p.strip()
            if p_clean and p_clean not in pxk_list:
                pxk_list.append(p_clean)

    if not pxk_list:
        return []

    c_str, _ = crm_api.get_session()
    results = []

    for pxk in pxk_list:
        rec_id = find_pot_id_by_pxk(pxk, c_str)
        if not rec_id:
            results.append({"pxk": pxk, "success": False, "error": f"Không tìm thấy bản ghi với mã PXK '{pxk}'"})
            continue

        url_d = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={rec_id}"
        req_d = urllib.request.Request(url_d, headers={"cookie": c_str, "user-agent": "Mozilla/5.0"})
        store_name = "N/A"
        actual_pxk = pxk
        try:
            with urllib.request.urlopen(req_d, timeout=12) as resp:
                html_d = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_d, 'html.parser')
            td_store = soup.find('td', id='Potentials_detailView_fieldValue_cf_pot_website')
            td_contract = soup.find('td', id='Potentials_detailView_fieldValue_cf_pot_contractid')
            if td_store:
                store_name = td_store.get_text(strip=True)
            if td_contract:
                actual_pxk = td_contract.get_text(strip=True)
        except Exception:
            pass

        # 1. Update note if provided
        if note:
            ok_n, msg_n = do_update_pot_field(rec_id, "cf_pot_note", note)
            if not ok_n:
                results.append({"pxk": actual_pxk, "store": store_name, "record_id": rec_id, "success": False, "error": msg_n})
                continue
            time.sleep(0.3)

        # 2. Update stage
        ok_s, msg_s = do_update_pot_field(rec_id, "sales_stage", target_stage)
        if ok_s:
            results.append({"pxk": actual_pxk, "store": store_name, "record_id": rec_id, "success": True})
        else:
            results.append({"pxk": actual_pxk, "store": store_name, "record_id": rec_id, "success": False, "error": msg_s})

        time.sleep(0.3)

    return results

def do_update_pot_field(pot_id, field, value):
    """
    Safely update a single field on Potentials using SaveAjax.
    Always uses single-field SaveAjax to prevent form defaults from overwriting other fields.
    Supports record ID, URL, or PXK contract number.
    """
    c_str, _ = crm_api.get_session()
    pot_id_str = str(pot_id).strip()
    m_id = re.search(r'record=(\d+)', pot_id_str)
    if m_id:
        pot_id_str = m_id.group(1)
    elif not pot_id_str.isdigit():
        found_id = find_pot_id_by_pxk(pot_id_str, c_str)
        if found_id:
            pot_id_str = found_id
        else:
            return False, f"Không tìm thấy bản ghi Potentials nào khớp với mã: {pot_id_str}"

    url_d = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id_str}"
    headers = {
        "cookie": c_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    req_d = urllib.request.Request(url_d, headers=headers)
    try:
        with urllib.request.urlopen(req_d, timeout=12) as resp:
            html_d = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return False, f"Không thể kết nối đến Potentials {pot_id_str}: {e}"

    m_csrf = (re.search(r'csrfMagicToken\s*=\s*[\'"]([^\'"]+)[\'"]', html_d) or 
              re.search(r'name=[\'"]__vtrftk[\'"]\s+value=[\'"]([^\'"]+)[\'"]', html_d))
    csrf = m_csrf.group(1) if m_csrf else ""
    if not csrf:
        return False, "Không lấy được CSRF token từ CRM."

    post_url = "https://kvcrm.kiotviet.vn/index.php"
    payload = {
        "__vtrftk": csrf,
        "module": "Potentials",
        "action": "SaveAjax",
        "record": pot_id_str,
        "field": field,
        "value": value
    }
    encoded = urllib.parse.urlencode(payload).encode('utf-8')
    post_headers = {
        "Cookie": c_str,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": url_d
    }
    req = urllib.request.Request(post_url, data=encoded, headers=post_headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_raw = resp.read().decode('utf-8')
            res_json = json.loads(res_raw)
            if res_json.get("success"):
                display_val = res_json.get("result", {}).get(field, {}).get("display_value", value)
                return True, f"Cập nhật thành công {field} = {display_val}"
            else:
                err_msg = res_json.get("error", {}).get("message", str(res_json))
                return False, f"Lỗi CRM: {err_msg}"
    except Exception as e:
        return False, f"Lỗi kết nối API: {e}"

if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  python quick_action.py transfer <TICKET/ATC> <STAFF_CODE>")
        print("  python quick_action.py reject <TICKET/ATC> [COMMENT]")
        print("  python quick_action.py online <TICKET/ATC/RET_ID> [OI/NA]")
        print("  python quick_action.py region <REGION_NAME_OR_ID> <QTY> <STAFF_CODE> [WARD]")
        print("  python quick_action.py checkquoc")
        print("  python quick_action.py checktk [TICKET_NO]")
        print("  python quick_action.py checkstore <STORE_NAME_OR_RET_ID>")
        print("  python quick_action.py checkpot <POT_ID_OR_RETAILER_OR_PHONE>")
        print("  python quick_action.py invoice <POT_ID_OR_LINK_OR_RET_ID>")
        print("  python quick_action.py pot_stage <POT_ID> [STAGE]")
        print("  python quick_action.py pot_note <POT_ID> <NOTE>")
        print("  python quick_action.py checkphone <PHONES> [STAFF_CODE]")
        print("  python quick_action.py gchat")
        print("  python quick_action.py gchat_tk")
        print("  python quick_action.py checkaddr <START_DATE> <END_DATE>")
        print("  python quick_action.py sla [MIN_DAYS]")
        sys.exit(0)

    cmd = args[0].lower()
    if cmd == "transfer" and len(args) >= 3:
        res_t = do_transfer(args[1], args[2])
        rec_id, ticket_no, retailer_id, atcs = res_t[:4]
        latest_atc = res_t[4] if len(res_t) > 4 else None
        desc = res_t[5] if len(res_t) > 5 else ""
        store_name = res_t[6] if len(res_t) > 6 else ""
        staff_info = STAFF_MAP.get(str(args[2]), (args[2], args[2]))[1]
        print(f"TRANSFER_SUCCESS: rec_id={rec_id}, ticket={ticket_no}, store={store_name}, retailer={retailer_id}, atcs={atcs}, staff={args[2]}, desc={desc}")
        if "--no-gchat" not in args:
            send_transfer_gchat(rec_id, ticket_no, store_name, retailer_id, args[2], staff_info, atcs, latest_atc, desc)
    elif cmd == "reject" and len(args) >= 2:
        cmt = args[2] if len(args) > 2 else "khu vực không có SC"
        rec_id, ticket_no, retailer_id, atcs = do_reject(args[1], cmt)
        print(f"REJECT_SUCCESS: rec_id={rec_id}, ticket={ticket_no}, retailer={retailer_id}, atcs={atcs}, comment={cmt}")
    elif cmd in ["online", "switch_online"] and len(args) >= 2:
        supp_type = args[2] if len(args) > 2 else "OI"
        success, rec_id, group_label, raw_res = do_switch_online(args[1], supp_type)
        print(f"ONLINE_SUCCESS: success={success}, atc={rec_id}, type={group_label}, raw={raw_res}")
    elif cmd == "region" and len(args) >= 4:
        ward = args[4] if len(args) > 4 else None
        success, msg, rname, scode, sname = do_assign_region(args[1], args[2], args[3], ward_filter=ward)
        print(f"REGION_ASSIGN: success={success}, region={rname}, qty={args[2]}, staff={scode} ({sname}), msg={msg}")
    elif cmd == "checkquoc":
        print(do_check_coacher_quoc())
    elif cmd in ["checksc", "sc"]:
        full_mode = len(args) > 1 and args[1].lower() in ["full", "all", "chitiet", "detail", "mota"]
        print(do_check_sc_group(full_desc=full_mode))
    elif cmd in ["checktk", "check"] and len(args) >= 2:
        print(do_check_single_ticket(args[1]))
    elif cmd == "checktk":
        print(do_check_tickets())
    elif cmd == "checkstore" and len(args) >= 2:
        res = do_check_store(args[1])
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif cmd in ["checkpot", "pot", "kyc"] and len(args) >= 2:
        query_input = args[1] if len(args) == 2 else args[1:]
        print(do_check_pot(query_input))
    elif cmd in ["invoice", "hoadon", "xuathoadon", "bill", "vat"] and len(args) >= 2:
        as_mail = len(args) > 2 and args[2].lower() in ["mail", "email", "thu"]
        query_input = args[1] if (len(args) == 2 or as_mail) else args[1:]
        print(do_check_invoice(query_input, as_email=as_mail))
    elif cmd in ["pot_stage", "potstage", "otp_stage"] and len(args) >= 2:
        target_stage = args[2] if len(args) > 2 else "Chờ Xét Duyệt"
        s, msg = do_update_pot_field(args[1], "sales_stage", target_stage)
        print(f"POT_STAGE_SUCCESS: {s} | {msg}")
    elif cmd in ["pot_note", "potnote", "otp_note"] and len(args) >= 3:
        note_text = " ".join(args[2:])
        s, msg = do_update_pot_field(args[1], "cf_pot_note", note_text)
        print(f"POT_NOTE_SUCCESS: {s} | {msg}")
    elif cmd in ["pxk", "pot_pxk"] and len(args) >= 2:
        pxk_query = args[1:]
        res_list = do_update_pot_by_pxk(pxk_query)
        for r in res_list:
            if r["success"]:
                print(f"PXK_SUCCESS: {r['store']} - {r['pxk']} (record={r['record_id']})")
            else:
                print(f"PXK_FAILED: {r['pxk']} -> {r.get('error')}")
    elif cmd == "gchat":
        import reporter
        success, msg = reporter.send_google_chat_report()
        print(f"GCHAT_SUCCESS: {success}\n{msg}")
    elif cmd == "gchat_tk":
        success, msg = do_send_ticket_gchat()
        print(f"GCHAT_TK_SUCCESS: {success}\n{msg}")
    elif cmd == "checkaddr" and len(args) >= 3:
        res = do_check_store_address(args[1], args[2])
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif cmd == "checkphone" and len(args) >= 2:
        staff_filter = args[2] if len(args) > 2 else None
        print(do_check_phone(args[1], target_staff=staff_filter))
    elif cmd == "sla":
        days = int(args[1]) if len(args) > 1 else 10
        print(do_check_sla(days))
    elif cmd in ["auto_assign", "autoassign", "chiatudong"]:
        is_dry = len(args) > 1 and args[1].lower() in ["dry", "test", "check", "thu"]
        b_size = int(args[2]) if len(args) > 2 and args[2].isdigit() else 8
        thresh = int(args[3]) if len(args) > 3 and args[3].isdigit() else 10
        s, report_str, recs = do_auto_assign_under_10(batch_size=b_size, threshold=thresh, dry_run=is_dry)
        # do_auto_assign_under_10 already prints report_str
    elif cmd in ["sheet", "updatesheet", "update_sheet", "capnhatsheet", "dienphuongxa"]:
        import auto_sheet_updater
        s, msg = auto_sheet_updater.run_auto_update_hcm_sheet()
        print(msg)
    else:
        print(f"Unknown command: {args}")
