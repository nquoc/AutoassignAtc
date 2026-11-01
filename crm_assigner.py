import os
import sys
import time
import urllib.parse
import urllib.request
import json
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium_helper import SeleniumHelper

from crm_api import get_staff_mapping, change_owner_api

def assign_atc(retailer_id, staff_id, status_callback=None):
    def update_status(msg):
        if status_callback:
            status_callback(msg)
        else:
            print(msg)

    update_status(f"⚙️ Đang giải mã ID nội bộ API cho nhân sự {staff_id}...")
    from crm_api import get_staff_mapping, change_owner_api, get_session, acquire_session_via_selenium
    internal_staff_id = get_staff_mapping(staff_id)
    if not internal_staff_id:
        return False, f"Không thể lấy được mã định danh nội bộ (API) cho nhân sự {staff_id}."
        
    update_status(f"🔍 Đang quét danh sách bằng API để tìm Retailer ID: {retailer_id}...")
    
    cookie_str, csrf = get_session()
    if not cookie_str:
        update_status("🔑 Session đã hết hạn, đang mở trình duyệt ẩn để tự động đăng nhập lại CRM (khoảng 15 giây)...")
        cookie_str, csrf = acquire_session_via_selenium("16309", update_status=update_status)
        if not cookie_str:
            return False, "Không có session hợp lệ. Xin hãy thử lại sau."
            
    import urllib.parse
    import urllib.request
    import json
    from bs4 import BeautifulSoup
    
    search_params = [[["retailer_id", "co", str(retailer_id)]]]
    encoded_params = urllib.parse.quote(json.dumps(search_params))
    list_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params={encoded_params}"
    
    req = urllib.request.Request(list_url, headers={"cookie": cookie_str})
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check login redirect
            if "login" in response.geturl().lower() or "signin" in response.geturl().lower():
                update_status("🔑 Session đã hết hạn, đang mở trình duyệt ẩn để tự động đăng nhập lại CRM...")
                cookie_str, csrf = acquire_session_via_selenium("16309", update_status=update_status)
                if not cookie_str:
                    return False, "Đăng nhập tự động thất bại."
                # Retry
                req = urllib.request.Request(list_url, headers={"cookie": cookie_str})
                with urllib.request.urlopen(req) as response2:
                    html = response2.read().decode('utf-8')
                    soup = BeautifulSoup(html, 'html.parser')
                    
            rows = soup.select('tr.listViewEntries')
            if not rows:
                update_status(f"⚠️ Chưa có ATC tạo mới cho Retailer ID {retailer_id}!")
                return False, f"Chưa có ATC tạo mới (Không tìm thấy record CSKHSC nào cho Retailer ID {retailer_id})."
                
            first_row = rows[0]
            data_id = first_row.get("data-id")
            
            tds = first_row.find_all('td')
            owner_name = "Unknown"
            if len(tds) > 1:
                owner_name = tds[1].get_text(strip=True)
                
            update_status(f"👤 Người xử lý hiện tại là: '{owner_name}'")
            
            owner_lower = owner_name.lower()
            allowed_keywords = [
                "sc group",
                "chăm sóc khách hàng hỗ trợ trực tiếp",
                "hỗ trợ trực tiếp",
                "chăm sóc khách hàng",
                "direct support",
                "cskh"
            ]
            is_allowed = any(kw in owner_lower for kw in allowed_keywords)
            
            # Safeguard check
            if not is_allowed:
                update_status(f"⚠️ Bỏ qua: ATC này đang được phụ trách bởi '{owner_name}'.")
                return False, f"Chưa có ATC tạo mới (ATC này đã được bàn giao cho '{owner_name}' xử lý trước đó rồi nha anh)."
                
            update_status(f"☑️ Đã trích xuất mã ATC ẩn: {data_id}.")
            
            update_status("🚀 Bắt đầu bắn API phân công (Siêu tốc)...")
            from crm_api import change_owner_api
            success, msg = change_owner_api([data_id], internal_staff_id)
            if success:
                return True, f"Bàn giao ATC thành công cho nhân sự: `{staff_id}`."
                
            update_status(f"⚠️ API phản hồi ({msg}), đang tự động chuyển sang luồng Trình duyệt Chrome...")
            return assign_via_selenium(list_url, [data_id], internal_staff_id, update_status=update_status)
            
    except Exception as e:
        return False, f"Lỗi API khi tìm kiếm ATC: {e}"

def assign_via_selenium(list_url, data_ids, internal_staff_id, update_status=None):
    def log(msg):
        if update_status: update_status(msg)
        else: print(msg)
        
    log("🌐 Đang khởi tạo trình duyệt Chrome ngầm để thao tác phân công...")
    temp_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "crm_selenium_assign")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    driver = None
    try:
        driver = SeleniumHelper.init_driver(temp_dir, headless=True)
        driver.get(list_url)
        time.sleep(3)
        
        # Check login
        u = driver.current_url.lower()
        if 'login' in u or 'signin' in u or 'accounts.google.com' in u:
            log("🔑 Đang tự động đăng nhập CRM...")
            SeleniumHelper.try_auto_login(driver)
            driver.get(list_url)
            time.sleep(3)
            
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.listViewEntries, tr[data-id]")
        if not rows:
            return False, "Không tìm thấy dòng dữ liệu nào trên CRM."
            
        ticked = 0
        for row in rows:
            r_id = row.get_attribute("data-id")
            if not data_ids or r_id in data_ids:
                cb = row.find_element(By.CSS_SELECTOR, "input.listViewEntriesCheckBox")
                if not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
                    ticked += 1
                if data_ids and ticked >= len(data_ids):
                    break
                    
        if ticked == 0:
            return False, "Không tick chọn được dữ liệu nào."
            
        buttons = driver.find_elements(By.CSS_SELECTOR, "button.dropdown-toggle")
        actions_btn = None
        for btn in buttons:
            if "actions" in btn.text.strip().lower():
                actions_btn = btn
                break
        if not actions_btn:
            return False, "Không tìm thấy nút Actions trên CRM."
            
        driver.execute_script("arguments[0].click();", actions_btn)
        time.sleep(1.5)
        
        change_owner_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Change Owner')]")
        driver.execute_script("arguments[0].click();", change_owner_link)
        time.sleep(2)
        
        js_select = """
        var selectEl = document.getElementById('changeOwnerId');
        selectEl.value = arguments[0];
        if (window.jQuery) {
            var $sel = window.jQuery(selectEl);
            $sel.trigger('change');
            $sel.trigger('chosen:updated').trigger('liszt:updated');
        } else {
            selectEl.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """
        driver.execute_script(js_select, str(internal_staff_id))
        time.sleep(1)
        
        modal = driver.find_element(By.ID, "transferOwnershipContainer")
        save_btn = modal.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(3)
        
        log("🎉 Đã lưu thay đổi thành công trên trình duyệt Chrome!")
        return True, "Bàn giao ATC thành công."
    except Exception as e:
        return False, f"Lỗi thao tác trình duyệt: {e}"
    finally:
        if driver:
            try: driver.quit()
            except: pass

def assign_region_data(url_str, quantity, staff_id, ward_filter=None, update_status=None):
    def log(msg):
        if update_status:
            update_status(msg)
        else:
            print(msg)

    target_url = url_str
    if ward_filter:
        try:
            parsed = urllib.parse.urlparse(url_str)
            params = urllib.parse.parse_qs(parsed.query)
            sp_raw = params.get('search_params', ['[[]]'])[0]
            sp_obj = json.loads(sp_raw)
            if not sp_obj or not isinstance(sp_obj, list) or len(sp_obj) == 0:
                sp_obj = [[]]
            if not isinstance(sp_obj[0], list):
                sp_obj[0] = []

            # Loại bỏ điều kiện cf_state cũ (ví dụ phủ định 'n' ở HCM) để thêm điều kiện mới 'e'
            sp_obj[0] = [p for p in sp_obj[0] if p[0] != "cf_state"]

            raw_w_list = ward_filter if isinstance(ward_filter, (list, tuple, set)) else str(ward_filter).split(",")
            clean_wards = []
            for w in raw_w_list:
                w_str = str(w).strip()
                if not w_str: continue
                clean_wards.append(w_str)
                if not any(w_str.lower().startswith(p) for p in ["phường", "xã", "thị trấn"]):
                    clean_wards.append(f"Phường {w_str}")
                    clean_wards.append(f"Xã {w_str}")

            ward_str_val = ",".join(clean_wards)
            op = "e"

            sp_obj[0].append(["cf_state", op, ward_str_val])
            new_sp_enc = urllib.parse.quote(json.dumps(sp_obj))
            
            if "search_params=" in url_str:
                base_url = url_str.split("search_params=")[0]
                target_url = f"{base_url}search_params={new_sp_enc}"
            else:
                target_url = f"{url_str}&search_params={new_sp_enc}"
        except Exception as e:
            log(f"⚠️ Lỗi cấu hình bộ lọc Phường/Xã: {e}")

    log(f"⚙️ Đang giải mã ID nội bộ API cho nhân sự {staff_id}...")
    internal_staff_id = get_staff_mapping(staff_id)
    if not internal_staff_id:
        return False, f"Không thể lấy được mã định danh nội bộ (API) cho nhân sự {staff_id}."
        
    if isinstance(ward_filter, (list, tuple, set)):
        ward_info_str = f" tại {len(ward_filter)} Phường/Xã ({', '.join(str(w) for w in ward_filter)})"
    elif ward_filter:
        ward_info_str = f" tại Phường/Xã '{ward_filter}'"
    else:
        ward_info_str = ""

    log(f"⚙️ Đang quét API siêu tốc để lấy danh sách Record ID{ward_info_str}...")
    
    from crm_api import get_session
    
    cookie_str, csrf = get_session()
    if not cookie_str:
        log("🔑 Session đã hết hạn, đang mở trình duyệt ẩn để tự động đăng nhập lại CRM (khoảng 15 giây)...")
        from crm_api import acquire_session_via_selenium
        cookie_str, csrf = acquire_session_via_selenium("16309", update_status=log)
        if not cookie_str:
            return False, "Không có session hợp lệ. Đăng nhập tự động thất bại."
        
    headers = {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(target_url, headers=headers)
    ticked_ids = []
    
    if isinstance(quantity, str) and quantity.lower() in ("all", "tatca", "tất cả"):
        qty_limit = 999999
    else:
        try:
            qty_limit = int(quantity)
        except Exception:
            qty_limit = 999999
    
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.find_all('tr', class_='listViewEntries')
            
            for row in rows:
                if len(ticked_ids) >= qty_limit:
                    break
                data_id = row.get('data-id')
                if data_id:
                    if ward_filter:
                        row_text = row.get_text(separator=' ', strip=True).lower()
                        if isinstance(ward_filter, (list, tuple, set)):
                            if not any(str(w).strip().lower() in row_text for w in ward_filter):
                                continue
                        elif "," in str(ward_filter):
                            w_list = [w.strip().lower() for w in str(ward_filter).split(",") if w.strip()]
                            if not any(w in row_text for w in w_list):
                                continue
                        else:
                            if str(ward_filter).strip().lower() not in row_text:
                                continue
                    ticked_ids.append(data_id)

        ticked_count = len(ticked_ids)
        if ticked_count == 0:
            return False, f"Không tìm thấy data nào{ward_info_str} để bàn giao."
            
        log(f"☑️ Đã quét ra {ticked_count} Record ID của atc đang treo{ward_info_str} (Thời gian: < 1 giây).")
        
        # Call API
        log("🚀 Bắt đầu bắn API phân công (Siêu tốc)...")
        success, api_msg = change_owner_api(ticked_ids, internal_staff_id)
        
        if success:
            log(f"🎉 Đã bắn API thành công! Chuyển {ticked_count} data cho {staff_id}.")
            return True, f"Bàn giao ATC thành công cho nhân sự: **{staff_id}** (Đã chuyển **{ticked_count}** data{ward_info_str} qua API)."
            
        log(f"⚠️ API phản hồi ({api_msg}), đang tự động chuyển sang luồng Trình duyệt Chrome...")
        return assign_via_selenium(target_url, ticked_ids, internal_staff_id, update_status=log)
    except Exception as e:
        log(f"⚠️ Lỗi API: {e}, đang chuyển sang luồng Trình duyệt Chrome...")
        return assign_via_selenium(target_url, None, internal_staff_id, update_status=log)
