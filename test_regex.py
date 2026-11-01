import urllib.request
import urllib.parse
import json
import re
import sys
from crm_api import get_session

sys.stdout.reconfigure(encoding='utf-8')

def test():
    retailer_id = "501163917"
    cookie_str, csrf = get_session()
    search_params = [[["retailer_id", "co", str(retailer_id)]]]
    encoded_params = urllib.parse.quote(json.dumps(search_params))
    list_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params={encoded_params}"
    
    req = urllib.request.Request(list_url, headers={"cookie": cookie_str})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        
    row_match = re.search(r'<tr[^>]*class="[^"]*listViewEntries[^"]*"[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
    if not row_match:
        print("No row found")
        return
        
    print("Full TR tag:", row_match.group(0)[:300]) # Print first 300 chars of the TR
    data_id_match = re.search(r'data-id="(\d+)"', row_match.group(0))
    data_id = data_id_match.group(1) if data_id_match else None
    print("Data-ID full match:", data_id_match.group(0) if data_id_match else None)
    
    tr_content = row_match.group(1)
    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr_content, re.DOTALL | re.IGNORECASE)
    if len(tds) > 1:
        owner_name = re.sub(r'<[^>]+>', '', tds[1]).strip()
        print("Owner name:", owner_name)

if __name__ == "__main__":
    test()
