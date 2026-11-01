import sys
from crm_api import get_region_summary
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

def test():
    url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154&orderby=&sortorder=&search_params=%5B%5B%5B%22assigned_user_id%22%2C%22c%22%2C%228465+-+H%E1%BB%93+Ng%E1%BB%8Dc+Thi%C3%AAn+Hy+-+Customer+Success+-+NTG%22%5D%5D%5D"
    
    def log(msg):
        print("LOG:", msg)
        
    res = get_region_summary(url, update_status=log)
    print("Result:", res)

if __name__ == "__main__":
    test()
