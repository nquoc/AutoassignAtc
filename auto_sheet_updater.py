import os
import sys
import json
import re
import time
import gspread

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except:
        pass

# Ensure current dir is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import crm_api

TAN_BINH_BACKUP_WARDS = [
    "Tân Sơn Hòa",
    "Tân Sơn Nhất",
    "Tân Hòa",
    "Bảy Hiền",
    "Tân Bình",
    "Tân Sơn"
]
TAN_BINH_ALLOWED_STAFF = ["8447", "8440", "8448", "8467"]
TAN_BINH_EXCLUDED_STAFF = ["8231", "8462", "8437"]

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
        raise ValueError("Không thể lấy dữ liệu data treo chưa gán từ CRM (Cookie có thể đã hết hạn)")
        
    unassigned_wards = summary.get("wards", {}) # {ward_name: count}
    
    # 2. Fetch staff holdings
    target_staff_ids = hcm_reg.get("staff_ids", [])
    view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"
    rows = crm_api.fetch_crm_export(view_url)
    
    if not rows or len(rows) <= 1:
        raise ValueError("Không thể lấy dữ liệu danh sách người xử lý từ View 20154 (Cookie CRM có thể đã hết hạn hoặc kết nối gián đoạn)")
    
    staff_holdings = {sid: 0 for sid in target_staff_ids}
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
    """
    Map unassigned CRM wards to staff to accurately estimate incoming pending workload.
    Priority:
    1. Primary wards across all staff (Primary ALWAYS beats Backup)
    2. Backup wards across all staff
    3. Fallback keywords
    """
    personnel = master_data["personnel"]
    personnel_order = ["8447", "8448", "8440", "8467", "8462", "8231"]
    all_codes = personnel_order + [c for c in personnel if c not in personnel_order]
    
    mapped = {}
    unmapped = []
    
    for raw_w, count in unassigned_wards.items():
        clean_w = re.sub(r'^(Phường|Xã|Quận|Huyện)\s+', '', raw_w, flags=re.IGNORECASE).strip()
        clean_lower = clean_w.lower()
        found_code = None
        
        # Pass 1: Check PRIMARY wards of all personnel
        for code in all_codes:
            if code not in personnel:
                continue
            primary_names = [w["name"].lower() for w in personnel[code]["primary_wards"]]
            # Exact match or substring match (e.g. "Bình Trị Đông" in "Bình Trị Đông B")
            if clean_lower in primary_names or any(len(p) >= 3 and (p in clean_lower or clean_lower in p) for p in primary_names):
                found_code = code
                break
                
        # Pass 2: Check BACKUP wards (if not matched to any primary ward)
        if not found_code:
            for code in all_codes:
                if code not in personnel:
                    continue
                backup_names = [w["name"].lower() for w in personnel[code]["backup_wards"]]
                if clean_lower in backup_names or any(len(b) >= 3 and (b in clean_lower or clean_lower in b) for b in backup_names):
                    found_code = code
                    break
                    
        # Pass 3: Fallback special keywords
        if not found_code:
            clean_l = clean_w.lower()
            raw_l = raw_w.lower()
            if any(k in clean_l for k in ["tân bình", "bảy hiền", "bay hien", "tân sơn nhất", "tan son nhat", "tân sơn hòa", "tan son hoa", "tân hòa", "tan hoa"]):
                found_code = "8447" # Duy (Cụm Tân Bình cũ)
            elif any(k in clean_l for k in ["hóc môn", "hoc mon", "q12"]) or "quận 12" in raw_l or clean_w == "12":
                found_code = "8462" # Khang (Quận 12 / Hóc Môn)
            elif any(k in clean_l for k in ["sài gòn", "sai gon", "bến nghé", "ben nghe", "quận 4", "quận 7", "nhiêu lộc", "nhieu loc"]):
                found_code = "8448" # Minh (Trung tâm, Nhiêu Lộc, Q4, Q7)
            elif any(k in clean_l for k in ["vườn lài", "vuon lai", "diên hồng", "dien hong", "chợ quán", "cho quan", "an đông", "an dong", "bình tây", "binh tay", "bình tiên", "binh tien", "bình phú", "binh phu", "phú lâm", "phu lam"]):
                found_code = "8467" # Đạt (Q10, Q5, Q6, Q3)
                
        if found_code:
            mapped[found_code] = mapped.get(found_code, 0) + count
        else:
            unmapped.append((raw_w, count))
            
    return mapped, unmapped

def compute_staff_wards(code, total_load, master_data):
    """
    Determine the list of wards to assign to a staff member based on their total load (ATC + pending).
    Tiers:
    - Tier 0 (<= 5 ATC): Full chính + Tất cả backup
    - Tier 1 (6-9 ATC): Full chính + Backup IN ĐẬM
    - Tier 2 (10-14 ATC): Full chính
    - Tier 3 (15-21 ATC): 3 phường chính đầu (nếu 100% in đậm) HOẶC các phường chính IN ĐẬM
    - Tier 4 (>= 22 ATC): Quá tải - Tạm ngưng
    """
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
        
        # Check active Tan Binh assignment
        tb_state_file = os.path.join(BASE_DIR, "tb_sheet_assignment.json")
        active_tb = False
        if os.path.exists(tb_state_file):
            try:
                with open(tb_state_file, "r", encoding="utf-8") as f:
                    tb_data = json.load(f)
                    active_tb = tb_data.get("enabled", False) or bool(tb_data.get("assignee"))
            except:
                active_tb = False
        
        # 2. Evaluate HCM personnel (in standard order)
        personnel_order = ["8447", "8448", "8440", "8467", "8462", "8231"]
        summary = []
        raw_staff_wards = {}
        
        for code in personnel_order:
            info = master["personnel"][code]
            atc = staff_holdings.get(code, 0)
            pending = mapped_pending.get(code, 0)
            total_load = atc + pending
            tier, desc, wards = compute_staff_wards(code, total_load, master)
            
            raw_staff_wards[code] = wards
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
            
        # 3. Deduplicate wards across staff (Primary has priority over Backup, earlier staff has priority)
        used_wards = set()
        # Reserved wards from fixed blocks (Đồng Nai & Vũng Tàu)
        for block_key in ["vung_tau", "dong_nai"]:
            for bw in master.get("special_fixed_blocks", {}).get(block_key, {}).get("wards", []):
                used_wards.add(bw.strip().lower())
                
        hcm_rows = []
        final_assigned_count = {}
        
        for item in summary:
            code = item["code"]
            info = master["personnel"][code]
            assigned_this_staff = []
            
            for w in raw_staff_wards.get(code, []):
                w_norm = w.strip().lower()
                if w_norm not in used_wards:
                    used_wards.add(w_norm)
                    assigned_this_staff.append(w)
                    
            item["final_wards"] = assigned_this_staff
            final_assigned_count[code] = len(assigned_this_staff)
            
        # 4. Open Google Sheet & determine dynamic start row
        target_sheet_id = master["system_info"]["sheets"]["target_sheet_id"]
        target_worksheet = master["system_info"]["sheets"]["target_worksheet"]
        
        gc = gspread.service_account(filename=sa_file)
        sh = gc.open_by_key(target_sheet_id)
        ws = sh.worksheet(target_worksheet)
        
        # Dynamically locate the start row right after Đồng Nai (block 3)
        start_row = 52
        stt = 51
        try:
            col_b_vals = ws.col_values(2) # Column B: city
            dn_indices = [i for i, v in enumerate(col_b_vals) if "đồng nai" in str(v).lower()]
            if dn_indices:
                last_dn_row = max(dn_indices) + 1 # 1-based row index
                start_row = last_dn_row + 1
                col_a_val = ws.cell(last_dn_row, 1).value
                if col_a_val and str(col_a_val).strip().isdigit():
                    stt = int(str(col_a_val).strip()) + 1
        except Exception as det_e:
            print(f"ℹ️ [AutoSheet] Dùng start_row mặc định (52): {det_e}", flush=True)
            start_row = 52
            stt = 51
            
        # Build rows to write
        for item in summary:
            code = item["code"]
            info = master["personnel"][code]
            for w in item["final_wards"]:
                hcm_rows.append([str(stt), "Hồ Chí Minh", w, f"{code} - {info['name']}", "", "", w])
                stt += 1
                
        # If Tan Binh backup is active, append 6 wards with Column D = "backup Tân Bình cũ"
        if active_tb:
            for tb_w in TAN_BINH_BACKUP_WARDS:
                hcm_rows.append([str(stt), "Hồ Chí Minh", tb_w, "backup Tân Bình cũ", "", "", tb_w])
                stt += 1
                
        end_row = start_row + len(hcm_rows) - 1
        
        if len(hcm_rows) > 0:
            if end_row > ws.row_count:
                ws.resize(rows=end_row + 15)
            ws.update(values=hcm_rows, range_name=f"A{start_row}:G{end_row}")
            
        clear_start = max(end_row + 1, start_row)
        if clear_start <= ws.row_count:
            ws.batch_clear([f"A{clear_start}:G{ws.row_count}"])
            
        # 5. Build response report
        now_time_str = time.strftime("%H:%M %d/%m/%Y")
        report_text = (
            f"🎉 **[TỰ ĐỘNG] CẬP NHẬT GOOGLE SHEET ĐỔ DATA THÀNH CÔNG!**\n"
            f"⏰ **Thời gian**: `{now_time_str}`\n"
            f"📊 **Tổng số phường HCM được điền**: `{len(hcm_rows)}` phường (bắt đầu từ dòng `{start_row}`)\n"
            f"🔒 **Vũng Tàu (4) & Đồng Nai (9)**: Giữ nguyên cố định ở trên.\n\n"
            f"📋 **Chi tiết tải & phân tầng Tier:**\n"
        )
        
        for r in summary:
            icon = "🟢" if "Tier 1" in r["tier"] or "Tier 0" in r["tier"] else ("🟡" if "Tier 2" in r["tier"] else ("🟠" if "Tier 3" in r["tier"] else "🔴"))
            final_w = r.get("final_wards", [])
            wards_str = f"`{len(final_w)}` phường ({', '.join(final_w)})" if final_w else "_Tạm ngưng xả tải_"
            report_text += (
                f"• {icon} **{r['code']} - {r['name']}**: Tải `{r['total_load']}` "
                f"(`{r['atc']}` ATC + `{r['pending']}` tồn) ➔ **{r['tier']}**\n"
                f"   👉 Điền: {wards_str}\n"
            )
            
        if active_tb:
            report_text += f"\n🏢 **Cụm Tân Bình cũ**: Đã điền thêm 6 phường backup (Cột D: `backup Tân Bình cũ`).\n"
        else:
            report_text += f"\n🏢 **Cụm Tân Bình cũ**: Chưa điền (Dùng lệnh `/themtb` hoặc `themtb` để thêm vào Sheet).\n"
            
        if unmapped:
            unmapped_str = ", ".join(f"`{w}` ({c})" for w, c in unmapped)
            report_text += f"\n⚠️ **Phường tồn chưa rõ tuyến**: {unmapped_str}\n"
            
        report_text += f"\n👉 [Bấm xem Google Sheet Miền Nam](https://docs.google.com/spreadsheets/d/{target_sheet_id}/edit?gid=50268761#gid=50268761)"
        
        # Send Telegram notification if bot and chat_id are available
        if bot and chat_id:
            try:
                bot.send_message(chat_id, report_text, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                try:
                    bot.send_message(chat_id, report_text, disable_web_page_preview=True)
                except Exception as te:
                    print(f"⚠️ [AutoSheet] Lỗi gửi thông báo Telegram: {te}", flush=True)
                    
        return True, report_text
        
    except Exception as e:
        err_msg = f"❌ [AutoSheet] Lỗi khi cập nhật Google Sheet tự động: {e}"
        print(err_msg, flush=True)
        if bot and chat_id:
            try:
                bot.send_message(chat_id, err_msg, disable_web_page_preview=True)
            except:
                pass
        return False, err_msg

def add_tan_binh_backup_sheet(staff_code=None, bot=None, chat_id=None):
    """
    Enables Tan Binh backup wards (Column D: "backup Tân Bình cũ") and immediately re-updates the Google Sheet.
    """
    tb_state_file = os.path.join(BASE_DIR, "tb_sheet_assignment.json")
    with open(tb_state_file, "w", encoding="utf-8") as f:
        json.dump({
            "enabled": True,
            "label": "backup Tân Bình cũ",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, ensure_ascii=False, indent=2)

    return run_auto_update_hcm_sheet(bot=bot, chat_id=chat_id)

def remove_tan_binh_backup_sheet(bot=None, chat_id=None):
    """
    Clears the Tan Binh backup wards assignment and re-updates the Google Sheet.
    """
    tb_state_file = os.path.join(BASE_DIR, "tb_sheet_assignment.json")
    if os.path.exists(tb_state_file):
        try:
            os.remove(tb_state_file)
        except:
            with open(tb_state_file, "w", encoding="utf-8") as f:
                json.dump({"enabled": False}, f)

    return run_auto_update_hcm_sheet(bot=bot, chat_id=chat_id)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ["add", "themtb", "themtanbinh"]:
            s, m = add_tan_binh_backup_sheet()
            print("Result success:", s)
            print(m)
            sys.exit(0)
        elif cmd in ["del", "remove", "xoatb", "xoatanbinh"]:
            s, m = remove_tan_binh_backup_sheet()
            print("Result success:", s)
            print(m)
            sys.exit(0)

    success, msg = run_auto_update_hcm_sheet()
    print("Result success:", success)
    print(msg)
