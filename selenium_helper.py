import os
import subprocess
import time

class SeleniumHelper:
    @staticmethod
    def get_chrome_profile_dir():
        return os.path.join(os.environ.get("LOCALAPPDATA"), "Checkvar_Chrome_Profile")

    @staticmethod
    def get_chrome_options(download_dir=None, headless=False):
        from selenium import webdriver
        
        options = webdriver.ChromeOptions()
        user_data_dir = SeleniumHelper.get_chrome_profile_dir()
        options.add_argument(f"user-data-dir={user_data_dir}")
        
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-crash-reporter")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-in-process-stack-traces")
            options.add_argument("--disable-logging")
            options.add_argument("--log-level=3")
            options.add_argument("--output=/dev/null")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        if download_dir:
            prefs["download.default_directory"] = download_dir
            
        options.add_experimental_option("prefs", prefs)
        return options

    @staticmethod
    def kill_orphaned_chrome_processes():
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmd = " ".join(p.info['cmdline'] or []).lower()
                    if "checkvar_chrome_profile" in cmd:
                        p.kill()
                except:
                    pass
        except:
            pass

        # Delete stale Singleton, lockfile and DevToolsActivePort files
        try:
            profile_dir = SeleniumHelper.get_chrome_profile_dir()
            if os.path.exists(profile_dir):
                for fname in os.listdir(profile_dir):
                    if fname.startswith("Singleton") or fname in ["DevToolsActivePort", "lockfile"]:
                        try:
                            os.remove(os.path.join(profile_dir, fname))
                        except:
                            pass
        except:
            pass
        time.sleep(1.0)

    @staticmethod
    def init_driver(download_dir=None, headless=False):
        # Clean up any locks first
        SeleniumHelper.kill_orphaned_chrome_processes()
        
        from selenium import webdriver
        options = SeleniumHelper.get_chrome_options(download_dir, headless)
        driver = webdriver.Chrome(options=options)
        
        if headless:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            if download_dir:
                abs_path = os.path.abspath(download_dir)
                try:
                    driver.execute_cdp_cmd('Browser.setDownloadBehavior', {
                        'behavior': 'allow',
                        'downloadPath': abs_path
                    })
                except:
                    pass
        return driver

    @staticmethod
    def try_auto_login(driver, log_callback=None):
        def update_log(msg):
            if log_callback: log_callback(msg)
            else: print(msg)

        from selenium.webdriver.common.by import By
        import time

        update_log("🔍 Phát hiện màn hình đăng nhập. Đang thử tự động đăng nhập qua Google...")
        start_time = time.time()
        
        while time.time() - start_time < 30:
            curr_url = driver.current_url.lower()
            
            is_login_page = False
            if 'login' in curr_url or 'signin' in curr_url or 'accounts.google.com' in curr_url:
                is_login_page = True
            else:
                try:
                    if driver.find_elements(By.NAME, "username") or driver.find_elements(By.ID, "username"):
                        is_login_page = True
                except:
                    pass
            
            if not is_login_page:
                update_log("🎉 Đăng nhập tự động thành công!")
                return True
                
            try:
                pass_fields = driver.find_elements(By.XPATH, "//input[@type='password']")
                if pass_fields and any(f.is_displayed() for f in pass_fields):
                    if 'accounts.google.com' in curr_url:
                        update_log("⚠️ Phát hiện Google yêu cầu mật khẩu / 2FA. Vui lòng thao tác tay!")
                        return False
            except:
                pass

            # 1. CRM Login Page
            has_username = False
            try:
                if driver.find_elements(By.NAME, "username") or driver.find_elements(By.ID, "username"):
                    has_username = True
            except:
                pass

            if ('kvcrm.kiotviet.vn' in curr_url) and ('login' in curr_url or has_username):
                try:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    google_iframe = None
                    for iframe in iframes:
                        src = iframe.get_attribute("src") or ""
                        title = iframe.get_attribute("title") or ""
                        if "gsi/button" in src or "Sign in with Google" in title:
                            google_iframe = iframe
                            break
                    
                    if google_iframe:
                        update_log("🖱 Phát hiện nút đăng nhập Google trong Iframe...")
                        driver.switch_to.frame(google_iframe)
                        time.sleep(1)
                        
                        google_btn = None
                        for xpath in [
                            "//*[contains(text(), 'quoc.na@kiotviet.com')]",
                            "//*[contains(@class, 'nsm7Bb-HzV7m-LgbsSe')]",
                            "//*[contains(text(), 'Đăng nhập với')]"
                        ]:
                            try:
                                el = driver.find_element(By.XPATH, xpath)
                                if el.is_displayed():
                                    google_btn = el
                                    break
                            except:
                                pass
                                
                        if google_btn:
                            driver.execute_script("arguments[0].click();", google_btn)
                            time.sleep(3)
                            
                        driver.switch_to.default_content()
                        continue
                    else:
                        google_btn = None
                        for xpath in [
                            "//*[contains(text(), 'quoc.na@kiotviet.com')]",
                            "//*[contains(text(), 'Đăng nhập với')]",
                            "//a[contains(@href, 'google')]",
                            "//button[contains(@class, 'google')]",
                            "//div[contains(@class, 'google')]"
                        ]:
                            try:
                                el = driver.find_element(By.XPATH, xpath)
                                if el.is_displayed():
                                    google_btn = el
                                    break
                            except:
                                pass
                        
                        if google_btn:
                            driver.execute_script("arguments[0].click();", google_btn)
                            time.sleep(3)
                            continue
                except Exception as e:
                    update_log(f"⚠️ Lỗi click nút đăng nhập CRM: {e}")
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass
            
            # 2. Google Account Chooser Page
            if 'accounts.google.com' in curr_url:
                try:
                    account_el = None
                    for xpath in [
                        "//*[contains(text(), 'quoc.na@kiotviet.com')]",
                        "//*[@data-email='quoc.na@kiotviet.com']",
                        "//*[contains(@data-email, 'kiotviet.com')]",
                        "//*[contains(text(), 'kiotviet.com')]"
                    ]:
                        try:
                            el = driver.find_element(By.XPATH, xpath)
                            if el.is_displayed():
                                account_el = el
                                break
                        except:
                            pass
                            
                    if account_el:
                        update_log("🖱 Đang click chọn tài khoản Google 'quoc.na@kiotviet.com'...")
                        curr_el = account_el
                        clicked = False
                        for _ in range(4):
                            try:
                                driver.execute_script("arguments[0].click();", curr_el)
                                time.sleep(1.5)
                                if 'accounts.google.com' not in driver.current_url.lower():
                                    clicked = True
                                    break
                                curr_el = curr_el.find_element(By.XPATH, "..")
                            except:
                                break
                        if clicked:
                            time.sleep(3)
                        continue
                except Exception as e:
                    update_log(f"⚠️ Lỗi chọn tài khoản Google: {e}")
            
            time.sleep(1)
        
        # Final check
        curr_url = driver.current_url.lower()
        is_logged_in = True
        if 'login' in curr_url or 'signin' in curr_url or 'accounts.google.com' in curr_url:
            is_logged_in = False
        else:
            try:
                if driver.find_elements(By.NAME, "username") or driver.find_elements(By.ID, "username"):
                    is_logged_in = False
            except:
                pass
                
        if is_logged_in:
            update_log("🎉 Đăng nhập tự động thành công!")
        return is_logged_in
