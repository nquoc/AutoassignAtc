import os
import sys
import time
import json
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt")

def check_cookie_valid(cookie_str):
    if not cookie_str:
        return False
    try:
        url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname=16309"
        req = urllib.request.Request(url, headers={"cookie": cookie_str, "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            final_url = response.geturl().lower()
            if "login" in final_url or "signin" in final_url or "accounts.google.com" in final_url:
                return False
            html = response.read().decode('utf-8', errors='ignore')
            if 'name="username"' in html or 'id="username"' in html:
                return False
            return True
    except:
        return False

def save_cookie_str(cookie_str):
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        f.write(cookie_str)
    print("🎉 THÀNH CÔNG! Đã lưu Cookie hợp lệ vào file cookie.txt!")

def try_get_from_clipboard():
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        if data:
            data_str = data.strip()
            cookie_val = ""
            csrf_val = ""
            
            # Try parse JSON format from Extension
            if data_str.startswith("{") and "cookie_str" in data_str:
                try:
                    obj = json.loads(data_str)
                    cookie_val = obj.get("cookie_str", "")
                    csrf_val = obj.get("csrf_token", "")
                except:
                    pass
            else:
                cookie_val = data_str

            if cookie_val and ("KVCRM_PHPSESSID" in cookie_val or "kvcrm_phpsessid" in cookie_val or "current_user" in cookie_val or "PHPSESSID" in cookie_val):
                print("[*] Phát hiện dữ liệu Cookie / Session trong Clipboard! Đang kiểm tra...")
                if check_cookie_valid(cookie_val):
                    save_cookie_str(cookie_val)
                    if csrf_val:
                        session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
                        with open(session_file, "w", encoding="utf-8") as f:
                            json.dump({
                                "cookie_str": cookie_val,
                                "csrf_token": csrf_val,
                                "timestamp": time.time()
                            }, f, indent=4)
                        print("🎉 Đã lưu đầy đủ cả Cookie và CSRF Token vào session.json!")
                    return True
                else:
                    print("⚠️ Đã tìm thấy Cookie trong Clipboard nhưng không hợp lệ hoặc đã hết hạn!")
    except:
        pass
    return False

def run_selenium_grabber():
    print("[*] Đang mở trình duyệt Chrome để hỗ trợ lấy Cookie tự động...")
    try:
        from crm_api import acquire_session_via_selenium, check_cookie_valid
        c_str, csrf = acquire_session_via_selenium(allow_gui_fallback=True)
        if c_str and check_cookie_valid(c_str):
            print("🎉 THÀNH CÔNG! Đã lấy và lưu Cookie KiotViet CRM thành công!")
            return True
        else:
            print("❌ Chưa lấy được Cookie hợp lệ.")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi chạy luồng lấy Cookie tự động: {e}")
        return False

def main():
    print("============================================")
    print(" 🛠 HỖ TRỢ LẤY COOKIE KIOTVIET CRM TỰ ĐỘNG")
    print("============================================")
    
    if try_get_from_clipboard():
        print("============================================")
        return

    print("\n💡 HƯỚNG DẪN LẤY COOKIE SIÊU NHANH (3 GIÂY):")
    print(" 1. Mở Chrome nơi bạn ĐÃ ĐĂNG NHẬP trang https://kvcrm.kiotviet.vn")
    print(" 2. Nhấn phím F12 -> chọn tab Console")
    print(" 3. Dán dòng lệnh sau và nhấn Enter:\n")
    print("      copy(document.cookie)\n")
    print(" 4. Chạy lại file auto_get_cookie.py này, script sẽ tự động đọc từ Clipboard!\n")
    print("============================================")
    
    if not sys.stdin.isatty():
        print("[*] Chạy tự động: Đang kích hoạt mở cửa sổ Chrome mới...")
        run_selenium_grabber()
        return

    print("Hoặc chọn hành động:")
    print(" 1. Mở cửa sổ Chrome mới để đăng nhập 1-Click")
    print(" 2. Nhập thủ công chuỗi Cookie")
    
    choice = input("Nhập lựa chọn (1 hoặc 2) [Mặc định 1]: ").strip()
    if choice == "2":
        manual_str = input("Dán chuỗi Cookie của bạn vào đây: ").strip()
        if check_cookie_valid(manual_str):
            save_cookie_str(manual_str)
        else:
            print("❌ Chuỗi Cookie không hợp lệ hoặc đã hết hạn.")
    else:
        run_selenium_grabber()

if __name__ == "__main__":
    main()
