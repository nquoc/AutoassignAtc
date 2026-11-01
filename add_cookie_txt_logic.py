import os

def run():
    target = 'crm_api.py'
    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    old_get_session = """def get_session():
    if os.path.exists(SESSION_FILE):"""
    
    new_get_session = """def get_session():
    # 1. Manual cookie from cookie.txt (highest priority)
    cookie_txt_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt")
    if os.path.exists(cookie_txt_file):
        try:
            with open(cookie_txt_file, "r", encoding="utf-8") as f:
                cookie_content = f.read().strip()
                if cookie_content and check_cookie_valid(cookie_content):
                    return cookie_content, "" # CSRF will be fetched dynamically
        except:
            pass

    # 2. Existing session file
    if os.path.exists(SESSION_FILE):"""

    if old_get_session in content:
        content = content.replace(old_get_session, new_get_session)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated get_session() to support cookie.txt")
    else:
        print("Could not find get_session() signature.")

if __name__ == "__main__":
    run()
