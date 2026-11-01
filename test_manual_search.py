import sys
import json
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from crm_api import get_session

sys.stdout.reconfigure(encoding='utf-8')

def test():
    retailer_id = "501042157"
    search_params = [[["retailer_id", "co", str(retailer_id)]]]
    encoded_params = urllib.parse.quote(json.dumps(search_params))
    list_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params={encoded_params}"
    
    cookie_str, csrf = get_session()
    if not cookie_str:
        print("Acquiring session...")
        from crm_api import acquire_session_via_selenium
        cookie_str, csrf = acquire_session_via_selenium()
        if not cookie_str:
            print("Failed to acquire session!")
            return
        
    req = urllib.request.Request(list_url, headers={"cookie": cookie_str})
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.select('tr.listViewEntries')
            if not rows:
                print("No rows found!")
                # maybe check if there is an error or it's a different table
                return
            
            first_row = rows[0]
            data_id = first_row.get("data-id")
            
            tds = first_row.find_all('td')
            # print all cells to find the owner cell (it was cells[1] in selenium, which is index 1 or 2 in BS if there are hidden columns)
            for i, td in enumerate(tds):
                print(f"Col {i}: {td.get_text(strip=True)}")
                
            print(f"Found data-id: {data_id}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
