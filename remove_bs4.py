import sys
import re

def run():
    with open('crm_assigner.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Rewrite assign_atc parsing
    old_assign_atc = """            from bs4 import BeautifulSoup
            
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
                owner_name = tds[1].get_text(strip=True)"""
                
    new_assign_atc = """            import re
            
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
                    
            # Use regex to find first row
            row_match = re.search(r'<tr[^>]*class="[^"]*listViewEntries[^"]*"[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
            if not row_match:
                update_status(f"⚠️ Chưa có ATC tạo mới cho Retailer ID {retailer_id}!")
                return False, f"Chưa có ATC tạo mới (Không tìm thấy record CSKHSC nào cho Retailer ID {retailer_id})."
                
            # Extract data-id
            data_id_match = re.search(r'data-id="(\d+)"', html) # Find the first data-id in the html (which belongs to the first row)
            if not data_id_match:
                return False, "Không thể trích xuất data-id từ kết quả."
            data_id = data_id_match.group(1)
            
            # Extract tds
            tr_content = row_match.group(1)
            tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_content, re.DOTALL | re.IGNORECASE)
            owner_name = "Unknown"
            if len(tds) > 1:
                # Strip internal html tags
                owner_name = re.sub(r'<[^>]+>', '', tds[1]).strip()"""
    
    content = content.replace(old_assign_atc, new_assign_atc)
    
    # Rewrite assign_region_data parsing
    old_assign_region = """            from bs4 import BeautifulSoup
            
            if "login" in response.geturl().lower() or "signin" in response.geturl().lower():
                update_status("🔑 Session đã hết hạn, đang mở trình duyệt ẩn để tự động đăng nhập lại CRM...")
                cookie_str, csrf = acquire_session_via_selenium("16309", update_status=update_status)
                if not cookie_str:
                    return False, "Đăng nhập tự động thất bại."
                req = urllib.request.Request(list_url, headers={"cookie": cookie_str})
                with urllib.request.urlopen(req) as response2:
                    html = response2.read().decode('utf-8')
                    soup = BeautifulSoup(html, 'html.parser')
            else:
                soup = BeautifulSoup(html, 'html.parser')
                
            rows = soup.select('tr.listViewEntries')
            for r in rows:
                data_id = r.get("data-id")
                if data_id:
                    data_ids.append(data_id)"""
                    
    new_assign_region = """            import re
            if "login" in response.geturl().lower() or "signin" in response.geturl().lower():
                update_status("🔑 Session đã hết hạn, đang mở trình duyệt ẩn để tự động đăng nhập lại CRM...")
                cookie_str, csrf = acquire_session_via_selenium("16309", update_status=update_status)
                if not cookie_str:
                    return False, "Đăng nhập tự động thất bại."
                req = urllib.request.Request(list_url, headers={"cookie": cookie_str})
                with urllib.request.urlopen(req) as response2:
                    html = response2.read().decode('utf-8')
            
            # Find all data-ids for listViewEntries
            # Each row is <tr class="listViewEntries" data-id="123"...
            data_ids = re.findall(r'<tr[^>]*class="[^"]*listViewEntries[^"]*"[^>]*data-id="(\d+)"', html)
            # If attributes are in different order, a fallback regex:
            if not data_ids:
                # Find all tr blocks with listViewEntries, then extract data-id from them
                tr_blocks = re.findall(r'<tr[^>]*class="[^"]*listViewEntries[^"]*"[^>]*>', html, re.IGNORECASE)
                for tr in tr_blocks:
                    m = re.search(r'data-id="(\d+)"', tr)
                    if m:
                        data_ids.append(m.group(1))"""
                        
    content = content.replace(old_assign_region, new_assign_region)

    with open('crm_assigner.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Replaced bs4 with re.")

if __name__ == "__main__":
    run()
