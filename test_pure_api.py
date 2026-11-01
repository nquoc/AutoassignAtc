import urllib.request
from crm_api import get_session
import re

import sys
sys.stdout.reconfigure(encoding='utf-8')

def test_pure_api():
    cookie_str, csrf_token = get_session()
    
    url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Kh%C3%A1nh+H%C3%B2a%22%5D%5D%5D"
    
    req = urllib.request.Request(url, headers={
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0"
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            
        print("Fetched ListAjax. Length:", len(html))
        
        # Parse data-id from tr
        # <tr class="listViewEntries" data-id="105251566">
        data_ids = re.findall(r'tr[^>]*data-id=["\'](\d+)["\'][^>]*class=["\'][^"\']*listViewEntries[^"\']*["\']', html)
        print("Found data-ids:", data_ids)
        
    except Exception as e:
        print("Error fetching list:", e)
        
    # 2. To get changeOwnerId, usually we can get it from the MassEdit or ChangeOwner modal HTML
    # URL for change owner modal: 
    # index.php?module=CSKHSC&view=MassActionAjax&mode=showTransferOwnershipForm
    modal_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=MassActionAjax&mode=transferOwnership"
    req_modal = urllib.request.Request(modal_url, headers={
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0"
    })
    try:
        with urllib.request.urlopen(req_modal) as resp:
            modal_html = resp.read().decode('utf-8')
            
        options = re.findall(r'<option value=["\'](\d+)["\'][^>]*>([^<]+)</option>', modal_html)
        print("Found options in Transfer modal:", len(options))
        if options:
            print("First 3 options:", options[:3])
    except Exception as e:
        print("Error fetching modal:", e)

if __name__ == "__main__":
    test_pure_api()
