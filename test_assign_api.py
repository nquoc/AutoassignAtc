import urllib.request
import urllib.parse
from crm_api import get_session
import sys
sys.stdout.reconfigure(encoding='utf-8')

def test_assign():
    cookie_str, csrf_token = get_session()
    if not cookie_str or not csrf_token:
        print("Không có session hợp lệ. Vui lòng đăng nhập lại.")
        return
        
    staff_id = "11216"
    atc_id = "105251538"
    
    print(f"Bắt đầu test gán ATC ID {atc_id} cho nhân sự nội bộ {staff_id} qua API...")
    
    form_data = {
        "__vtrftk": csrf_token,
        "module": "CSKHSC",
        "action": "ChangeOwnerAction",
        "viewname": "16309",
        "selected_ids[]": atc_id,
        "excluded_ids[]": "",
        "changeOwnerId": staff_id,
        "search_params": "[[]]"
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
            data = resp.read().decode('utf-8')
            print("Response status:", resp.status)
            if "login" in resp.geturl().lower() or "signin" in resp.geturl().lower():
                print("Lỗi: Bị đẩy ra trang đăng nhập (Session hết hạn hoặc lỗi CSRF).")
            else:
                print("Gửi API thành công! Phản hồi từ CRM:")
                # usually returns a JSON like {"success":true,"result":[]}
                print(data[:500])
    except Exception as e:
        print(f"Lỗi khi gửi API: {e}")

if __name__ == "__main__":
    test_assign()
