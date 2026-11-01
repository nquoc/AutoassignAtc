import os
import time
from selenium.webdriver.common.by import By
from selenium_helper import SeleniumHelper
import json

def capture_network():
    temp_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "crm_intercept2")
    driver = SeleniumHelper.init_driver(temp_dir, headless=True)
    try:
        url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Kh%C3%A1nh+H%C3%B2a%22%5D%5D%5D"
        driver.get(url)
        time.sleep(4)
        SeleniumHelper.try_auto_login(driver)
        
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
            if (this._url.indexOf('index.php') !== -1) {
                window.interceptedRequests.push({
                    url: this._url,
                    method: this._method,
                    data: data
                });
            }
            send.apply(this, arguments);
        };
        """
        driver.get(url)
        driver.execute_script(inject_js)
        time.sleep(4)
        
        # also click change owner to capture that
        change_owner_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Change Owner')]")
        driver.execute_script("arguments[0].click();", change_owner_link)
        time.sleep(2)
        
        reqs = driver.execute_script("return window.interceptedRequests;")
        with open("network_log.json", "w", encoding="utf-8") as f:
            json.dump(reqs, f, indent=2)
            
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_network()
