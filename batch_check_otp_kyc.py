import os
import sys
import re
import time
import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import crm_api
from quick_action import get_headers

RETAILER_LIST = [
    "200052131", "200109324", "200130927", "200064546", "200114448", "200117851",
    "200110682", "200071463", "200116337", "200109857", "200120201", "200126458",
    "200085435", "200124262", "200127281", "200091462", "200048937", "200095489",
    "200108115", "200113334", "200128270", "200120814", "200081595", "200123453",
    "200129641", "200128839", "200128736", "200111573", "200128399", "200115496",
    "200072275", "200128397", "200128118", "200106569", "200111752", "200114411",
    "200114602", "200107187", "200116747", "200044435", "200112726", "200111076",
    "200131063", "200123070", "200086566", "200115349", "200106419", "200105376",
    "200088600", "200124033", "200044915", "200104069", "200055244", "200123919",
    "200109302", "200124280", "200131115", "200104178", "200128406", "200100757",
    "200109469", "200127737", "200123262", "200125155", "200126561", "200102875",
    "200081619", "200101930", "200125758", "200103929", "200063050", "200122492",
    "200045772", "200093540", "200066842", "200094150", "200097842", "200125154",
    "200126575", "200124342", "200107199", "200105091", "200100856", "200108716"
]

def fetch_single_otp_info(ret_id, headers):
    q_item = str(ret_id).strip()
    req_headers = dict(headers)
    req_headers["x-requested-with"] = "XMLHttpRequest"

    # Search Potentials via BasicAjax
    url_search = f"https://kvcrm.kiotviet.vn/index.php?module=Vtiger&view=BasicAjax&mode=showSearchResults&value={urllib.parse.quote(q_item)}"
    try:
        req = urllib.request.Request(url_search, headers=req_headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            h_s = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        h_s = ""

    soup_s = BeautifulSoup(h_s, 'html.parser')
    pot_rows = soup_s.find_all('tr', id=re.compile(r'Potentials_globalSearch'))
    candidates = []
    for tr in pot_rows:
        crmid = tr.get('data-crmid')
        tds = tr.find_all('td')
        if not crmid or not tds:
            continue
        title = tds[0].get_text(separator=' ', strip=True) if len(tds) > 0 else ''
        status = tds[1].get_text(separator=' ', strip=True) if len(tds) > 1 else ''
        created_time = tds[3].get_text(separator=' ', strip=True) if len(tds) > 3 else ''
        candidates.append({
            'crmid': crmid,
            'title': title,
            'status': status,
            'created_time': created_time
        })

    pot_id = None
    # 1. Ưu tiên Hợp đồng có trạng thái 'Thành công' gần nhất (Closed Won)
    success_candidates = [
        c for c in candidates 
        if any(w in c['status'].lower() for w in ['thành công', 'thanh cong', 'closed won'])
    ]
    if success_candidates:
        success_candidates.sort(key=lambda x: x['created_time'], reverse=True)
        pot_id = success_candidates[0]['crmid']
    elif candidates:
        # Nếu không có HĐ Thành công, lấy HĐ mới nhất
        candidates.sort(key=lambda x: x['created_time'], reverse=True)
        pot_id = candidates[0]['crmid']

    if not pot_id:
        return {
            "retailer_id": q_item,
            "pot_id": "N/A",
            "potential_name": "Không tìm thấy OTP/HĐ",
            "contract_no": "N/A",
            "contact_name": "N/A",
            "phone": "N/A",
            "addr": "Không tìm thấy HĐ",
            "ward": "N/A",
            "city": "N/A",
            "email": "N/A",
            "passport": "",
            "owner": "N/A",
            "status": "N/A",
            "created_time": "N/A",
            "link": ""
        }

    # Fetch detail Potentials
    url_d = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    try:
        req_d = urllib.request.Request(url_d, headers=headers)
        with urllib.request.urlopen(req_d, timeout=10) as resp_d:
            html_d = resp_d.read().decode('utf-8', errors='ignore')
    except Exception:
        html_d = ""

    soup = BeautifulSoup(html_d, 'html.parser')
    def get_f(fld):
        el = soup.find('td', id=f"Potentials_detailView_fieldValue_{fld}")
        if not el: return ""
        sel = el.find('option', selected=True)
        if sel: return sel.get_text(separator=' ', strip=True)
        span = el.find('span', class_='value')
        if span: return span.get_text(separator=' ', strip=True)
        return el.get_text(separator=' ', strip=True)

    # Decrypt KYC Data
    kyc_res = crm_api.get_kyc_data("Potentials", pot_id)
    kyc_info = kyc_res.get("result", {}) if kyc_res.get("success") else {}
    other_p = kyc_info.get("other_parsed", {})

    addr = kyc_info.get("addr") or other_p.get("cf_pot_diachich") or get_f("cf_contact_street")
    if addr == "********":
        addr = get_f("cf_pot_diachich") or ""

    phone = kyc_info.get("phone_not_hiden") or kyc_info.get("phone") or get_f("cf_mobile")
    email = kyc_info.get("email") or get_f("cf_email")
    if email == "********": email = ""
    passport = other_p.get("passport") or get_f("cf_passport")

    return {
        "retailer_id": get_f("retailer_id") or q_item,
        "pot_id": pot_id,
        "potential_name": get_f("potentialname"),
        "contract_no": get_f("cf_pot_contractid") or get_f("potential_no"),
        "contact_name": get_f("contact_id"),
        "phone": phone,
        "addr": addr,
        "ward": get_f("cf_state"),
        "city": get_f("cf_city"),
        "email": email,
        "passport": passport if passport != "N/A" else "",
        "owner": get_f("assigned_user_id"),
        "status": get_f("sales_stage"),
        "created_time": get_f("createdtime"),
        "link": f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    }

def main():
    print(f"🚀 Bắt đầu quét và giải mã KYC địa chỉ OTP thành công gần nhất cho {len(RETAILER_LIST)} Retailer IDs...")
    headers = get_headers()
    results = []
    completed = 0
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_otp_info, rid, headers): rid for rid in RETAILER_LIST}
        for fut in futures:
            rid = futures[fut]
            try:
                res = fut.result()
                if res:
                    results.append(res)
            except Exception as e:
                print(f"Lỗi Retailer {rid}: {e}")
            completed += 1
            if completed % 10 == 0 or completed == len(RETAILER_LIST):
                print(f"   ⏳ Đã hoàn thành: {completed}/{len(RETAILER_LIST)} ({completed*100//len(RETAILER_LIST)}%)...")

    # Sort results in original order of RETAILER_LIST
    order_map = {rid: i for i, rid in enumerate(RETAILER_LIST)}
    results.sort(key=lambda x: order_map.get(str(x['retailer_id']), 9999))

    # Export to Excel
    export_path = os.path.join(CURRENT_DIR, "dia_chi_otp_thanh_cong_export.xlsx")
    df = pd.DataFrame(results)
    col_mapping = {
        "retailer_id": "Retailer ID",
        "pot_id": "Mã OTP / HĐ (Potentials ID)",
        "potential_name": "Tên Hợp đồng",
        "status": "Giai đoạn HĐ",
        "addr": "Địa chỉ kinh doanh chi tiết (KYC OTP)",
        "ward": "Phường / Xã",
        "city": "Tỉnh / Thành phố",
        "contact_name": "Khách hàng / Đại diện",
        "phone": "Số điện thoại (KYC)",
        "email": "Email (KYC)",
        "contract_no": "Số hợp đồng",
        "owner": "Người xử lý",
        "created_time": "Ngày tạo HĐ",
        "link": "Link CRM"
    }
    df_export = df[[c for c in col_mapping.keys() if c in df.columns]].rename(columns=col_mapping)
    df_export.to_excel(export_path, index=False)
    print(f"\n✅ ĐÃ XUẤT FILE EXCEL: {export_path}")
    print(f"⏱️ Tổng thời gian: {time.time() - t_start:.2f} giây.")

if __name__ == "__main__":
    main()
