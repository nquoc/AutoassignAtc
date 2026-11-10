import sys
import os
import urllib.request
import urllib.parse
import json
import re
import html as html_lib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crm_api

def get_headers():
    cookie_str, _ = crm_api.get_session()
    return {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

def clean_text(t):
    if not t:
        return ""
    t = html_lib.unescape(re.sub(r'<[^>]+>', ' ', str(t))).strip()
    return re.sub(r'\s+', ' ', t)

def normalize_addr(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\.,\-_/]', ' ', s)
    s = re.sub(r'\b(tp|thành phố|tỉnh|phường|p\.|xã|thị trấn|tt|quận|q\.|huyện|h\.|ấp|đường|số|khu|kdc)\b', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def query_atcs_view_17629(start_date, end_date):
    """
    Query CSKHSC View 17629 for "Đổi thông tin gian hàng thành công" within date range across all pages.
    """
    headers = get_headers()
    search_params = json.dumps([[
        ["thoi_gian_checkin", "bw", f"{start_date},{end_date}"],
        ["cskhcs_support_work_kh", "c", "Đổi thông tin gian hàng thành công"]
    ]])
    all_ids = []
    page = 1
    while True:
        url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&viewname=17629&search_params={urllib.parse.quote(search_params)}&page={page}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode('utf-8', errors='ignore')
            matches = re.findall(r'<tr\b(?=[^>]*\bclass=["\'][^"\']*\blistViewEntries\b[^"\']*["\'])(?=[^>]*\bdata-id=["\'](\d+)["\'])[^>]*>', content)
            new_ids = [m for m in matches if m not in all_ids]
            if not new_ids:
                break
            all_ids.extend(new_ids)
            page += 1
            if page > 20:
                break
        except Exception as e:
            print(f"Error querying view 17629: {e}")
            break
    return all_ids

def get_potentials_unmasked_address(pot_id):
    """
    Fetch unmasked address from Potentials record via GetKYC API.
    Returns (addr, old_addr).
    """
    if not pot_id:
        return "", ""
    headers = get_headers()
    url_pot = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}"
    req = urllib.request.Request(url_pot, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html_pot = resp.read().decode('utf-8', errors='ignore')
        m_token = re.search(r'class=["\'][^"\']*kyc-kyc_token[^"\']*["\'][^>]*>(.*?)<', html_pot) or re.search(r'id=["\'][^"\']*kyc_token[^"\']*["\'][^>]*>(.*?)<', html_pot)
        token = m_token.group(1).strip() if m_token else ""
        
        kyc_url = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&action=GetKYC&record_id={pot_id}&token={urllib.parse.quote(token)}"
        req_kyc = urllib.request.Request(kyc_url, headers=headers)
        with urllib.request.urlopen(req_kyc, timeout=10) as resp_kyc:
            kyc_res = json.loads(resp_kyc.read().decode('utf-8'))
            if kyc_res.get("success") and kyc_res.get("result"):
                res_obj = kyc_res["result"]
                pot_addr = clean_text(res_obj.get("addr", ""))
                other_str = res_obj.get("other", "{}")
                pot_old_addr = ""
                try:
                    other_data = json.loads(other_str) if isinstance(other_str, str) else other_str
                    pot_old_addr = clean_text(other_data.get("cf_pot_diachich", ""))
                except Exception:
                    pass
                return pot_addr, pot_old_addr
    except Exception as e:
        print(f"Error fetching Potentials KYC {pot_id}: {e}")
    return "", ""

def check_single_atc(aid):
    """
    Extracts ATC info, fetches linked Potentials KYC address, and compares them.
    """
    headers = get_headers()
    url_atc = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={aid}"
    req_atc = urllib.request.Request(url_atc, headers=headers)
    try:
        with urllib.request.urlopen(req_atc, timeout=10) as resp:
            h_atc = resp.read().decode('utf-8', errors='ignore')
            
        m_no = re.search(r'id=["\']CSKHSC_detailView_fieldValue_cskhsc_no["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        no = clean_text(m_no.group(1)) if m_no else aid
        
        m_ret = re.search(r'id=["\']CSKHSC_detailView_fieldValue_retailer_id["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        retailer_id = clean_text(m_ret.group(1)) if m_ret else ""
        
        m_owner = re.search(r'id=["\']CSKHSC_detailView_fieldValue_assigned_user_id["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        owner = clean_text(m_owner.group(1)) if m_owner else ""
        
        m_actual = re.search(r'id=["\']CSKHSC_detailView_fieldValue_dia_diem_thuc_te["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL) or re.search(r'Địa điểm thực tế cửa hàng.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', h_atc, re.IGNORECASE | re.DOTALL)
        actual_addr = clean_text(m_actual.group(1)) if m_actual else ""

        m_pot = re.search(r'id=["\']CSKHSC_detailView_fieldValue_parent_id["\'][^>]*>(.*?)</td>', h_atc, re.DOTALL)
        pot_html = m_pot.group(1) if m_pot else h_atc
        m_pot_id = re.search(r'module=Potentials&(?:amp;)?view=Detail&(?:amp;)?record=(\d+)', pot_html)
        pot_id = m_pot_id.group(1) if m_pot_id else ""
        
        pot_addr, pot_old_addr = get_potentials_unmasked_address(pot_id)
        
        norm_act = normalize_addr(actual_addr)
        norm_pot = normalize_addr(pot_addr)
        
        is_exact = (norm_act == norm_pot)
        is_match = False
        match_type = "❌ Không khớp"
        
        if norm_act and norm_pot:
            if is_exact or norm_act in norm_pot or norm_pot in norm_act:
                is_match = True
                match_type = "✅ Khớp 100%"
            else:
                words_act = set(norm_act.split())
                words_pot = set(norm_pot.split())
                if words_act and words_pot:
                    overlap = len(words_act & words_pot) / max(len(words_act), len(words_pot))
                    if overlap >= 0.65:
                        is_match = True
                        match_type = "⚠️ Lệch nhẹ (tên quán/viết tắt)"
        
        return {
            "aid": aid,
            "no": no,
            "retailer_id": retailer_id,
            "owner": owner,
            "actual_addr": actual_addr,
            "pot_id": pot_id,
            "pot_addr": pot_addr,
            "pot_old_addr": pot_old_addr,
            "is_match": is_match,
            "match_type": match_type,
            "atc_link": url_atc,
            "pot_link": f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={pot_id}" if pot_id else ""
        }
    except Exception as e:
        print(f"Error checking ATC {aid}: {e}")
        return None

def check_address_by_date_range(start_date, end_date):
    """
    High-level entry point: query all ATCs by date range in view 17629 and compare addresses.
    """
    atc_ids = query_atcs_view_17629(start_date, end_date)
    if not atc_ids:
        return []
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(check_single_atc, atc_ids))
    return [r for r in results if r is not None]

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    s_date = sys.argv[1] if len(sys.argv) > 1 else "2026-08-13"
    e_date = sys.argv[2] if len(sys.argv) > 2 else "2026-08-17"
    print(f"Checking store addresses from {s_date} to {e_date}...")
    res = check_address_by_date_range(s_date, e_date)
    print(f"Done! Checked {len(res)} ATCs.")
    for r in res:
        print(f"[{r['no']}] {r['match_type']} | Thực tế: {r['actual_addr']} | OTP: {r['pot_addr']}")
