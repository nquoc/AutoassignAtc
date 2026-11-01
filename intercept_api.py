import os
import sys
import time
import json
import urllib.parse
from selenium.webdriver.common.by import By
from selenium_helper import SeleniumHelper

sys.stdout.reconfigure(encoding='utf-8')

def capture_change_owner():
    temp_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "crm_intercept")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    driver = SeleniumHelper.init_driver(temp_dir, headless=True)
    try:
        url_str = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Kh%C3%A1nh+H%C3%B2a%22%5D%5D%5D"
        driver.get(url_str)
        time.sleep(4)
        
        SeleniumHelper.try_auto_login(driver)
        driver.get(url_str)
        time.sleep(4)
        
        # Inject XHR interceptor
        inject_js = """
        window.interceptedRequests = [];
        var open = XMLHttpRequest.prototype.open;
        var send = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(method, url) {
            this._url = url;
            this._method = method;
            open.apply(this, arguments);
        };
        XMLHttpRequest.prototype.send = function(data) {
            if (this._method.toUpperCase() === 'POST' && this._url.indexOf('index.php') !== -1) {
                window.interceptedRequests.push({
                    url: this._url,
                    method: this._method,
                    data: data
                });
            }
            send.apply(this, arguments);
        };
        """
        driver.execute_script(inject_js)
        
        # Select 1 record
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.listViewEntries, tr[data-id]")
        if not rows:
            print("No rows found!")
            return
            
        checkbox = rows[0].find_element(By.CSS_SELECTOR, "input.listViewEntriesCheckBox")
        driver.execute_script("arguments[0].click();", checkbox)
        time.sleep(1)
        
        # Click Actions
        buttons = driver.find_elements(By.CSS_SELECTOR, "button.dropdown-toggle")
        actions_btn = None
        for btn in buttons:
            if "actions" in btn.text.strip().lower():
                actions_btn = btn
                break
        driver.execute_script("arguments[0].click();", actions_btn)
        time.sleep(1)
        
        # Click Change Owner
        change_owner_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Change Owner')]")
        driver.execute_script("arguments[0].click();", change_owner_link)
        time.sleep(2)
        
        # Select first staff in modal
        modal = driver.find_element(By.ID, "transferOwnershipContainer")
        select_el = modal.find_element(By.ID, "changeOwnerId")
        options = select_el.find_elements(By.TAG_NAME, "option")
        
        target_val = options[1].get_attribute("value")
        print(f"Target staff id: {target_val}")
        
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
        driver.execute_script(js_select, target_val)
        time.sleep(1)
        
        # Click Save
        save_btn = modal.find_element(By.CSS_SELECTOR, "button[type='submit']")
        driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(3)
        
        # Get intercepted requests
        reqs = driver.execute_script("return window.interceptedRequests;")
        print("Captured POST requests:")
        for r in reqs:
            if isinstance(r['data'], str) and 'action=' in r['data']:
                print(r['url'])
                print(urllib.parse.unquote(r['data']))
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

capture_change_owner()
