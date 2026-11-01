import sys

sys.stdout.reconfigure(encoding='utf-8')

def replace_in_file(filepath, old_text, new_text):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(old_text, new_text)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
def refactor():
    # 1. crm_api.py
    replace_in_file('crm_api.py',
                    'def fetch_crm_export(url_str, force_refresh=False):',
                    'def fetch_crm_export(url_str, force_refresh=False, update_status=None):')
    
    replace_in_file('crm_api.py',
                    'cookie_str, csrf_token = acquire_session_via_selenium(viewname)',
                    'cookie_str, csrf_token = acquire_session_via_selenium(viewname, update_status)')
                    
    replace_in_file('crm_api.py',
                    'def get_region_summary(url_str):',
                    'def get_region_summary(url_str, update_status=None):')
                    
    replace_in_file('crm_api.py',
                    'rows = fetch_crm_export(url_str)',
                    'rows = fetch_crm_export(url_str, update_status=update_status)')

    # 2. bot.py
    replace_in_file('bot.py',
                    'summary = get_region_summary(region[\'url\'])',
                    '''def log_status(msg):
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg)
            except:
                pass
        summary = get_region_summary(region['url'], update_status=log_status)''')

    # 3. crm_assigner.py (already has update_status, but need to pass it to acquire_session_via_selenium if get_session fails)
    # Right now, assign_region_data has:
    # cookie_str, csrf = get_session()
    # if not cookie_str:
    #     return False, "Không có session hợp lệ. Xin hãy lấy lại session."
    
    with open('crm_assigner.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    old_code = '''    cookie_str, csrf = get_session()
    if not cookie_str:
        return False, "Không có session hợp lệ. Xin hãy lấy lại session."'''
        
    new_code = '''    cookie_str, csrf = get_session()
    if not cookie_str:
        log("🔑 Session đã hết hạn, đang mở trình duyệt ẩn để tự động đăng nhập lại CRM (khoảng 15 giây)...")
        from crm_api import acquire_session_via_selenium
        cookie_str, csrf = acquire_session_via_selenium("16309", update_status=log)
        if not cookie_str:
            return False, "Không có session hợp lệ. Đăng nhập tự động thất bại."'''
            
    content = content.replace(old_code, new_code)
    
    with open('crm_assigner.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Refactor complete.")

if __name__ == "__main__":
    refactor()
