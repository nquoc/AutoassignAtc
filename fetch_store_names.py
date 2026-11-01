import os
import sys
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from quick_action import get_headers

def fetch_store_name(pot_id, headers):
    if not pot_id or str(pot_id) == 'N/A' or not str(pot_id).isdigit():
        return pot_id, ""
    url = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        el = soup.find('td', id='Potentials_detailView_fieldValue_cf_pot_website')
        if el:
            sel = el.find('option', selected=True)
            if sel: return pot_id, sel.get_text(separator=' ', strip=True)
            span = el.find('span', class_='value')
            if span: return pot_id, span.get_text(separator=' ', strip=True)
            return pot_id, el.get_text(separator=' ', strip=True)
    except Exception as e:
        pass
    return pot_id, ""

def main():
    print("🚀 Bắt đầu lấy Tên gian hàng (cf_pot_website) cho 84 bản ghi...")
    df = pd.read_excel('dia_chi_otp_thanh_cong_export.xlsx')
    headers = get_headers()
    pot_ids = df['Mã OTP / HĐ (Potentials ID)'].tolist()

    store_map = {}
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_store_name, pid, headers): pid for pid in pot_ids}
        for fut in futures:
            pid, store = fut.result()
            store_map[str(pid)] = store

    df['Tên gian hàng'] = df['Mã OTP / HĐ (Potentials ID)'].astype(str).map(store_map).fillna('')
    
    # 3-column dataframe
    df_3col = pd.DataFrame({
        'Retailer ID': df['Retailer ID'],
        'Tên gian hàng': df['Tên gian hàng'],
        'Địa chỉ chi tiết': df['Địa chỉ kinh doanh chi tiết (KYC OTP)'].apply(lambda s: re.sub(r'(_x000D_|\r|\n)+', ' ', str(s)).strip())
    })
    df_3col['Địa chỉ chi tiết'] = df_3col['Địa chỉ chi tiết'].apply(lambda s: re.sub(r'\s+', ' ', str(s)))

    # Save Excel and TSV
    xlsx_path = os.path.join(CURRENT_DIR, 'dia_chi_chi_tiet_3cot.xlsx')
    tsv_path = os.path.join(CURRENT_DIR, 'dia_chi_chi_tiet_3cot.tsv')
    df_3col.to_excel(xlsx_path, index=False)
    df_3col.to_csv(tsv_path, sep='\t', index=False, encoding='utf-8-sig')

    # Also update full export file
    df['Tên gian hàng'] = df_3col['Tên gian hàng']
    df['Địa chỉ kinh doanh chi tiết (KYC OTP)'] = df_3col['Địa chỉ chi tiết']
    df.to_excel(os.path.join(CURRENT_DIR, 'dia_chi_otp_thanh_cong_export.xlsx'), index=False)

    print(f"✅ Hoàn tất! Đã xuất file 3 cột: {xlsx_path}")

if __name__ == "__main__":
    main()
