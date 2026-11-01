import os
import sys
import json
import re
import time
import gspread

# Ensure current dir is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import crm_api

def get_hcm_crm_data():
    """
    Fetch live CRM unassigned wards and staff holdings for HCM.
    """
    regions_file = os.path.join(BASE_DIR, "regions.json")
    with open(regions_file, "r", encoding="utf-8") as f:
        all_regions = json.load(f)
        
    hcm_reg = next((r for r in all_regions if r["id"].lower() == "hcm"), None)
    if not hcm_reg:
        raise ValueError("Không tìm thấy cấu hình khu vực HCM trong regions.json")
        
    # 1. Fetch unassigned summary
    summary = crm_api.get_region_summary(hcm_reg["url"])
    if not summary:
        raise ValueError("Không thể lấy dữ liệu data treo chưa gán từ CRM")
        
    unassigned_wards = summary.get("wards", {}) # {ward_name: count}
    
    # 2. Fetch staff holdings
    target_staff_ids = hcm_reg.get("staff_ids", [])
    view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"
    rows = crm_api.fetch_crm_export(view_url)
    
    staff_holdings = {sid: 0 for sid in target_staff_ids}
    if rows and len(rows) > 0:
        headers = rows[0]
        o_idx = headers.index("Người xử lý") if "Người xử lý" in headers else 13
        for r in rows[1:]:
            if len(r) > o_idx:
                owner = r[o_idx].strip()
                for sid in target_staff_ids:
                    if sid in owner:
                        staff_holdings[sid] += 1
                        break
                        
    return hcm_reg, staff_holdings, unassigned_wards

def map_wards_to_staff(unassigned_wards, master_data):
    personnel = master_data["personnel"]
    mapped = {}
    unmapped = []
    
    for raw_w, count in unassigned_wards.items():
        clean_w = re.sub(r'^(Phường|Xã|Quận|Huyện)\s+', '', raw_w, flags=re.IGNORECASE).strip()
        found_code = None
        
        for code, info in personnel.items():
            primary_names = [w["name"].lower() for w in info["primary_wards"]]
            backup_names = [w["name"].lower() for w in info["backup_wards"]]
            clean_lower = clean_w.lower()
            if clean_lower in primary_names or any(clean_lower in p for p in primary_names):
                found_code = code
                break
            if clean_lower in backup_names or any(clean_lower in b for b in backup_names):
                found_code = code
                break
                
        if not found_code:
            clean_l = clean_w.lower()
            if "tân bình" in clean_l:
                found_code = "8447" # Duy
            elif "sài gòn" in clean_l or "bến nghé" in clean_l:
                found_code = "8448" # Minh
            elif "vườn lài" in clean_l:
                found_code = "8467" # Đạt
            elif "hóc môn" in clean_l:
                found_code = "8462" # Khang
                
        if found_code:
            mapped[found_code] = mapped.get(found_code, 0) + count
        else:
            unmapped.append((raw_w, count))
            
    return mapped, unmapped

def compute_staff_wards(code, total_load, master_data):
    p_info = master_data["personnel"][code]
    primary = p_info["primary_wards"]
    backup = p_info["backup_wards"]
    
    # Tier 4: Quá tải (>= 22 ATC)
    if total_load >= 22:
        return "Tier 4", "Quá tải (Tạm ngưng)", []
        
    # Tier 0: Cực thoáng (<= 5 ATC)
    if total_load <= 5:
        chinh = [w["name"] for w in primary]
        phu = [w["name"] for w in backup if w["name"] not in chinh]
        return "Tier 0", "Cực thoáng (Full chính + Tất cả backup)", chinh + phu
        
    # Tier 1: Rất thoáng (> 5 và < 10 ATC)
    if total_load < 10:
        chinh = [w["name"] for w in primary]
        phu = [w["name"] for w in backup if w["is_bold"] and w["name"] not in chinh]
        return "Tier 1", "Rất thoáng (Full chính + Backup IN ĐẬM)", chinh + phu
        
    # Tier 2: Tải nhẹ (10 <= total_load < 15 ATC)
    if total_load < 15:
        return "Tier 2", "Tải nhẹ (Full chính)", [w["name"] for w in primary]
        
    # Tier 3: Tải trung bình (15 <= total_load < 22 ATC)
    all_bold = all(w["is_bold"] for w in primary)
    if all_bold:
        return "Tier 3", "Tải trung bình (3 phường chính đầu)", [w["name"] for w in primary[:3]]
    else:
        bold_chinh = [w["name"] for w in primary if w["is_bold"]]
        if code == "8462" and "Gò Vấp" in bold_chinh:
            bold_chinh.remove("Gò Vấp")
        return "Tier 3", "Tải trung bình (Chính IN ĐẬM)", bold_chinh

def run_auto_update_hcm_sheet(bot=None, chat_id=None):
    """
    Main entry point: Pulls live CRM data, calculates workload, updates Google Sheet,
    and sends notification.
    """
    try:
        master_file = os.path.join(BASE_DIR, "master_personnel_wards.json")
        sa_file = os.path.join(BASE_DIR, "service_account.json")
        
        with open(master_file, "r", encoding="utf-8") as f:
            master = json.load(f)
            
        # 1. Fetch live CRM data
        hcm_reg, staff_holdings, unassigned_wards = get_hcm_crm_data()
        mapped_pending, unmapped = map_wards_to_staff(unassigned_wards, master)
        
        # 2. Evaluate HCM personnel (in standard order)
        personnel_order = ["8447", "8448", "8440", "8467", "8462", "8231"]
        summary = []
        hcm_rows = []
        stt = 51 # Start STT at 51 (Row 52 on Sheet Miền Nam)
        
        for code in personnel_order:
            info = master["personnel"][code]
            atc = staff_holdings.get(code, 0)
            pending = mapped_pending.get(code, 0)
            total_load = atc + pending
            tier, desc, wards = compute_staff_wards(code, total_load, master)
            
            summary.append({
                "code": code,
                "name": info["name"],
                "atc": atc,
                "pending": pending,
                "total_load": total_load,
                "tier": tier,
                "desc": desc,
                "wards": wards
            })
            
            for w in wards:
                hcm_rows.append([str(stt), "Hồ Chí Minh", w, f"{code} - {info['name']}", "", "", w])
                stt += 1
                
        # 3. Update Google Sheet
        target_sheet_id = master["system_info"]["sheets"]["target_sheet_id"]
        target_worksheet = master["system_info"]["sheets"]["target_worksheet"]
        
        gc = gspread.service_account(filename=sa_file)
        sh = gc.open_by_key(target_sheet_id)
        ws = sh.worksheet(target_worksheet)
        
        start_row = 52
        end_row = start_row + len(hcm_rows) - 1
        
        if len(hcm_rows) > 0:
            if end_row > ws.row_count:
                ws.resize(rows=end_row + 15)
            ws.update(values=hcm_rows, range_name=f"A{start_row}:G{end_row}")
            
        clear_start = max(end_row + 1, start_row)
        if clear_start <= ws.row_count:
            ws.batch_clear([f"A{clear_start}:Z{ws.row_count}"])
            
        # 4. Build response report
        now_time_str = time.strftime("%H:%M %d/%m/%Y")
        report_text = (
            f"🎉 **[TỰ ĐỘNG] CẬP NHẬT GOOGLE SHEET ĐỔ DATA THÀNH CÔNG!**\n"
            f"⏰ **Thời gian**: `{now_time_str}`\n"
            f"📊 **Tổng số phường HCM được điền**: `{len(hcm_rows)}` phường\n"
            f"🔒 **Vũng Tàu (4) & Đồng Nai (9)**: Giữ nguyên cố định ở trên.\n\n"
            f"📋 **Chi tiết tải & phân tầng Tier:**\n"
        )
        
        for r in summary:
            icon = "🟢" if "Tier 1" in r["tier"] or "Tier 0" in r["tier"] else ("🟡" if "Tier 2" in r["tier"] else ("🟠" if "Tier 3" in r["tier"] else "🔴"))
            wards_str = f"`{len(r['wards'])}` phường ({', '.join(r['wards'])})" if r["wards"] else "_Tạm ngưng xả tải_"
            report_text += (
                f"• {icon} **{r['code']} - {r['name']}**: Tải `{r['total_load']}` "
                f"(`{r['atc']}` ATC + `{r['pending']}` tồn) ➔ **{r['tier']}**\n"
                f"   👉 Điền: {wards_str}\n"
            )
            
        if unmapped:
            report_text += f"\n⚠️ **Phường tồn chưa rõ tuyến**: `{unmapped}`\n"
            
        report_text += f"\n👉 [Bấm xem Google Sheet Miền Nam](https://docs.google.com/spreadsheets/d/{target_sheet_id}/edit?gid=50268761#gid=50268761)"
        
        # Send Telegram notification if bot and chat_id are available
        if bot and chat_id:
            try:
                bot.send_message(chat_id, report_text, parse_mode="Markdown")
            except Exception as te:
                print(f"⚠️ [AutoSheet] Lỗi gửi thông báo Telegram: {te}", flush=True)
                
        return True, report_text
        
    except Exception as e:
        err_msg = f"❌ [AutoSheet] Lỗi khi cập nhật Google Sheet tự động: {e}"
        print(err_msg, flush=True)
        if bot and chat_id:
            try:
                bot.send_message(chat_id, err_msg, parse_mode="Markdown")
            except:
                pass
        return False, err_msg

if __name__ == "__main__":
    success, msg = run_auto_update_hcm_sheet()
    print("Result success:", success)
    print(msg)
