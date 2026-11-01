import sys
import os
import json
import urllib.request
import urllib.parse
import re
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

sys.path.insert(0, r"h:\My Drive\tools\AutoassignAtc")
import crm_api

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

RETAILER_IDS = [
    "500993560", "500808312", "501158391", "500729798", "501043307",
    "501115640", "500894645", "500302084", "500542761", "500459994",
    "501054919", "501112501", "500612536", "500895374", "501133527",
    "501070419", "501058095", "500702010", "501133156", "501065292",
    "500710693", "501012637", "501194399", "500128696", "500462849",
    "500919714", "500470033", "500822348", "500783027", "500802949",
    "500821992", "500877328", "500444972", "501013177", "500525231",
    "500792760", "501088928", "501081437", "501031034", "501035625",
    "501133693", "501166777", "501169255", "501055035", "501130841",
    "500156477", "501144556", "501090934", "501091611", "501045211",
    "501152983", "500741400", "501132345", "500274596", "501043624",
    "501137136", "501203718", "500868921", "501154771", "500885749",
    "501160189", "501152045", "500948629", "1468709",   "500186998",
    "501132718", "501170813", "500099743", "500140325", "501118370",
    "500622556", "500983417", "501087244", "500218820", "501094754",
    "500573556", "500409373", "500470156", "500038620", "501099040",
    "501119924", "501127942", "501076213", "500885578", "501091731",
    "500278096", "500800172", "501054444", "500546772", "952547",
    "239302",    "501052763", "501100958", "501147273", "501119946",
    "1365596",   "500017918", "501199267", "501058057", "501183864",
    "501122470", "501181835", "501161338", "501187333", "501130494",
    "501051863", "501160565", "501196837", "501199039", "501095710",
    "500365044", "500805747", "501121322", "501026835", "500725452",
    "500925262", "501163698", "501077734", "501082804", "501102948",
    "501096870", "501128616", "501159016", "501073795", "501040703",
    "500619926", "861892",    "501156224", "501150578", "501153535",
    "500919269", "500496466", "501037204", "500744337", "500560306",
    "500808106", "500822792", "705103",    "500504777", "501045704",
    "500725305", "501002032", "500822712", "500633281", "1431513",
    "501113779", "501050405", "1438982",   "501116963", "501196373",
    "500969152", "501160332", "500708063", "500630429", "501121320",
    "500972986", "501076930", "500958113", "501090843", "501084047",
    "500956924", "500846048", "500601670", "500875172", "501066754",
    "501075997", "501087146", "501055883", "500903814", "501056869",
    "501168543", "501192072", "501023096", "501165314", "501173836",
    "501201125", "501145997", "500880009", "500924723", "500762306",
    "500539426", "500479794", "501202323", "501025625", "501186447",
    "500790750", "500958859", "501017868", "500024019", "501198922",
    "501187054", "500816379", "501182496", "501088897", "500266777",
    "500426297", "501043917", "501189246", "500099640", "500979318",
    "875371",    "500555085", "792061",    "500885860", "500899209",
    "500783628", "500529331", "500818762", "501028291", "500989334",
    "501016362"
]

def fetch_store_name(rid, cookie_str):
    headers = {
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-requested-with": "XMLHttpRequest"
    }
    
    # 1. Primary Method: BasicAjax showSearchResults
    url_search = f"https://kvcrm.kiotviet.vn/index.php?module=Vtiger&view=BasicAjax&mode=showSearchResults&value={urllib.parse.quote(rid)}"
    try:
        req = urllib.request.Request(url_search, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(html, 'html.parser')
        candidate_stores = []
        for span in soup.find_all('span', style=re.compile(r'font-size:\s*11px')):
            txt = span.get_text(strip=True)
            # Check for exact match with rid
            # e.g. "hkdbodesao - 500993560" or "hkdbodesao- 500993560"
            parts = re.split(r'\s*[-–—]\s*', txt)
            if len(parts) >= 2:
                # The rid part should match exactly
                for i in range(1, len(parts)):
                    if parts[i].strip() == rid:
                        store_name = "-".join(parts[:i]).strip()
                        if store_name:
                            candidate_stores.append(store_name)
                            break
                            
        if candidate_stores:
            # Pick most common or first clean store name
            return rid, candidate_stores[0], "OK"
    except Exception as e:
        pass

    # 2. Fallback 1: Search CSKHSC List View
    try:
        sp_sc = [[["retailer_id", "e", str(rid)]]]
        url_sc = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=List&search_params={urllib.parse.quote(json.dumps(sp_sc))}"
        req_sc = urllib.request.Request(url_sc, headers=headers)
        with urllib.request.urlopen(req_sc, timeout=10) as resp_sc:
            html_sc = resp_sc.read().decode('utf-8', errors='ignore')
        soup_sc = BeautifulSoup(html_sc, 'html.parser')
        rows = soup_sc.select('tr.listViewEntries')
        for tr in rows:
            for td in tr.find_all('td'):
                f_name = td.get('data-field-name', '')
                if f_name in ['cf_website', 'contact_id']:
                    txt = td.get_text(strip=True)
                    if txt:
                        return rid, txt, "OK (CSKHSC)"
    except Exception:
        pass

    # 3. Fallback 2: Search HelpDesk List View
    try:
        sp_hd = [[["retailer_id", "e", str(rid)]]]
        url_hd = f"https://kvcrm.kiotviet.vn/index.php?module=HelpDesk&view=List&search_params={urllib.parse.quote(json.dumps(sp_hd))}"
        req_hd = urllib.request.Request(url_hd, headers=headers)
        with urllib.request.urlopen(req_hd, timeout=10) as resp_hd:
            html_hd = resp_hd.read().decode('utf-8', errors='ignore')
        soup_hd = BeautifulSoup(html_hd, 'html.parser')
        rows = soup_hd.select('tr.listViewEntries')
        for tr in rows:
            for td in tr.find_all('td'):
                f_name = td.get('data-field-name', '')
                if f_name in ['cf_website', 'contact_id']:
                    txt = td.get_text(strip=True)
                    if txt:
                        return rid, txt, "OK (HelpDesk)"
    except Exception:
        pass

    return rid, "Không tìm thấy", "NOT_FOUND"

def main():
    cookie_str, csrf = crm_api.get_session()
    if not cookie_str:
        print("🔑 Đang lấy cookie CRM...")
        try:
            from extract_crm_cookie import extract_kiotviet_cookies
            cookie_str = extract_kiotviet_cookies()
        except:
            pass
        if not cookie_str:
            cookie_str, csrf = crm_api.acquire_session_via_selenium()
            
    if not cookie_str:
        print("❌ Không lấy được cookie CRM!")
        return

    print(f"🚀 Bắt đầu quét {len(RETAILER_IDS)} Retailer IDs đa luồng (12 workers)...")
    start_time = time.time()
    
    results = {}
    completed_count = 0
    total = len(RETAILER_IDS)
    
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_store_name, rid, cookie_str): rid for rid in RETAILER_IDS}
        for future in as_completed(futures):
            rid, store, status = future.result()
            results[rid] = store
            completed_count += 1
            if completed_count % 20 == 0 or completed_count == total:
                print(f"  ⏳ Đã xử lý {completed_count}/{total} ({(completed_count/total)*100:.1f}%) - {rid} -> {store}")
                
    elapsed = time.time() - start_time
    print(f"\n🎉 HOÀN THÀNH QUÉT {total} GIAN HÀNG TRONG {elapsed:.1f} GIÂY!")
    
    # Save to Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Danh Sach Gian Hang"
    
    # Header styling
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    border_thin = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    headers = ["STT", "Retailer ID", "Tên Gian Hàng"]
    ws.append(headers)
    for col in range(1, 4):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin
        
    for idx, rid in enumerate(RETAILER_IDS, start=1):
        store = results.get(rid, "Không tìm thấy")
        row_cells = [idx, int(rid) if rid.isdigit() else rid, store]
        ws.append(row_cells)
        r_idx = idx + 1
        ws.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=r_idx, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=r_idx, column=3).alignment = Alignment(horizontal="left")
        for col in range(1, 4):
            ws.cell(row=r_idx, column=col).border = border_thin
            
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 18
    ws.column_dimensions['C'].width = 35
    
    export_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Danh_Sach_Ten_Gian_Hang_20261001.xlsx")
    wb.save(export_file)
    print(f"📊 Đã xuất file Excel: {export_file}")
    
    # Output json results
    json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retailer_store_names.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump([{"stt": i, "retailer_id": rid, "store_name": results.get(rid, "")} for i, rid in enumerate(RETAILER_IDS, start=1)], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
