import os
import sys
import json
import re
import time
import datetime
import urllib.request
import urllib.parse
import html as html_lib
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import crm_api
from check_store_address import query_atcs_view_17629, get_potentials_unmasked_address, normalize_addr, clean_text, get_headers

def check_atc_detailed(aid):
    headers = get_headers()
    url_atc = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={aid}"
    req_atc = urllib.request.Request(url_atc, headers=headers)
    try:
        with urllib.request.urlopen(req_atc, timeout=12) as resp:
            h_atc = resp.read().decode('utf-8', errors='ignore')
            
        m_no = re.search(r'id=["\']CSKHSC_detailView_fieldValue_cskhsc_no["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        no = clean_text(m_no.group(1)) if m_no else aid
        
        m_ret = re.search(r'id=["\']CSKHSC_detailView_fieldValue_retailer_id["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        retailer_id = clean_text(m_ret.group(1)) if m_ret else ""
        
        m_owner = re.search(r'id=["\']CSKHSC_detailView_fieldValue_assigned_user_id["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        owner = clean_text(m_owner.group(1)) if m_owner else ""
        
        m_time = re.search(r'id=["\']CSKHSC_detailView_fieldValue_thoi_gian_checkin["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        checkin_time = clean_text(m_time.group(1)) if m_time else ""
        if not checkin_time:
            m_ctime = re.search(r'id=["\']CSKHSC_detailView_fieldValue_createdtime["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
            checkin_time = clean_text(m_ctime.group(1)) if m_ctime else ""
        
        m_actual = re.search(r'id=["\']CSKHSC_detailView_fieldValue_dia_diem_thuc_te["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL) or re.search(r'Địa điểm thực tế cửa hàng.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', h_atc, re.IGNORECASE | re.DOTALL)
        actual_addr = clean_text(m_actual.group(1)) if m_actual else ""

        m_pot = re.search(r'id=["\']CSKHSC_detailView_fieldValue_parent_id["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        pot_html = m_pot.group(1) if m_pot else h_atc
        m_pot_id = re.search(r'module=Potentials&(?:amp;)?view=Detail&(?:amp;)?record=(\d+)', pot_html)
        pot_id = m_pot_id.group(1) if m_pot_id else ""
        
        pot_addr, pot_old_addr = get_potentials_unmasked_address(pot_id) if pot_id else ("", "")
        
        norm_act = normalize_addr(actual_addr)
        norm_pot = normalize_addr(pot_addr)
        
        is_exact = (norm_act == norm_pot)
        is_match = False
        match_type = "❌ Không khớp"
        
        if not pot_addr:
            match_type = "❓ Chưa có KYC / OTP"
        elif norm_act and norm_pot:
            if is_exact or norm_act in norm_pot or norm_pot in norm_act:
                is_match = True
                match_type = "✅ Khớp 100%"
            else:
                words_act = set(norm_act.split())
                words_pot = set(norm_pot.split())
                if words_act and words_pot:
                    overlap = len(words_act & words_pot) / max(len(words_act), len(words_pot))
                    if overlap >= 0.60:
                        is_match = True
                        match_type = "⚠️ Lệch nhẹ (tên quán/viết tắt)"
                    else:
                        match_type = "❌ Lệch địa chỉ"
        
        return {
            "Mã ATC": no,
            "Retailer ID": retailer_id,
            "Người xử lý (Owner)": owner,
            "Thời gian check-in": checkin_time,
            "Địa điểm thực tế": actual_addr,
            "Mã OTP / HĐ (Potentials ID)": pot_id,
            "Địa chỉ kinh doanh mới (KYC OTP)": pot_addr,
            "Địa chỉ kinh doanh cũ": pot_old_addr,
            "Kết quả đối chiếu": match_type,
            "Link ATC": url_atc,
            "Link Potentials": f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}" if pot_id else ""
        }
    except Exception as e:
        print(f"Error checking ATC {aid}: {e}")
        return None

def main():
    start_date = "2026-10-01"
    end_date = "2026-10-20"
    print(f"🚀 Bắt đầu quét danh sách ATC đổi thông tin gian hàng từ {start_date} đến {end_date}...")
    
    atc_ids = query_atcs_view_17629(start_date, end_date)
    print(f"☑️ Tìm thấy {len(atc_ids)} ATC cần đối chiếu. Đang quét đa luồng 16 workers...")
    
    start_t = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(check_atc_detailed, aid): aid for aid in atc_ids}
        completed = 0
        for f in futures:
            res = f.result()
            if res:
                results.append(res)
            completed += 1
            if completed % 30 == 0 or completed == len(atc_ids):
                print(f"  ⏳ Tiến độ: {completed}/{len(atc_ids)} ({completed*100//len(atc_ids)}%)...")

    elapsed = time.time() - start_t
    print(f"🎉 Hoàn tất đối chiếu {len(results)}/{len(atc_ids)} ATC trong {elapsed:.1f} giây!")
    
    # Save to Excel
    df = pd.DataFrame(results)
    out_xlsx = os.path.join(CURRENT_DIR, "doi_thong_tin_01_20_10_export.xlsx")
    df.to_excel(out_xlsx, index=False)
    print(f"💾 Đã lưu kết quả ra file Excel: {out_xlsx}")
    
    # Summary stats
    stats = df["Kết quả đối chiếu"].value_counts().to_dict()
    print("\n--- THỐNG KÊ KẾT QUẢ ĐỐI CHIẾU ---")
    for k, v in stats.items():
        print(f"  • {k}: {v} ATC ({v*100/len(results):.1f}%)")

if __name__ == "__main__":
    main()
