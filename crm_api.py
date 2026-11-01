import os
import sys
import time
import urllib.request
import urllib.parse
import json
import csv
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Import SeleniumHelper from local directory
from selenium_helper import SeleniumHelper

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")

_cookie_cache = {"cookie": "", "time": 0, "valid": False}

def check_cookie_valid(cookie_str):
    if not cookie_str:
        return False
    now = time.time()
    if _cookie_cache["cookie"] == cookie_str and (now - _cookie_cache["time"] < 60) and _cookie_cache["valid"]:
        return True
    try:
        url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname=16309"
        req = urllib.request.Request(url, headers={"cookie": cookie_str, "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            final_url = response.geturl().lower()
            if "login" in final_url or "signin" in final_url or "accounts.google.com" in final_url:
                _cookie_cache.update({"cookie": cookie_str, "time": now, "valid": False})
                return False
            html = response.read().decode('utf-8', errors='ignore')
            if 'name="username"' in html or 'id="username"' in html:
                _cookie_cache.update({"cookie": cookie_str, "time": now, "valid": False})
                return False
            _cookie_cache.update({"cookie": cookie_str, "time": now, "valid": True})
            return True
    except:
        return False

def get_session():
    cached_csrf = ""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                s_data = json.load(f)
                cached_csrf = s_data.get("csrf_token", "")
        except:
            pass

    # 1. Manual cookie from cookie.txt (highest priority)
    cookie_txt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt")
    if os.path.exists(cookie_txt_file):
        try:
            with open(cookie_txt_file, "r", encoding="utf-8") as f:
                cookie_content = f.read().strip()
                if cookie_content and check_cookie_valid(cookie_content):
                    return cookie_content, cached_csrf
        except:
            pass

    # 2. Existing session file
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookie_str = data.get("cookie_str")
                csrf_token = data.get("csrf_token")
                if check_cookie_valid(cookie_str):
                    return cookie_str, csrf_token
        except:
            pass
    return None, None

def save_session(cookie_str, csrf_token):
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "cookie_str": cookie_str,
                "csrf_token": csrf_token,
                "timestamp": time.time()
            }, f, indent=4)
    except Exception as e:
        print(f"Error saving session: {e}")

import threading
_session_lock = threading.Lock()

def acquire_session_via_selenium(viewname="16309", update_status=None, allow_gui_fallback=True):
    def get_fresh_cached_session():
        try:
            cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session_cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if time.time() - data.get("timestamp", 0) < 45:
                        c_str = data.get("cookie", "")
                        csrf = data.get("csrf_token", "")
                        if c_str and csrf:
                            return c_str, csrf
        except Exception:
            pass
        return None, None

    # 1. Quick check: Did another thread just refresh the session in the last 45s?
    fresh_c, fresh_csrf = get_fresh_cached_session()
    if fresh_c and fresh_csrf:
        return fresh_c, fresh_csrf

    # 2. Wait for lock (up to 60s) so concurrent threads queue up instead of failing immediately
    if not _session_lock.acquire(blocking=True, timeout=60):
        fresh_c, fresh_csrf = get_fresh_cached_session()
        if fresh_c and fresh_csrf:
            return fresh_c, fresh_csrf
        return None, None
        
    try:
        # Double check after acquiring the lock: Did the thread we were waiting for refresh successfully?
        fresh_c, fresh_csrf = get_fresh_cached_session()
        if fresh_c and fresh_csrf:
            return fresh_c, fresh_csrf
        def log(msg):
            if update_status:
                update_status(msg)
            else:
                print(msg, flush=True)
                
        def _run_selenium(headless):
            temp_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "crm_autoassign_downloads")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            driver = None
            try:
                driver = SeleniumHelper.init_driver(temp_dir, headless=headless)
                url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname={viewname}"
                driver.get(url)
                time.sleep(3)
                
                def check_login():
                    u = driver.current_url.lower()
                    if 'login' in u or 'signin' in u or 'accounts.google.com' in u:
                        return True
                    try:
                        from selenium.webdriver.common.by import By
                        if driver.find_elements(By.NAME, "username") or driver.find_elements(By.ID, "username"):
                            return True
                    except:
                        pass
                    return False

                if check_login():
                    success = SeleniumHelper.try_auto_login(driver)
                    if not success and not headless:
                        log("⏳ Cửa sổ trình duyệt đang mở. Vui lòng xác thực Google/2FA trên màn hình trong 45s...")
                        w_start = time.time()
                        while time.time() - w_start < 45:
                            if not check_login():
                                log("🎉 Đã phát hiện đăng nhập thành công!")
                                break
                            time.sleep(1)
                    time.sleep(3)
                    
                export_view_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Export&selected_ids=[]&excluded_ids=[]&viewname={viewname}&page=1&search_params=%5B%5B%5D%5D"
                driver.get(export_view_url)
                time.sleep(2)
                
                cookies = driver.get_cookies()
                cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                
                html = driver.page_source
                match = re.search(r'name=["\']__vtrftk["\']\s+value=["\']([^"\']+)["\']', html)
                csrf_token = ""
                if match:
                    csrf_token = match.group(1)
                    
                if cookie_str and ("kvcrm_phpsessid" in cookie_str.lower() or "current_user" in cookie_str.lower()):
                    save_session(cookie_str, csrf_token)
                    cookie_txt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt")
                    try:
                        with open(cookie_txt_file, "w", encoding="utf-8") as f:
                            f.write(cookie_str)
                    except:
                        pass
                    return cookie_str, csrf_token
            except Exception as e:
                print(f"Error acquiring session (headless={headless}): {e}", flush=True)
            finally:
                try:
                    if driver:
                        driver.quit()
                except:
                    pass
            return None, None

        log("🛠 Đang mở luồng tự động để làm mới phiên làm việc CRM...")
        c_str, csrf = _run_selenium(headless=True)
        if c_str and csrf:
            return c_str, csrf

        if allow_gui_fallback:
            log("🌐 Cần tương tác đăng nhập Google, đang mở cửa sổ trình duyệt...")
            c_str, csrf = _run_selenium(headless=False)
            if c_str and csrf:
                return c_str, csrf

        return None, None
    finally:
        _session_lock.release()

def fetch_crm_export(url_str, force_refresh=False, update_status=None):
    parsed = urllib.parse.urlparse(url_str)
    params = urllib.parse.parse_qs(parsed.query)
    
    viewname = params.get('viewname', ['16309'])[0]
    search_params = params.get('search_params', ['[[]]'])[0]
    search_key = params.get('search_key', [''])[0]
    operator = params.get('operator', [''])[0]
    search_value = params.get('search_value', [''])[0]
    
    cookie_str, csrf_token = None, None
    if not force_refresh:
        cookie_str, csrf_token = get_session()
        
    if cookie_str and not csrf_token:
        try:
            export_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Export&selected_ids=[]&excluded_ids=[]&viewname={viewname}&page=1&search_params=%5B%5B%5D%5D"
            req = urllib.request.Request(export_url, headers={"cookie": cookie_str, "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                m = re.search(r'csrfMagicToken\s*=\s*["\']([^"\']+)["\']', html) or re.search(r'name=["\']__vtrftk["\']\s+value=["\']([^"\']+)["\']', html) or re.search(r'(sid:[a-zA-Z0-9,]+)', html)
                if m:
                    csrf_token = m.group(1)
        except Exception:
            pass

    if not cookie_str:
        cookie_str, csrf_token = acquire_session_via_selenium(viewname, update_status)
        
    if not cookie_str:
        return None
        
    for attempt in range(2):
        form_data = {
            "__vtrftk": csrf_token,
            "module": "CSKHSC",
            "source_module": "CSKHSC",
            "action": "ExportData",
            "viewname": viewname,
            "selected_ids": "[]",
            "excluded_ids": "[]",
            "mode": "ExportAllData",
            "page": "1",
            "search_key": search_key,
            "operator": operator,
            "search_value": search_value,
            "search_params": search_params,
            "phong_ban": ""
        }
        
        encoded_data = urllib.parse.urlencode(form_data).encode('utf-8')
        post_url = "https://kvcrm.kiotviet.vn/index.php"
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "cookie": cookie_str,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        }
        
        req = urllib.request.Request(post_url, data=encoded_data, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data_bytes = resp.read()
                final_url = resp.geturl()
                if "login" in final_url.lower() or "signin" in final_url.lower():
                    raise ValueError("Session expired.")
                    
                content_str = data_bytes.decode('utf-16', errors='ignore')
                lines = content_str.splitlines()
                reader = csv.reader(lines, delimiter='\t')
                rows = list(reader)
                if len(rows) > 0 and "Retailer ID" in rows[0]:
                    return rows
                else:
                    raise ValueError("Invalid format returned.")
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}", flush=True)
            if attempt == 0:
                cookie_str, csrf_token = acquire_session_via_selenium(viewname, update_status)
                if not cookie_str or not csrf_token:
                    break
            else:
                break
    return None

def parse_region_summary(rows):
    if not rows or len(rows) < 2:
        return {
            "total_unassigned": 0,
            "wards": {}
        }
        
    headers = rows[0]
    retailer_idx = -1
    owner_idx = -1
    state_idx = -1
    
    for i, h in enumerate(headers):
        if h == "Retailer ID":
            retailer_idx = i
        elif h == "Người xử lý":
            owner_idx = i
        elif h == "Xã/Phường/Thị trấn":
            state_idx = i
            
    if owner_idx == -1 or state_idx == -1:
        print(f"Error: Required columns not found in headers {headers}!", flush=True)
        return None
        
    total_unassigned = 0
    wards = {}
    
    for row in rows[1:]:
        if len(row) <= max(owner_idx, state_idx):
            continue
            
        owner = row[owner_idx].strip()
        ward = row[state_idx].strip() or "Chưa xác định"
        
        total_unassigned += 1
        wards[ward] = wards.get(ward, 0) + 1
            
    sorted_wards = dict(sorted(wards.items(), key=lambda item: item[1], reverse=True))
    
    return {
        "total_unassigned": total_unassigned,
        "wards": sorted_wards
    }

def get_region_summary(url_str, update_status=None):
    rows = fetch_crm_export(url_str, update_status=update_status)
    if rows:
        return parse_region_summary(rows)
    return None

def get_staff_mapping(staff_short_id):
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staff_mapping_cache.json")
    mapping = {}
    
    # Load cache if exists
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                mapping = data.get("mapping", {})
                if str(staff_short_id) in mapping:
                    return str(mapping[str(staff_short_id)])
        except:
            pass
            
    # Fetch from API
    cookie_str, csrf_token = get_session()
    if not cookie_str or not csrf_token:
        cookie_str, csrf_token = acquire_session_via_selenium("16309")
        
    if not cookie_str:
        return None
        
    modal_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=MassActionAjax&mode=transferOwnership"
    req = urllib.request.Request(modal_url, headers={
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0"
    })
    
    try:
        import html as html_lib
        with urllib.request.urlopen(req) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
            
        options = re.findall(r'<option value=["\'](\d+)["\'][^>]*>([^<]+)</option>', html_page)
        staff_dict = {}
        for opt in options:
            val = opt[0]
            clean_text = html_lib.unescape(opt[1]).strip()
            clean_text = re.sub(r'\s+', ' ', clean_text)
            match = re.search(r'\b(\d{4,6})\b', clean_text)
            if match:
                s_id = match.group(1)
                mapping[s_id] = val
                name_clean = clean_text
                m_sub = re.match(r'^\d+\s*[-–:]\s*(.+)$', clean_text)
                if m_sub:
                    name_clean = m_sub.group(1).strip()
                staff_dict[s_id] = {
                    "short_id": s_id,
                    "internal_id": val,
                    "name": name_clean,
                    "full_name": clean_text
                }
                
        # Cache it
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": time.time(),
                "mapping": mapping,
                "staff": staff_dict
            }, f, ensure_ascii=False, indent=4)
            
        return mapping.get(str(staff_short_id))
    except Exception as e:
        print(f"Error fetching staff mapping: {e}")
        return None

def get_staff_info(staff_short_id):
    """
    Returns dict {"short_id": ..., "internal_id": ..., "name": ..., "full_name": ...} or None
    """
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "staff_mapping_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                staff_dict = data.get("staff", {})
                if str(staff_short_id) in staff_dict:
                    return staff_dict[str(staff_short_id)]
        except:
            pass
            
    # Fallback to get_staff_mapping
    internal_id = get_staff_mapping(staff_short_id)
    if internal_id:
        return {"short_id": str(staff_short_id), "internal_id": str(internal_id), "name": str(staff_short_id), "full_name": str(staff_short_id)}
    return None

def change_owner_api(atc_ids, target_internal_id, viewname="16309"):
    """
    Direct API call to change owner for a list of ATC data-ids.
    Returns (True, message) on success, (False, err) on fail.
    """
    cookie_str, csrf_token = get_session()
    if not cookie_str:
        cookie_str, csrf_token = acquire_session_via_selenium(viewname)
        
    if not cookie_str:
        return False, "Không có session API hợp lệ."
        
    # Fetch fresh CSRF token dynamically to prevent "Invalid request" errors
    try:
        fetch_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname={viewname}"
        req_fetch = urllib.request.Request(fetch_url, headers={"cookie": cookie_str, "user-agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_fetch, timeout=8) as resp_fetch:
            html = resp_fetch.read().decode('utf-8', errors='ignore')
            match = re.search(r'csrfMagicToken\s*=\s*["\']([^"\']+)["\']', html) or re.search(r'name=["\']__vtrftk["\']\s+value=["\']([^"\']+)["\']', html) or re.search(r'(sid:[a-zA-Z0-9,]+)', html)
            if match:
                csrf_token = match.group(1)
                save_session(cookie_str, csrf_token)
    except Exception as e:
        print(f"Warning: Failed to refresh CSRF token dynamically: {e}")

    form_data = [
        ("__vtrftk", csrf_token),
        ("module", "CSKHSC"),
        ("action", "ChangeOwnerAction"),
        ("viewname", viewname),
        ("excluded_ids[]", ""),
        ("changeOwnerId", str(target_internal_id)),
        ("search_params", "[[]]")
    ]
    for aid in atc_ids:
        form_data.append(("selected_ids[]", str(aid)))
        
    encoded_data = urllib.parse.urlencode(form_data).encode('utf-8')
    post_url = "https://kvcrm.kiotviet.vn/index.php"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(post_url, data=encoded_data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            if "login" in resp.geturl().lower() or "signin" in resp.geturl().lower():
                return False, "Session API hết hạn, bị đẩy ra trang đăng nhập."
            
            if '"success":true' in data or '"success": true' in data:
                return True, "Gọi API thành công."
            else:
                return False, f"Lỗi từ CRM: {data[:200]}"
    except Exception as e:
        return False, f"Lỗi kết nối API: {e}"

def get_kyc_data(module, record_id):
    """
    Fetches decrypted KYC data (address, phone, email, passport) for a record
    in modules such as Potentials, Contacts, Leads, HelpDesk.
    """
    cookie_str, _ = get_session()
    headers = {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url_d = f"https://kvcrm.kiotviet.vn/index.php?module={module}&view=Detail&record={record_id}"
    try:
        req_d = urllib.request.Request(url_d, headers=headers)
        with urllib.request.urlopen(req_d, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return {"success": False, "error": f"Lỗi mở trang Detail: {e}"}

    # Extract kyc_token
    token = ""
    m = re.search(r'fieldValue_kyc_token["\'][^>]*>(.*?)</td>', html, re.DOTALL)
    if m:
        token_match = re.search(r'([a-f0-9]{32,64})', m.group(1))
        if token_match:
            token = token_match.group(1)
    
    if not token:
        m2 = re.search(r'class=["\'][^"\']*kyc-kyc_token[^"\']*["\'][^>]*>([a-f0-9]{32,64})<', html)
        if m2:
            token = m2.group(1)

    if not token:
        return {"success": False, "error": "Không tìm thấy KYC token trên trang"}

    # Call GetKYC action
    kyc_url = f"https://kvcrm.kiotviet.vn/index.php?module={module}&action=GetKYC&record_id={record_id}&token={token}"
    try:
        req_kyc = urllib.request.Request(kyc_url, headers=headers)
        with urllib.request.urlopen(req_kyc, timeout=10) as resp_kyc:
            res_json = json.loads(resp_kyc.read().decode('utf-8', errors='ignore'))
            if res_json.get("success") and "result" in res_json:
                res = res_json["result"]
                if "other" in res and isinstance(res["other"], str) and res["other"].startswith("{"):
                    try:
                        res["other_parsed"] = json.loads(res["other"])
                    except:
                        pass
                return {"success": True, "result": res}
            return res_json
    except Exception as e:
        return {"success": False, "error": f"Lỗi gọi API GetKYC: {e}"}
