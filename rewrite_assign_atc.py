import sys
import re

def rewrite():
    with open('crm_assigner.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the assign_atc function block
    start_str = "def assign_atc(retailer_id, staff_id, status_callback=None):"
    
    # We will replace from start_str to the end of assign_atc.
    # The next function is `def assign_region_data(url_str, quantity, staff_id, status_callback=None):`
    end_str = "def assign_region_data(url_str, quantity, staff_id, update_status=None):"
    
    parts = content.split(end_str)
    if len(parts) != 2:
        print("Error: Could not split at assign_region_data")
        return
        
    before_end = parts[0]
    
    # Keep everything before assign_atc
    before_assign = before_end.split(start_str)[0]
    
    new_assign_atc = '''def assign_atc(retailer_id, staff_id, status_callback=None):
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
            
            # Safeguard: must be "SC Group" or similar to assign
            if "sc group" not in owner_name.lower() and "chăm sóc khách hàng" not in owner_name.lower():
                update_status(f"⚠️ Bỏ qua: ATC này đang được phụ trách bởi '{owner_name}'.")
                return False, f"Chưa có ATC tạo mới (ATC này đã được bàn giao cho '{owner_name}' xử lý trước đó rồi nha anh)."
                
            update_status(f"☑️ Đã trích xuất mã ATC ẩn: {data_id}.")
            
            update_status("🚀 Bắt đầu bắn API phân công (Siêu tốc)...")
            from assign_api import assign_via_api
            success, msg = assign_via_api(data_id, internal_staff_id, update_status)
            return success, msg
            
    except Exception as e:
        return False, f"Lỗi API khi tìm kiếm ATC: {e}"

'''
    
    final_content = before_assign + new_assign_atc + end_str + parts[1]
    
    with open('crm_assigner.py', 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print("Re-wrote assign_atc function successfully.")

if __name__ == "__main__":
    rewrite()
