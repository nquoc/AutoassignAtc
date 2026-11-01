import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sample_data = [
  {
    "category": "Công việc",
    "id": "1784862613210",
    "name": "Gia Lai - anh Hải",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_state%22%2C%22e%22%2C%22X%C3%A3+Th%E1%BB%91ng+Nh%E1%BA%A5t%2CPh%C6%B0%E1%BB%9Dng+Th%E1%BB%91ng+Nh%E1%BA%A5t%2CX%C3%A3+An+Ph%C3%BA%2CPh%C6%B0%E1%BB%9Dng+Di%C3%AAn+H%E1%BB%93ng%2CPh%C6%B0%E1%BB%9Dng+Pleiku%2CPh%C6%B0%E1%BB%9Dng+H%E1%BB%99i+Ph%C3%BA%2CX%C3%A3+Bi%E1%BB%83n+H%E1%BB%93%2CPh%C6%B0%E1%BB%9Dng+An+Ph%C3%BA%2CX%C3%A3+G%C3%A0o%2CX%C3%A3+%C4%90ak+%C4%90oa%2CX%C3%A3+Ch%C6%B0+P%C4%83h%2CX%C3%A3+Mang+Yang%2CX%C3%A3+Ch%C6%B0+S%C3%AA%2CX%C3%A3+Ch%C6%B0+P%C6%B0h%22%5D%2C%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Gia+Lai%22%5D%5D%5D"
  },
  {
    "category": "Công việc",
    "id": "1783250083917",
    "name": "sóc trăng - Hậu giang",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_state%22%2C%22e%22%2C%22Ph%C6%B0%E1%BB%9Dng+Ph%C3%BA+L%E1%BB%A3i%2CX%C3%A3+Ch%C3%A2u+Th%C3%A0nh%2CX%C3%A3+Th%E1%BA%A1nh+H%C3%B3a%2CPh%C6%B0%E1%BB%9Dng+Ng%C3%A3+B%E1%BA%A3y%2CX%C3%A3+%C4%90%C3%B4ng+Ph%C6%B0%E1%BB%9Bc%2CX%C3%A3+Hi%E1%BB%87p+H%C6%B0ng%2CPh%C6%B0%E1%BB%9Dng+S%C3%B3c+Tr%C4%83ng%22%5D%2C%5B%22cf_city%22%2C%22e%22%2C%22Th%C3%A0nh+ph%E1%BB%91+C%E1%BA%A7n+Th%C6%A1%22%5D%5D%5D"
  },
  {
    "category": "Công việc",
    "id": "1780700433960",
    "name": "Quy Nhơn Treo",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_state%22%2C%22e%22%2C%22Ph%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+B%E1%BA%AFc%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+T%C3%A2y%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+Nam%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+%C4%90%C3%B4ng%22%5D%2C%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Gia+Lai%22%5D%5D%5D"
  },
  {
    "id": "1777784047331",
    "name": "Cần Thơ Treo",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22Th%C3%A0nh+ph%E1%BB%91+C%E1%BA%A7n+Th%C6%A1%22%5D%5D%5D"

  },
  {
    "category": "Công việc",
    "id": "1780969808131",
    "name": "Sáp Nhập treo data",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=19211&orderby=&sortorder=&search_params=&search_key=summary&search_value="
  },
  {
    "id": "1778031135532",
    "name": "Cà mau treo",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+C%C3%A0+Mau%22%5D%5D%5D"

  },
  {
    "id": "1778287731850",
    "name": "Lâm Đồng",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+L%C3%A2m+%C4%90%E1%BB%93ng%22%5D%5D%5D"
  },
  {
    "category": "Công việc",
    "id": "1784862396467",
    "name": "Khánh Hòa Treo",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=createdtime&sortorder=ASC&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Kh%C3%A1nh+H%C3%B2a%22%5D%5D%5D"
  },
  {
    "category": "Công việc",
    "id": "1780219251256",
    "name": "Qui Nhơn",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=createdtime&sortorder=ASC&search_params=%5B%5B%5B%22cf_state%22%2C%22e%22%2C%22Ph%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+B%E1%BA%AFc%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+T%C3%A2y%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+Nam%2CPh%C6%B0%E1%BB%9Dng+Quy+Nh%C6%A1n+%C4%90%C3%B4ng%22%5D%2C%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Gia+Lai%22%5D%5D%5D"
  },
  {
    "id": "1778287713034",
    "name": "Gia Lai treo",
    "url": "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=16309&orderby=&sortorder=&search_params=%5B%5B%5B%22cf_city%22%2C%22e%22%2C%22T%E1%BB%89nh+Gia+Lai%22%5D%5D%5D"
  }
]

with open("regions.json", "r", encoding="utf-8") as f:
    regions = json.load(f)

quoc_map = {}
for r in regions:
    if r.get("coacher") == "quoc":
        quoc_map[r["name"].strip().lower()] = r["url"]
        quoc_map[r["id"].strip().lower()] = r["url"]

quoc_map["khánh hòa treo"] = quoc_map.get("khánh hòa")
quoc_map["qui nhơn"] = quoc_map.get("quy nhơn treo")
quoc_map["gia lai - anh hải"] = quoc_map.get("gia lai - a hải")
quoc_map["gia lai treo"] = quoc_map.get("gia lai - a hải")
quoc_map["sóc trăng - hậu giang"] = quoc_map.get("sóc trăng - hậu giang")

for item in sample_data:
    n_clean = item["name"].strip().lower()
    if n_clean in quoc_map and quoc_map[n_clean]:
        item["url"] = quoc_map[n_clean]

with open("export_coacher_quoc.json", "w", encoding="utf-8") as f:
    json.dump(sample_data, f, indent=2, ensure_ascii=False)

print("Export completed successfully.")
