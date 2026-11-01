import sys
import urllib.request
import re
import json
from crm_api import get_session

sys.stdout.reconfigure(encoding='utf-8')

def test_debug():
    cookie_str, csrf_token = get_session()
    print("Session Cookie:", cookie_str[:20] if cookie_str else None)
    
    modal_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=MassActionAjax&mode=transferOwnership"
    req = urllib.request.Request(modal_url, headers={
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0"
    })
    
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
        print("HTML length:", len(html))
        options = re.findall(r'<option value=["\'](\d+)["\'][^>]*>([^<]+)</option>', html)
        print("Found options count:", len(options))
        if options:
            print("First 3 options:", options[:3])
            
        for opt in options:
            text = opt[1].strip()
            match = re.search(r'\b(\d{4,6})\b', text)
            if match:
                s_id = match.group(1)
                if s_id == "8178":
                    print("Found 8178:", opt)
                
    except Exception as e:
        print("Error fetching modal:", e)

if __name__ == "__main__":
    test_debug()
