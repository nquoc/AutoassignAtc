import os
import sys
import json
import base64
import sqlite3
import shutil
import glob
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_chrome_master_key(local_state_path):
    import win32crypt
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:] # Strip 'DPAPI'
    master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return master_key

def decrypt_payload(cipher, master_key):
    try:
        if cipher.startswith(b'v10') or cipher.startswith(b'v11') or cipher.startswith(b'v20'):
            nonce = cipher[3:15]
            ciphertext = cipher[15:]
            aesgcm = AESGCM(master_key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode('utf-8', errors='ignore')
        else:
            import win32crypt
            decrypted = win32crypt.CryptUnprotectData(cipher, None, None, None, 0)[1]
            return decrypted.decode('utf-8', errors='ignore')
    except Exception as e:
        return ""

def extract_kiotviet_cookies():
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    chrome_user_data = os.path.join(local_app_data, "Google", "Chrome", "User Data")
    
    possible_user_data_dirs = [
        chrome_user_data,
        os.path.join(local_app_data, "Checkvar_Chrome_Profile"),
        os.path.join(local_app_data, "Microsoft", "Edge", "User Data")
    ]
    
    found_cookies = {}
    
    for u_dir in possible_user_data_dirs:
        local_state_path = os.path.join(u_dir, "Local State")
        if not os.path.exists(local_state_path):
            continue
            
        try:
            master_key = get_chrome_master_key(local_state_path)
        except Exception as e:
            continue
            
        cookie_db_paths = glob.glob(os.path.join(u_dir, "*", "Network", "Cookies")) + glob.glob(os.path.join(u_dir, "*", "Cookies"))
        
        for db_path in cookie_db_paths:
            if not os.path.exists(db_path):
                continue
                
            temp_db = os.path.join(os.environ.get("TEMP", "C:\\temp"), "temp_cookies_db")
            try:
                shutil.copyfile(db_path, temp_db)
            except Exception:
                continue
                
            try:
                conn = sqlite3.connect(temp_db)
                conn.text_factory = bytes
                cursor = conn.cursor()
                cursor.execute(b"SELECT host_key, name, value, encrypted_value FROM cookies WHERE host_key LIKE '%kiotviet%'")
                rows = cursor.fetchall()
                
                for host, name, val, enc_val in rows:
                    name_str = name.decode('utf-8', errors='ignore')
                    val_str = val.decode('utf-8', errors='ignore') if val else ""
                    
                    if val_str:
                        found_cookies[name_str] = val_str
                    elif enc_val:
                        dec_val = decrypt_payload(enc_val, master_key)
                        if dec_val:
                            found_cookies[name_str] = dec_val
                conn.close()
            except Exception as e:
                pass
            finally:
                if os.path.exists(temp_db):
                    try: os.remove(temp_db)
                    except: pass

    if found_cookies:
        cookie_str = "; ".join([f"{k}={v}" for k, v in found_cookies.items()])
        cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt")
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(cookie_str)
        print("🎉 THÀNH CÔNG! Đã trích xuất Cookie KiotViet CRM thành công từ Chrome!")
        print(f"🔑 Tổng cộng {len(found_cookies)} thẻ cookie được lưu vào file cookie.txt:")
        for k in found_cookies:
            print(f"  • {k}")
        return cookie_str
    else:
        print("❌ Không tìm thấy cookie kiotviet.vn nào trong Chrome!")
        print("💡 Vui lòng đảm bảo bạn ĐÃ ĐĂNG NHẬP vào https://kvcrm.kiotviet.vn trên trình duyệt Chrome!")
        return None

if __name__ == "__main__":
    extract_kiotviet_cookies()
