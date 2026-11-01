import sys
import json
import urllib.parse
from bs4 import BeautifulSoup
from crm_api import get_session, fetch_crm_export
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

def test():
    url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22Th%C3%A0nh+ph%E1%BB%91+C%E1%BA%A7n+Th%C6%A1%22%5D%5D%5D"
    
    # 1. Fetch Summary (Export Data)
    rows = fetch_crm_export(url)
    if rows:
        headers = rows[0]
        data_rows = rows[1:2] # Just 1 row
        summary_data = [dict(zip(headers, row)) for row in data_rows]
    else:
        summary_data = "No data from export"
        
    # 2. Fetch HTML List View (Data IDs)
    cookie_str, csrf = get_session()
    req = urllib.request.Request(url, headers={"cookie": cookie_str})
    html_data = []
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')
            table_rows = soup.select('tr.listViewEntries')
            for tr in table_rows[:1]: # Just 1 row
                row_data = {
                    "tr_attributes": tr.attrs,
                    "columns": []
                }
                
                tds = tr.find_all('td')
                for i, td in enumerate(tds):
                    col_info = {
                        "index": i,
                        "class": td.get("class", []),
                        "text": td.get_text(strip=True),
                    }
                    row_data["columns"].append(col_info)
                html_data.append(row_data)
    except Exception as e:
        html_data = str(e)
        
    output = {
        "1. TẤT CẢ FIELDS - API Export CSV (1 dòng)": summary_data,
        "2. TẤT CẢ FIELDS - API Quét HTML (1 dòng)": html_data
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test()
