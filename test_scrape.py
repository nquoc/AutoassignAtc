import json
import urllib.request
import sys
from bs4 import BeautifulSoup
from crm_api import get_session

sys.stdout.reconfigure(encoding='utf-8')

def test():
    cookie_str, csrf = get_session()
    if not cookie_str:
        print("No session!")
        return

    # Let's test with Can Tho
    url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22Th%C3%A0nh+ph%E1%BB%91+C%E1%BA%A7n+Th%C6%A1%22%5D%5D%5D"
    
    headers = {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            rows = soup.find_all('tr', class_='listViewEntries')
            
            print(f"Found {len(rows)} rows.")
            for r in rows[:5]:
                print(f"ID: {r.get('data-id')}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
