import os
import sys
import re
import json
import time
import threading
import telebot
import csv
import datetime
import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from concurrent.futures import ThreadPoolExecutor
from crm_assigner import assign_atc, assign_region_data
from crm_api import get_region_summary, get_session, check_cookie_valid, acquire_session_via_selenium, fetch_crm_export
from reporter import log_assignment, send_google_chat_report

# Ensure standard encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Read configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception as e:
    print(f"Lỗi đọc file config.json: {e}")
    sys.exit(1)

BOT_TOKEN = config.get("bot_token")
if not BOT_TOKEN:
    print("Vui lòng cấu hình bot_token trong config.json")
    sys.exit(1)

# Read regions config
REGIONS_PATH = os.path.join(os.path.dirname(__file__), "regions.json")
try:
    with open(REGIONS_PATH, "r", encoding="utf-8") as f:
        regions_list = json.load(f)
except Exception as e:
    print(f"Lỗi đọc file regions.json: {e}")
    regions_list = []

# Read staff config
STAFF_PATH = os.path.join(os.path.dirname(__file__), "staff.json")
try:
    with open(STAFF_PATH, "r", encoding="utf-8") as f:
        staff_dict = json.load(f)
except Exception as e:
    print(f"Lỗi đọc file staff.json: {e}")
    staff_dict = {"quoc": [], "vietanh": []}

bot = telebot.TeleBot(BOT_TOKEN)
crm_lock = threading.Lock()
TAN_BINH_BACKUP_WARDS = [

    "Tân Sơn Hòa",

    "Tân Sơn Nhất",

    "Tân Hòa",

    "Bảy Hiền",

    "Tân Bình",

    "Tân Sơn"

]

TAN_BINH_ALLOWED_STAFF = ["8447", "8440", "8448", "8467"]
def is_tan_binh_ward(w_name):

    if not w_name:

        return False

    clean = str(w_name).lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").replace("huyện ", "").strip()

    return any(clean == tb.lower() or tb.lower() in clean for tb in TAN_BINH_BACKUP_WARDS)

def get_coachers_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="📊 Quét tất cả (Cả 2 Coacher)", callback_data="scan_all:all"))
    markup.add(
        InlineKeyboardButton(text="👑 Coacher Quốc", callback_data="coacher:quoc"),
        InlineKeyboardButton(text="👑 Coacher Việt Anh", callback_data="coacher:vietanh")
    )
    return markup

def get_regions_markup(coacher_key="all"):
    markup = InlineKeyboardMarkup()
    if coacher_key == "all":
        markup.add(InlineKeyboardButton(text="📊 Quét tất cả khu vực", callback_data="scan_all:all"))
        for r in regions_list:
            markup.add(InlineKeyboardButton(text=f"[{r.get('coacher_name', 'Quốc')}] {r['name']}", callback_data=f"reg:{r['id']}"))
    else:
        filtered = [r for r in regions_list if r.get("coacher") == coacher_key]
        coacher_name = "Quốc" if coacher_key == "quoc" else "Việt Anh"
        markup.add(InlineKeyboardButton(text=f"📊 Quét tất cả của Coacher {coacher_name}", callback_data=f"scan_all:{coacher_key}"))
        markup.add(InlineKeyboardButton(text="🔍 Check ATC Treo", callback_data=f"check_atc:{coacher_key}"))
        for r in filtered:
            markup.add(InlineKeyboardButton(text=r["name"], callback_data=f"reg:{r['id']}"))
        markup.add(InlineKeyboardButton(text="⬅️ Chọn lại Coacher", callback_data="back_coachers"))
    return markup

def get_quantity_markup(region_id):

    markup = InlineKeyboardMarkup(row_width=3)

    quantities = [1, 3, 5, 10, 15, 20]

    buttons = [InlineKeyboardButton(text=str(q), callback_data=f"qty:{region_id}:{q}") for q in quantities]

    markup.add(*buttons)

    

    region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)

    if region and region.get("ward_staff_map"):

        markup.add(InlineKeyboardButton(text="🎯 Gợi ý data theo Nhân sự (Chính + Backup)", callback_data=f"staff_suggest:{region_id}"))

        if region_id.lower() == "hcm":

            markup.add(InlineKeyboardButton(text="🏢 Backup Cụm Tân Bình cũ (Quanh Cty)", callback_data="tb_menu"))

        

    markup.add(InlineKeyboardButton(text="📍 Lựa Phường/Xã để chia data", callback_data=f"px_list:{region_id}"))

    

    c_key = region.get("coacher", "quoc") if region else "quoc"

    markup.add(InlineKeyboardButton(text="⬅️ Quay lại danh sách khu vực", callback_data=f"coacher:{c_key}"))

    return markup
def get_staff_markup(region_id, quantity, show_all=False):
    markup = InlineKeyboardMarkup(row_width=2)
    region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
    c_key = region.get("coacher", "quoc") if region else "quoc"
    
    all_coacher_staff = staff_dict.get(c_key, [])
    allowed_ids = region.get("staff_ids", []) if (region and not show_all) else []
    
    if allowed_ids and not show_all:
        staff_list = [s for s in all_coacher_staff if s["short_id"] in allowed_ids]
        if not staff_list:
            staff_list = all_coacher_staff
    else:
        staff_list = all_coacher_staff
        
    buttons = []
    for s in staff_list:
        label = s["name"]
        if " - " in label:
            parts = label.split(" - ")
            label = f"{parts[0]} - {parts[1]}"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"assign:{region_id}:{quantity}:{s['short_id']}"))
    markup.add(*buttons)
    
    if allowed_ids and not show_all and len(staff_list) < len(all_coacher_staff):
        markup.add(InlineKeyboardButton(text="🌐 Hiện tất cả NS của Coacher", callback_data=f"show_all_staff:{region_id}:{quantity}"))
        
    markup.add(InlineKeyboardButton(text="⬅️ Chọn lại số lượng", callback_data=f"reg:{region_id}"))
    return markup

def get_ward_staff_markup(region_id, ward_name, show_all=False):
    markup = InlineKeyboardMarkup(row_width=2)
    region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
    c_key = region.get("coacher", "quoc") if region else "quoc"
    
    all_coacher_staff = staff_dict.get(c_key, [])
    allowed_ids = region.get("staff_ids", []) if (region and not show_all) else []
    
    if allowed_ids and not show_all:
        staff_list = [s for s in all_coacher_staff if s["short_id"] in allowed_ids]
        if not staff_list:
            staff_list = all_coacher_staff
    else:
        staff_list = all_coacher_staff

    ward_staff_map = region.get("ward_staff_map", {}) if region else {}
    assigned_sid = None
    if ward_staff_map and ward_name:
        w_lower = ward_name.lower()
        for sid, val in ward_staff_map.items():
            kw_list = val.get("primary", []) if isinstance(val, dict) else val
            bak_list = val.get("backup", []) if isinstance(val, dict) else []
            if any(kw.lower() in w_lower for kw in kw_list):
                assigned_sid = sid
                break
            if any(kw.lower() in w_lower for kw in bak_list):
                assigned_sid = sid
                break
        
    buttons = []
    if assigned_sid:
        top_staff = [s for s in staff_list if s["short_id"] == assigned_sid]
        other_staff = [s for s in staff_list if s["short_id"] != assigned_sid]
        sorted_staff = top_staff + other_staff
    else:
        sorted_staff = staff_list

    for s in sorted_staff:
        label = s["name"]
        if " - " in label:
            parts = label.split(" - ")
            label = f"{parts[0]} - {parts[1]}"
        if assigned_sid and s["short_id"] == assigned_sid:
            label = f"⭐ {label} (Phụ trách)"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"px_staff:{region_id}:{ward_name}:{s['short_id']}"))
    markup.add(*buttons)
    
    if allowed_ids and not show_all and len(staff_list) < len(all_coacher_staff):
        markup.add(InlineKeyboardButton(text="🌐 Hiện tất cả NS của Coacher", callback_data=f"show_all_px_staff:{region_id}:{ward_name}"))
        
    markup.add(InlineKeyboardButton(text="⬅️ Chọn lại Phường/Xã", callback_data=f"px_list:{region_id}"))
    return markup

def get_multi_ward_staff_markup(region_id, selected_wards=None, show_all=False):
    markup = InlineKeyboardMarkup(row_width=2)
    region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
    c_key = region.get("coacher", "quoc") if region else "quoc"
    
    all_coacher_staff = staff_dict.get(c_key, [])
    allowed_ids = region.get("staff_ids", []) if (region and not show_all) else []
    
    if allowed_ids and not show_all:
        staff_list = [s for s in all_coacher_staff if s["short_id"] in allowed_ids]
        if not staff_list:
            staff_list = all_coacher_staff
    else:
        staff_list = all_coacher_staff

    ward_staff_map = region.get("ward_staff_map", {}) if region else {}
    matched_sids = set()
    if ward_staff_map and selected_wards:
        for w_name in selected_wards:
            w_lower = str(w_name).lower()
            for sid, val in ward_staff_map.items():
                kw_list = val.get("primary", []) if isinstance(val, dict) else val
                bak_list = val.get("backup", []) if isinstance(val, dict) else []
                if any(kw.lower() in w_lower for kw in kw_list) or any(kw.lower() in w_lower for kw in bak_list):
                    matched_sids.add(sid)
                    
    buttons = []
    if matched_sids:
        top_staff = [s for s in staff_list if s["short_id"] in matched_sids]
        other_staff = [s for s in staff_list if s["short_id"] not in matched_sids]
        sorted_staff = top_staff + other_staff
    else:
        sorted_staff = staff_list

    for s in sorted_staff:
        label = s["name"]
        if " - " in label:
            parts = label.split(" - ")
            label = f"{parts[0]} - {parts[1]}"
        if s["short_id"] in matched_sids:
            label = f"⭐ {label} (Phụ trách)"
        buttons.append(InlineKeyboardButton(text=label, callback_data=f"px_m_stf:{region_id}:{s['short_id']}"))
    markup.add(*buttons)
    
    if allowed_ids and not show_all and len(staff_list) < len(all_coacher_staff):
        markup.add(InlineKeyboardButton(text="🌐 Hiện tất cả NS của Coacher", callback_data=f"show_all_px_m_stf:{region_id}"))
        
    markup.add(InlineKeyboardButton(text="⬅️ Chọn lại Phường/Xã", callback_data=f"px_list:{region_id}"))
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 **Bot Tự Động Phân Công & Bàn Giao ATC / Ticket KiotViet**\n\n"
        "👉 **1. Bàn giao Ticket / ATC / Tên gian hàng:**\n"
        "• `[Tên Gian Hàng / Mã Ticket / Retailer ID] [Mã nhân sự]`\n"
        "  _Ví dụ_: `TT8802410 8460` hoặc `nhanongcafe 8460` hoặc `500988791 8460`\n"
        "  _Ví dụ_: `chuyen TT8802410 8460` hoặc `nhanongcafe chuyển 8460`\n"
        "*(Tự động kiểm tra Rule: Chỉ chuyển khi đơn đang ở Pool chung / chưa ai nhận, khóa an toàn đơn đã làm/đã có nhân sự nhận)*\n\n"
        "👉 **2. Phân công data tỉnh / khu vực:**\n"
        "• Xem danh sách: `ds`\n"
        "• Xem Phường/Xã: `px [ID viết tắt]`\n"
        "• Chia 1 hoặc nhiều Phường/Xã: `[ID viết tắt] [STT_hoặc_Tên] [Số lượng/all] [Mã nhân sự]`\n"
        "  _Ví dụ_: `cto 1,2 all 8460` hoặc `cto 1,2,3 5 8460` hoặc `chia cto 1,2 cho 8460`\n"
        "• Chia tỉnh: `[ID viết tắt] [Số lượng] [Mã nhân sự]` (Ví dụ: `danang 2 8421`)\n\n"
        "👉 **3. Tự động chia data (< 10 ATC treo):**\n"
        "• Tự động quét 2 lần/ngày: **08:30 sáng** & **20:30 tối** (đẩy thêm 8 data)\n"
        "• Kiểm tra mô phỏng trước: `/checkauto` hoặc `check chia`\n"
        "• Chạy chia ngay lập tức: `/autoassign` hoặc `chiatudong`\n\n"
        "👉 **4. Báo cáo & Giám sát:**\n"
        "• Báo cáo Coacher Quốc: `/checkquoc`\n"
        "• Cảnh báo trễ SLA: `/sla`\n"
        "• Báo cáo Google Chat: `/report`\n"
        "• Cập nhật Google Sheet Miền Nam (21h tự động): `/updatesheet` hoặc `/sheet`"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['chuyen', 'transfer', 'bangiao'])
def handle_chuyen_command(message):
    parts = message.text.strip().split()
    if len(parts) >= 3:
        query_str = parts[1]
        staff_code = parts[2]
        threading.Thread(target=process_transfer_thread, args=(message.chat.id, query_str, staff_code), daemon=True).start()
    else:
        bot.reply_to(
            message,
            "💡 **Cú pháp chuyển Ticket / ATC / Tên gian hàng:**\n"
            "`/chuyen [Tên gian hàng / Mã Ticket / Mã ATC / Retailer ID] [Mã nhân sự]`\n\n"
            "Ví dụ:\n"
            "• `/chuyen TT8802410 8460`\n"
            "• `/chuyen nhanongcafe 8460`\n"
            "• `/chuyen 500988791 8460`",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['admincoacher'])
def send_admin_menu(message):
    welcome_text = (
        "👑 **MENU QUẢN LÝ DÀNH CHO COACHER**\n\n"
        "Vui lòng **Chọn Coacher** bên dưới để quản lý danh sách khu vực và check ATC treo:\n"
    )
    markup = get_coachers_markup()
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['login'])
def force_login_command(message):
    chat_id = message.chat.id
    status_msg = bot.send_message(chat_id, "⏳ **Đang kiểm tra và làm mới Session CRM...**", parse_mode="Markdown")
    def update_log(msg):
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=msg, parse_mode="Markdown")
        except:
            pass
    def login_thread():
        from crm_api import acquire_session_via_selenium
        c_str, csrf = acquire_session_via_selenium("16309", update_status=update_log, allow_gui_fallback=True)
        if c_str and csrf:
            bot.send_message(chat_id, "🎉 **ĐÃ CẬP NHẬT SESSION CRM THÀNH CÔNG!**\nSession mới đã được lưu và sẵn sàng chia data.", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ **Đăng nhập CRM thất bại.** Vui lòng kiểm tra lại tài khoản hoặc thao tác đăng nhập Google trực tiếp trên trình duyệt.", parse_mode="Markdown")
    threading.Thread(target=login_thread, daemon=True).start()

def process_transfer_thread(chat_id, query_str, staff_code):
    status_msg = bot.send_message(
        chat_id, 
        f"⏳ **Đang kiểm tra & bàn giao:** `{query_str}` ➔ `{staff_code}`...",
        parse_mode="Markdown"
    )
    
    crm_lock.acquire(blocking=True)
    try:
        from quick_action import do_transfer, STAFF_MAP
        res_t = do_transfer(query_str, staff_code)
        rec_id = res_t[0]
        ticket_no = res_t[1]
        retailer_id = res_t[2]
        atcs = res_t[3]
        latest_atc = res_t[4] if len(res_t) > 4 else None
        description = res_t[5] if len(res_t) > 5 else ""
        store_name = res_t[6] if len(res_t) > 6 else ""
        
        staff_info = STAFF_MAP.get(str(staff_code), (staff_code, staff_code))[1]
        ret_str = f"`{retailer_id}`" if retailer_id else "_Chưa xác định_"
        store_str = f"`{store_name}`" if store_name else "_Chưa xác định_"
        
        if atcs:
            atc_part = f"• **ATC liên quan**: `{', '.join(atcs)}` (Đã chuyển sang {staff_code})"
        else:
            atc_part = "• **ATC liên quan**: Không có ATC liên quan ở SC GROUP"
            if latest_atc:
                atc_part += f"\n• **ATC gần nhất**: `{latest_atc['no']}` (Trạng thái: `{latest_atc['status']}`, Người xử lý: `{latest_atc['assigned_user']}`)"
            else:
                atc_part += "\n• **ATC gần nhất**: _Không tìm thấy ATC nào trên hệ thống_"
        
        desc_part = ""
        if description and description.strip():
            d_clean = description.strip()
            if len(d_clean) > 800:
                d_clean = d_clean[:800] + "..."
            desc_part = f"\n• **Mô tả (Description)**:\n```\n{d_clean}\n```"

        success_text = (
            f"✅ **BÀN GIAO THÀNH CÔNG** #Ticket\n\n"
            f"• **Mã Ticket/Gốc**: `{ticket_no}` (ID: `{rec_id}`)\n"
            f"• **Tên gian hàng (Tên GH)**: {store_str}\n"
            f"• **Retailer ID**: {ret_str}\n"
            f"• **Nhân sự nhận**: `{staff_code} - {staff_info}`\n"
            f"{atc_part}"
            f"{desc_part}\n\n"
            f"⚡ **Thời gian hoàn thành**: {time.strftime('%H:%M:%S %d/%m/%Y')}\n"
            f"#Ticket"
        )
        bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_msg.message_id, 
            text=success_text, 
            parse_mode="Markdown"
        )
        # Bắn thông báo lên Google Chat & tag đích danh nhân sự nhận
        try:
            from quick_action import send_transfer_gchat
            threading.Thread(
                target=send_transfer_gchat,
                args=(rec_id, ticket_no, store_name, retailer_id, staff_code, staff_info, atcs, latest_atc, description),
                daemon=True
            ).start()
        except Exception as ge:
            print(f"⚠️ [Transfer] Lỗi gọi send_transfer_gchat: {ge}", flush=True)
    except Exception as e:
        err_msg = str(e)
        bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_msg.message_id, 
            text=f"❌ **KHÔNG THỂ BÀN GIAO**\n\n• **Đối tượng**: `{query_str}`\n• **Lý do**: {err_msg}", 
            parse_mode="Markdown"
        )
    finally:
        crm_lock.release()

process_assignment_thread = process_transfer_thread

def process_region_scan_callback(chat_id, message_id, region):
    try:
        def log_status(msg):
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg)
            except:
                pass

        target_staff_ids = region.get("staff_ids", [])

        def fetch_summary():
            return get_region_summary(region['url'], update_status=log_status)

        def fetch_holdings():
            if not target_staff_ids:
                return {}
            try:
                view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"
                rows = fetch_crm_export(view_url)
                if not rows or len(rows) < 1:
                    return {}
                headers = rows[0]
                o_idx = headers.index('Người xử lý') if 'Người xử lý' in headers else 13
                counts = {sid: 0 for sid in target_staff_ids}
                for r in rows[1:]:
                    if len(r) > o_idx:
                        owner = r[o_idx].strip()
                        for sid in target_staff_ids:
                            if sid in owner:
                                counts[sid] += 1
                                break
                return counts
            except Exception:
                return {}

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_summary = executor.submit(fetch_summary)
            fut_holdings = executor.submit(fetch_holdings)
            summary = fut_summary.result()
            staff_holdings = fut_holdings.result()

        if not summary:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ **Không thể lấy dữ liệu CRM cho khu vực:** {region['name']}. Vui lòng thử lại sau.",
                reply_markup=get_regions_markup(),
                parse_mode="Markdown"
            )
            return
            
        total = summary["total_unassigned"]
        wards = summary["wards"]
        
        ward_details = ""
        if wards:
            ward_details = "\n".join(f"- **{ward}**: {count} data" for ward, count in wards.items())
        else:
            ward_details = "_Không có data chưa xử lý_"

        c_key = region.get("coacher", "quoc")
        staff_list = staff_dict.get(c_key, [])

        staff_holding_section = ""
        if staff_holdings:
            staff_lines = []
            sorted_sids = sorted(staff_holdings.keys(), key=lambda sid: staff_holdings[sid], reverse=True)
            for sid in sorted_sids:
                s_obj = next((s for s in staff_list if s["short_id"] == sid), None)
                raw_name = s_obj["name"] if s_obj else sid
                short_name = raw_name.split(" - ")[1] if " - " in raw_name else raw_name
                h_cnt = staff_holdings[sid]
                icon = "🔴" if h_cnt >= 25 else ("🟡" if h_cnt >= 10 else "🟢")
                staff_lines.append(f"• {icon} **{sid} - {short_name}**: `{h_cnt}` ATC đang giữ")
            
            total_staff_h = sum(staff_holdings.values())
            staff_holding_section = (
                f"👤 **Số lượng ATC treo nhân sự {region['name']} đang giữ (Tổng: `{total_staff_h}` ATC):**\n"
                + "\n".join(staff_lines) + "\n\n"
            )
            
        if total > 0:
            reply_text = (
                f"📍 **Khu vực**: {region['name']}\n"
                f"📊 **Tổng số data treo chưa chia**: `{total}` data\n\n"
                f"{staff_holding_section}"
                f"📋 **Chi tiết theo Phường/Xã còn tồn:**\n"
                f"{ward_details}\n\n"
                f"👉 **Bước 1: Chọn số lượng data muốn chia:**"
            )
            markup = get_quantity_markup(region['id'])
        else:
            reply_text = (
                f"📍 **Khu vực**: {region['name']}\n"
                f"📊 **Tổng số data chưa xử lý**: `0` data\n\n"
                f"{staff_holding_section}"
                f"🔴 **Khu vực này hiện tại đã HẾT data chưa xử lý!**"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(text="⬅️ Quay lại danh sách", callback_data="back_regions"))
            
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=reply_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ **Đã xảy ra lỗi khi quét dữ liệu:** {e}",
            reply_markup=get_regions_markup(),
            parse_mode="Markdown"
        )

ward_cache = {}  # {region_id: [ward1, ward2, ...]}
ward_counts_cache = {}  # {region_id: {ward1: count1, ...}}
ward_selection_session = {}  # {(chat_id, region_id): set([ward1, ...])}

def build_ward_list_markup(chat_id, region, sorted_wards):
    r_id = region['id'].lower()
    selected_set = ward_selection_session.setdefault((chat_id, r_id), set())
    
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, (w_name, count) in enumerate(sorted_wards[:16], 1):
        is_sel = w_name in selected_set
        icon = "✅" if is_sel else "⬜"
        display_w = w_name
        if len(display_w) > 16:
            display_w = display_w.replace("Phường ", "P.").replace("Xã ", "X.").replace("Thị trấn ", "TT.")
        btn_text = f"{icon} {idx}. {display_w} ({count})"
        buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"px_tog:{r_id}:{idx}"))
    markup.add(*buttons)
    
    markup.add(
        InlineKeyboardButton(text="⚡ Chọn tất cả", callback_data=f"px_all:{r_id}"),
        InlineKeyboardButton(text="🔄 Bỏ chọn hết", callback_data=f"px_none:{r_id}")
    )
    
    num_sel = len(selected_set)
    if num_sel > 0:
        total_data = sum(ward_counts_cache.get(r_id, {}).get(w, 0) for w in selected_set)
        action_text = f"➡️ Bàn giao {num_sel} Phường đã chọn ({total_data} data)"
        markup.add(InlineKeyboardButton(text=action_text, callback_data=f"px_proceed:{r_id}"))
    else:
        markup.add(InlineKeyboardButton(text="👆 Bấm các ô trên để chọn Phường", callback_data=f"px_hint:{r_id}"))
        
    markup.add(InlineKeyboardButton(text="⬅️ Quay lại khu vực", callback_data=f"reg:{region['id']}"))
    return markup

def process_ward_list_callback(chat_id, message_id, region):
    r_id = region['id'].lower()
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⏳ **Đang quét danh sách Phường/Xã khu vực:** {region['name']}...",
            parse_mode="Markdown"
        )
    except Exception:
        pass
        
    rows = fetch_crm_export(region['url'])
    if not rows or len(rows) < 2:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ **Khu vực {region['name']} hiện tại chưa có data nào hoặc không thể tải dữ liệu.**",
            parse_mode="Markdown"
        )
        return
        
    headers = rows[0]
    w_idx = headers.index('Xã/Phường/Thị trấn') if 'Xã/Phường/Thị trấn' in headers else 4
    o_idx = headers.index('Người xử lý') if 'Người xử lý' in headers else 11
    
    allowed_kw = ["sc group", "chăm sóc khách hàng hỗ trợ trực tiếp", "hỗ trợ trực tiếp", "chăm sóc khách hàng", "direct support", "cskh"]
    ward_counts = {}
    
    for row in rows[1:]:
        if len(row) <= max(w_idx, o_idx): continue
        ward_val = row[w_idx].strip()
        owner_val = row[o_idx].strip()
        
        if not any(kw in owner_val.lower() for kw in allowed_kw):
            continue
            
        if not ward_val:
            ward_val = "Chưa cập nhật Phường/Xã"
            
        ward_counts[ward_val] = ward_counts.get(ward_val, 0) + 1

    if not ward_counts:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🟢 **Khu vực {region['name']} hiện tại đã HẾT data chưa xử lý!**",
            parse_mode="Markdown"
        )
        return

    sorted_wards = sorted(ward_counts.items(), key=lambda x: x[1], reverse=True)
    total_unassigned = sum(ward_counts.values())
    
    ward_cache[r_id] = [w for w, c in sorted_wards]
    ward_counts_cache[r_id] = dict(sorted_wards)
    ward_selection_session[(chat_id, r_id)] = set()
    
    lines = [
        f"📍 **DANH SÁCH PHƯỜNG / XÃ KHU VỰC: {region['name'].upper()}**",
        f"🔥 *Tổng data chưa chia*: `{total_unassigned}` data tại {len(sorted_wards)} Phường/Xã\n"
    ]
    
    for idx, (w_name, count) in enumerate(sorted_wards, 1):
        lines.append(f"• `{idx}`. **{w_name}**: `{count}` data")
        
    lines.append(f"\n👉 **Cú pháp chia siêu tốc bằng tin nhắn:**")
    lines.append(f"`{r_id} [STT_hoặc_Tên_Phường] [SốLượng/all] [MãNV]`")
    lines.append(f"*Ví dụ*: `{r_id} 1,2 all 8460` (Chia hết P1, P2)")
    lines.append(f"       `{r_id} 1,2,3 5 8460` (Chia 5 data từ P1, P2, P3)")
    lines.append(f"       `{r_id} 1-3 all 8460` | `{r_id} An Khánh, Hưng Lợi 8460`\n")
    lines.append("Hoặc **bấm nút chọn nhiều Phường/Xã bên dưới** để chia cùng lúc:")
    
    markup = build_ward_list_markup(chat_id, region, sorted_wards)
    
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text="\n".join(lines),
        reply_markup=markup,
        parse_mode="Markdown"
    )

def process_region_assignment_callback(chat_id, message_id, region, quantity, staff_id, ward_name=None, source_mode=None):

    backup_wards = []

    if not ward_name:

        w_map = region.get("ward_staff_map", {})

        if str(staff_id) in w_map:

            val = w_map[str(staff_id)]

            if isinstance(val, dict):

                ward_name = val.get("primary", [])

                backup_wards = val.get("backup", [])

                if not ward_name and backup_wards:

                    ward_name = backup_wards

                    backup_wards = []

            else:

                ward_name = val

            

    steps = []

    if isinstance(ward_name, (list, tuple, set)):

        ward_list = [str(w) for w in ward_name]

        if len(ward_list) == 1:

            ward_str = f" ({ward_list[0]})"

        else:

            ward_str = f" ({len(ward_list)} Phường/Xã: {', '.join(ward_list[:3])}{'...' if len(ward_list) > 3 else ''})"

    elif ward_name:

        ward_str = f" ({ward_name})"

    else:

        ward_str = ""

    

    qty_display = "Tất cả" if str(quantity).lower() in ("all", "tatca", "tất cả") else str(quantity)

    

    def status_callback(msg):

        steps.append(msg)

        display_text = (

            f"⏳ **Đang phân công khu vực:** {region['name']}{ward_str}\n"

            f"- Số lượng yêu cầu: `{qty_display}`\n"

            f"- Mã nhân sự: `{staff_id}`\n\n"

            f"**Tiến trình chi tiết:**\n" + "\n".join(f"  {s}" for s in steps[-8:])

        )

        try:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text=display_text,

                parse_mode="Markdown"

            )

        except Exception as e:

            pass
    status_callback("⏳ Hệ thống đang bận xử lý, chờ đến lượt...")

    

    crm_lock.acquire(blocking=True)

    try:

        steps.clear()

        success, message = assign_region_data(region['url'], quantity, staff_id, ward_filter=ward_name, update_status=status_callback)

        if not success and backup_wards and ("Không tìm thấy data" in message or "không tìm thấy record" in message.lower()):

            status_callback(f"ℹ️ Phường chính không có data treo, tự động chuyển sang Phường Backup ({', '.join(backup_wards[:3])})...")

            ward_name = backup_wards

            if len(backup_wards) == 1:

                ward_str = f" (Backup: {backup_wards[0]})"

            else:

                ward_str = f" (Backup: {len(backup_wards)} Phường: {', '.join(backup_wards[:2])}...)"

            success, message = assign_region_data(region['url'], quantity, staff_id, ward_filter=backup_wards, update_status=status_callback)

            if success:

                message = f"[Lấy từ kho Backup] {message}"

        

        c_key = region.get("coacher", "quoc") if region else "quoc"

        res_markup = InlineKeyboardMarkup()

        if source_mode == "tanbinh":

            res_markup.add(

                InlineKeyboardButton(text="🏢 Tiếp tục Menu Tân Bình cũ", callback_data="tb_menu"),

                InlineKeyboardButton(text="🎯 Menu Gợi ý HCM", callback_data="staff_suggest:hcm")

            )

        elif region and (region.get("ward_staff_map") or region['id'].lower() in ("hcm", "dongnai")):

            res_markup.add(

                InlineKeyboardButton(text="🎯 Gợi ý data theo Nhân sự (Hồ Chí Minh)", callback_data="staff_suggest:hcm")

            )

            res_markup.add(

                InlineKeyboardButton(text="🏢 Backup Cụm Tân Bình cũ (Quanh Cty)", callback_data="tb_menu")

            )

        if region:

            res_markup.add(

                InlineKeyboardButton(text=f"📍 Tiếp tục chia Phường/Xã khác ({region['name']})", callback_data=f"px_list:{region['id']}"),

                InlineKeyboardButton(text="⬅️ Quay lại danh sách khu vực", callback_data=f"coacher:{c_key}")

            )

        

        if success:

            staff_list = staff_dict.get(c_key, [])

            staff_obj = next((s for s in staff_list if s["short_id"] == staff_id), None)

            

            staff_display_name = staff_id

            if staff_obj:

                staff_display_name = staff_obj["name"]

                if " - " in staff_display_name:

                    parts = staff_display_name.split(" - ")

                    staff_display_name = f"{parts[0]} - {parts[1]}"

                

            log_assignment(f"{region['name']}{ward_str}", c_key, staff_id, staff_display_name, quantity)

            

            final_text = (

                f"✅ **PHÂN CÔNG KHU VỰC THÀNH CÔNG**\n\n"

                f"• **Khu vực**: `{region['name']}`{ward_str}\n"

                f"• **Nhân sự nhận**: `{staff_display_name}` ({staff_id})\n"

                f"• **Chi tiết**: {message}\n\n"

                f"⚡ **Thời gian hoàn thành**: {time.strftime('%H:%M:%S %d/%m/%Y')}"

            )

            # Clear ward selection session and cache on success

            r_id = region['id'].lower()

            ward_selection_session.pop((chat_id, r_id), None)

            ward_counts_cache.pop(r_id, None)

            ward_cache.pop(r_id, None)

            if r_id in ("hcm", "dongnai"):

                ward_counts_cache.pop("hcm", None)

                ward_counts_cache.pop("dongnai", None)

        else:

            final_text = (

                f"❌ **PHÂN CÔNG KHU VỰC THẤT BẠI**\n\n"

                f"• **Khu vực**: `{region['name']}`{ward_str}\n"

                f"• **Nhân sự**: `{staff_id}`\n"

                f"• **Lý do**: {message}"

            )

            

        # Thu gọn tin nhắn tiến trình trước đó

        try:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text=f"⚡ **Tiến trình hoàn tất:** {region['name']}{ward_str} ➔ `{staff_id}` ({time.strftime('%H:%M:%S')})",

                parse_mode="Markdown"

            )

        except Exception:

            pass
        bot.send_message(chat_id, final_text, reply_markup=res_markup, parse_mode="Markdown")
        # Khi ở HCM (hoặc khu vực có gợi ý nhân sự, hoặc sau khi chia Tân Bình), tự động hiện lại menu phù hợp

        is_hcm_or_dn = (region and region['id'].lower() in ("hcm", "dongnai")) or source_mode == "tanbinh"

        if success and is_hcm_or_dn:

            def show_suggest_menu_after():

                time.sleep(1)

                try:

                    if source_mode == "tanbinh":

                        loading_msg = bot.send_message(

                            chat_id,

                            "🏢 **Đang tổng hợp dữ liệu cụm Tân Bình cũ (quanh cty)...**",

                            parse_mode="Markdown"

                        )

                        process_tanbinh_menu(chat_id, loading_msg.message_id)

                    else:

                        hcm_reg = next((r for r in regions_list if r['id'].lower() == 'hcm'), None)

                        target_reg = hcm_reg if hcm_reg else region

                        loading_msg = bot.send_message(

                            chat_id,

                            f"🎯 **Đang tổng hợp dữ liệu gợi ý mới nhất ({target_reg['name']})...**",

                            parse_mode="Markdown"

                        )

                        process_staff_suggest_menu(chat_id, loading_msg.message_id, target_reg)

                except Exception as ex:

                    print(f"⚠️ [Suggest Menu] Lỗi hiển thị gợi ý sau phân công: {ex}", flush=True)
            threading.Thread(target=show_suggest_menu_after, daemon=True).start()

    except Exception as e:

        bot.send_message(chat_id, f"❌ **Lỗi hệ thống**: {e}", parse_mode="Markdown")

    finally:

        crm_lock.release()
def match_ward_to_staff(w_name, w_map):
    clean = w_name.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()
    # 1. Exact match primary
    for sid, info in w_map.items():
        pri_list = info.get("primary", []) if isinstance(info, dict) else info
        if any(clean == kw.lower() for kw in pri_list):
            return sid, "primary"
    # 2. Exact match backup
    for sid, info in w_map.items():
        bak_list = info.get("backup", []) if isinstance(info, dict) else []
        if any(clean == kw.lower() for kw in bak_list):
            return sid, "backup"
    # 3. Substring match by longest keyword
    candidates = []
    for sid, info in w_map.items():
        pri_list = info.get("primary", []) if isinstance(info, dict) else info
        bak_list = info.get("backup", []) if isinstance(info, dict) else []
        for kw in pri_list:
            if kw.lower() in clean:
                candidates.append((len(kw), sid, "primary"))
        for kw in bak_list:
            if kw.lower() in clean:
                candidates.append((len(kw), sid, "backup"))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1], candidates[0][2]
    return None, None

def process_staff_suggest_menu(chat_id, message_id, region):

    r_id = region['id'].lower()

    w_map = region.get("ward_staff_map", {})

    if not w_map:

        try:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text=f"❌ Khu vực {region['name']} chưa cấu hình mapping nhân sự!",

                reply_markup=get_quantity_markup(region['id'])

            )

        except Exception:

            pass

        return

        

    target_staff_ids = list(w_map.keys())
    def fetch_summary():

        return get_region_summary(region['url'])
    def fetch_dn_summary():

        if r_id == "hcm":

            dn_reg = next((r for r in regions_list if r['id'].lower() == 'dongnai'), None)

            if dn_reg and dn_reg.get('url'):

                return get_region_summary(dn_reg['url'])

        return None
    def fetch_holdings():

        try:

            view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"

            rows = fetch_crm_export(view_url)

            if not rows or len(rows) < 1:

                return {}

            headers = rows[0]

            o_idx = headers.index('Người xử lý') if 'Người xử lý' in headers else 13

            counts = {sid: 0 for sid in target_staff_ids}

            for r in rows[1:]:

                if len(r) > o_idx:

                    owner = r[o_idx].strip()

                    for sid in target_staff_ids:

                        if sid in owner:

                            counts[sid] += 1

                            break

            return counts

        except Exception:

            return {}
    with ThreadPoolExecutor(max_workers=3) as executor:

        fut_summary = executor.submit(fetch_summary)

        fut_dn = executor.submit(fetch_dn_summary)

        fut_holdings = executor.submit(fetch_holdings)

        summary = fut_summary.result()

        dn_summary = fut_dn.result()

        staff_holdings = fut_holdings.result()
    if summary and summary.get("wards"):

        cached_wards = summary["wards"]

        ward_counts_cache[r_id] = cached_wards

        ward_cache[r_id] = list(cached_wards.keys())

    else:

        cached_wards = ward_counts_cache.get(r_id, {})
    dn_wards = dn_summary.get("wards", {}) if dn_summary else {}

    if dn_wards:

        ward_counts_cache["dongnai"] = dn_wards

            

    total_unassigned = sum(cached_wards.values()) if cached_wards else 0

    c_key = region.get("coacher", "quoc")

    staff_list = staff_dict.get(c_key, [])

    

    staff_pri_counts = {sid: 0 for sid in w_map}

    staff_bak_counts = {sid: 0 for sid in w_map}

    for sid, info in w_map.items():

        pri_list = info.get("primary", []) if isinstance(info, dict) else info

        bak_list = info.get("backup", []) if isinstance(info, dict) else []
        # 1. Primary matching

        if sid == "8437" and r_id == "hcm":

            # 8437 uses Dong Nai for primary

            for w, count in dn_wards.items():

                w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").replace("huyện ", "").strip()

                if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in pri_list):

                    staff_pri_counts[sid] += count

        else:

            for w, count in cached_wards.items():

                if is_tan_binh_ward(w):

                    continue  # EXCLUDE Tan Binh wards from regular suggestion!

                w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()

                if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in pri_list):

                    staff_pri_counts[sid] += count
        # 2. Backup matching (all in HCM, excluding Tan Binh)

        for w, count in cached_wards.items():

            if is_tan_binh_ward(w):

                continue  # EXCLUDE Tan Binh wards from regular suggestion!

            w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()

            if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in bak_list):

                staff_bak_counts[sid] += count

    

    markup = InlineKeyboardMarkup(row_width=1)

    overview_lines = [

        f"🎯 **GỢI Ý DATA THEO NHÂN SỰ: {region['name'].upper()}**",

        f"📊 *Tổng data treo toàn khu vực*: `{total_unassigned}` data\n",

        "👉 **Bấm chọn nhân sự bên dưới để xem chi tiết và chia data:**",

        "_(Hệ thống ưu tiên Phường chính, nếu hết tự động lấy Phường Backup)_\n"

    ]

    

    for sid, w_info in w_map.items():

        staff_obj = next((s for s in staff_list if s["short_id"] == sid), None)

        raw_name = staff_obj["name"] if staff_obj else sid

        short_name = raw_name.split(" - ")[1] if " - " in raw_name else raw_name

        

        pri_count = staff_pri_counts.get(sid, 0)

        bak_count = staff_bak_counts.get(sid, 0)

        h_cnt = staff_holdings.get(sid, 0)

        

        pri_wards = w_info.get("primary", []) if isinstance(w_info, dict) else w_info

        bak_wards = w_info.get("backup", []) if isinstance(w_info, dict) else []
        if pri_count > 0:

            if sid == "8437" and r_id == "hcm":

                tag = f"🔥 {pri_count} chính (Đ.Nai)"

            else:

                tag = f"🔥 {pri_count} chính"

            status_icon = "🟢"

        elif bak_count > 0:

            tag = f"🔄 {bak_count} backup"

            status_icon = "🟡"

        elif not pri_wards and not bak_wards:

            tag = "📦 Kho chung"

            status_icon = "🔵"

        else:

            tag = "0 data"

            status_icon = "⚪"

            

        btn_text = f"{status_icon} {sid} - {short_name} ({tag} | giữ: {h_cnt})"

        markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"suggest_pick:{region['id']}:{sid}"))

        overview_lines.append(f"• `{sid}` - **{short_name}**: `{tag}` *(Hiện giữ: `{h_cnt}` ATC)*")

        

    if r_id == "hcm":

        markup.add(InlineKeyboardButton(text="🏢 Backup Cụm Tân Bình cũ (Quanh Cty)", callback_data="tb_menu"))
    markup.add(

        InlineKeyboardButton(text="🔄 Cập nhật số liệu mới nhất", callback_data=f"staff_suggest:{region['id']}"),

        InlineKeyboardButton(text="⬅️ Quay lại khu vực", callback_data=f"reg:{region['id']}")

    )

    

    try:

        if message_id:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text="\n".join(overview_lines),

                reply_markup=markup,

                parse_mode="Markdown"

            )

        else:

            bot.send_message(

                chat_id=chat_id,

                text="\n".join(overview_lines),

                reply_markup=markup,

                parse_mode="Markdown"

            )

    except Exception as e:

        if "message is not modified" not in str(e).lower():

            try:

                bot.send_message(

                    chat_id=chat_id,

                    text="\n".join(overview_lines),

                    reply_markup=markup,

                    parse_mode="Markdown"

                )

            except Exception:

                pass
def process_staff_suggest_detail(chat_id, message_id, region, staff_id):

    r_id = region['id'].lower()

    w_map = region.get("ward_staff_map", {})

    w_info = w_map.get(str(staff_id), {})

    

    c_key = region.get("coacher", "quoc")

    staff_list = staff_dict.get(c_key, [])

    staff_obj = next((s for s in staff_list if s["short_id"] == str(staff_id)), None)

    raw_name = staff_obj["name"] if staff_obj else str(staff_id)

    short_name = raw_name.split(" - ")[1] if " - " in raw_name else raw_name

    

    pri_wards = w_info.get("primary", []) if isinstance(w_info, dict) else w_info

    bak_wards = w_info.get("backup", []) if isinstance(w_info, dict) else []

    pri_bold_list = w_info.get("primary_bold", []) if isinstance(w_info, dict) else []

    bak_bold_list = w_info.get("backup_bold", []) if isinstance(w_info, dict) else []

    

    cached_wards = ward_counts_cache.get(r_id, {})

    if not cached_wards:

        summary = get_region_summary(region['url'])

        if summary and summary.get("wards"):

            cached_wards = summary["wards"]

            ward_counts_cache[r_id] = cached_wards

            ward_cache[r_id] = list(cached_wards.keys())
    # For 8437, primary is Dong Nai!

    dn_wards = {}

    if str(staff_id) == "8437" and r_id == "hcm":

        dn_wards = ward_counts_cache.get("dongnai", {})

        if not dn_wards:

            dn_reg = next((r for r in regions_list if r['id'].lower() == 'dongnai'), None)

            if dn_reg and dn_reg.get('url'):

                dn_summary = get_region_summary(dn_reg['url'])

                if dn_summary and dn_summary.get("wards"):

                    dn_wards = dn_summary["wards"]

                    ward_counts_cache["dongnai"] = dn_wards

            

    pri_matched = {}

    bak_matched = {}
    if str(staff_id) == "8437" and r_id == "hcm":

        # 1. Primary from Dong Nai

        for w, count in dn_wards.items():

            w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").replace("huyện ", "").strip()

            if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in pri_wards):

                pri_matched[w] = count

        target_pri_region = "Dongnai"

        target_pri_label = "Kho Đồng Nai"

    else:

        for w, count in cached_wards.items():

            if is_tan_binh_ward(w):

                continue

            w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()

            if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in pri_wards):

                pri_matched[w] = count

        target_pri_region = region['id']

        target_pri_label = "Phường chính"
    # Backup always from HCM (excluding Tan Binh)

    for w, count in cached_wards.items():

        if is_tan_binh_ward(w):

            continue

        w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()

        if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in bak_wards):

            bak_matched[w] = count

    target_bak_region = "Hcm" if r_id == "hcm" else region['id']

    target_bak_label = "Kho Backup" if str(staff_id) != "8437" else "Kho Backup (Thủ Đức, Q9)"

                

    pri_total = sum(pri_matched.values())

    bak_total = sum(bak_matched.values())

    

    markup = InlineKeyboardMarkup(row_width=1)

    loc_desc = "Đồng Nai (Địa bàn chính)" if (str(staff_id) == "8437" and r_id == "hcm") else region['name']

    lines = [

        f"🎯 **GỢI Ý DATA CHO NHÂN SỰ:** `{raw_name}`",

        f"📍 **Khu vực:** `{loc_desc}`\n"

    ]

    

    if pri_total > 0:

        lines.append(f"🔥 **1. PHƯỜNG CHÍNH{' (ĐỒNG NAI)' if str(staff_id) == '8437' else ''}: TÌM THẤY `{pri_total}` ATC TREO**")

        for w, c in sorted(pri_matched.items(), key=lambda x: x[1], reverse=True):

            w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").replace("huyện ", "").strip()

            is_bold = any(w_clean == kw.lower() or kw.lower() in w_clean for kw in pri_bold_list)

            star = "⭐ " if is_bold else ""

            badge = " *(Ưu tiên)*" if is_bold else ""

            lines.append(f"  • {star}**{w}**: `{c}` ATC{badge}")
        bak_desc = f" ({', '.join(bak_wards)})" if bak_wards else ""

        lines.append(f"\n📦 **2. PHƯỜNG BACKUP:** `{bak_total}` ATC{bak_desc}\n")

        lines.append(f"👉 **Bấm nút bên dưới để chia ngay data {target_pri_label}:**")

        

        markup.add(InlineKeyboardButton(

            text=f"⚡ Chia TẤT CẢ {pri_total} ATC ({target_pri_label}) cho {short_name}",

            callback_data=f"assign_suggest:{target_pri_region}:{staff_id}:primary:all"

        ))

        if pri_total > 10:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 10 ATC ({target_pri_label}) cho {short_name}",

                callback_data=f"assign_suggest:{target_pri_region}:{staff_id}:primary:10"

            ))

        if pri_total > 5:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 5 ATC ({target_pri_label}) cho {short_name}",

                callback_data=f"assign_suggest:{target_pri_region}:{staff_id}:primary:5"

            ))

        if pri_total > 3:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 3 ATC ({target_pri_label}) cho {short_name}",

                callback_data=f"assign_suggest:{target_pri_region}:{staff_id}:primary:3"

            ))

            

    elif bak_total > 0:

        lines.append(f"⚪ **1. PHƯỜNG CHÍNH:** `0` ATC treo _(Đã hết data: {', '.join(pri_wards)})_\n")

        lines.append(f"🔄 **2. TỰ ĐỘNG CHUYỂN SANG PHƯỜNG BACKUP: TÌM THẤY `{bak_total}` ATC TREO**")

        for w, c in sorted(bak_matched.items(), key=lambda x: x[1], reverse=True):

            w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").replace("huyện ", "").strip()

            is_bold = any(w_clean == kw.lower() or kw.lower() in w_clean for kw in bak_bold_list)

            star = "⭐ " if is_bold else ""

            badge = " *(Ưu tiên)*" if is_bold else ""

            lines.append(f"  • {star}**{w}**: `{c}` ATC{badge}")

        lines.append(f"\n👉 **Bấm nút bên dưới để chia data từ {target_bak_label}:**")

        

        markup.add(InlineKeyboardButton(

            text=f"⚡ Chia TẤT CẢ {bak_total} ATC ({target_bak_label}) cho {short_name}",

            callback_data=f"assign_suggest:{target_bak_region}:{staff_id}:backup:all"

        ))

        if bak_total > 10:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 10 ATC ({target_bak_label}) cho {short_name}",

                callback_data=f"assign_suggest:{target_bak_region}:{staff_id}:backup:10"

            ))

        if bak_total > 5:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 5 ATC ({target_bak_label}) cho {short_name}",

                callback_data=f"assign_suggest:{target_bak_region}:{staff_id}:backup:5"

            ))

        if bak_total > 3:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 3 ATC ({target_bak_label}) cho {short_name}",

                callback_data=f"assign_suggest:{target_bak_region}:{staff_id}:backup:3"

            ))

            

    elif not pri_wards and not bak_wards:

        total_pool = sum(cached_wards.values()) if cached_wards else 0

        lines.append(f"📦 **KHO CHUNG KHU VỰC: TÌM THẤY `{total_pool}` ATC TREO**")

        lines.append(f"ℹ️ *Nhân sự `{short_name}` nhận data từ kho chung {region['name']}.*")

        lines.append("\n👉 **Bấm nút bên dưới để chia data từ kho chung:**")
        markup.add(InlineKeyboardButton(

            text=f"⚡ Chia TẤT CẢ {total_pool} ATC (Kho chung) cho {short_name}",

            callback_data=f"assign_suggest:{region['id']}:{staff_id}:primary:all"

        ))

        if total_pool > 10:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 10 ATC (Kho chung) cho {short_name}",

                callback_data=f"assign_suggest:{region['id']}:{staff_id}:primary:10"

            ))

        if total_pool >= 8:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 8 ATC (Kho chung) cho {short_name}",

                callback_data=f"assign_suggest:{region['id']}:{staff_id}:primary:8"

            ))

        if total_pool > 5:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 5 ATC (Kho chung) cho {short_name}",

                callback_data=f"assign_suggest:{region['id']}:{staff_id}:primary:5"

            ))

        if total_pool > 3:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 3 ATC (Kho chung) cho {short_name}",

                callback_data=f"assign_suggest:{region['id']}:{staff_id}:primary:3"

            ))

    else:

        lines.append(f"⚪ **1. PHƯỜNG CHÍNH:** `0` ATC treo _({', '.join(pri_wards)})_")

        lines.append(f"⚪ **2. PHƯỜNG BACKUP:** `0` ATC treo _({', '.join(bak_wards)})_\n")

        lines.append("🔴 **Hiện tại cả Phường chính và Phường Backup của nhân sự này đều chưa có data treo mới!**")

        

        markup.add(InlineKeyboardButton(

            text="🔄 Quét lại live CRM",

            callback_data=f"suggest_pick:{region['id']}:{staff_id}"

        ))

        

    markup.add(

        InlineKeyboardButton(text="⬅️ Chọn nhân sự khác", callback_data=f"staff_suggest:{region['id']}"),

        InlineKeyboardButton(text="⬅️ Quay lại khu vực", callback_data=f"reg:{region['id']}")

    )

    

    try:

        bot.edit_message_text(

            chat_id=chat_id,

            message_id=message_id,

            text="\n".join(lines),

            reply_markup=markup,

            parse_mode="Markdown"

        )

    except Exception as e:

        if "message is not modified" not in str(e).lower():

            try:

                bot.send_message(

                    chat_id=chat_id,

                    text="\n".join(lines),

                    reply_markup=markup,

                    parse_mode="Markdown"

                )

            except Exception:

                pass
def process_tanbinh_menu(chat_id, message_id=None):

    hcm_reg = next((r for r in regions_list if r['id'].lower() == 'hcm'), None)

    if not hcm_reg:

        return

        

    def fetch_summary():

        return get_region_summary(hcm_reg['url'])
    def fetch_holdings():

        try:

            view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"

            rows = fetch_crm_export(view_url)

            if not rows or len(rows) < 1:

                return {}

            headers = rows[0]

            o_idx = headers.index('Người xử lý') if 'Người xử lý' in headers else 13

            counts = {sid: 0 for sid in TAN_BINH_ALLOWED_STAFF}

            for r in rows[1:]:

                if len(r) > o_idx:

                    owner = r[o_idx].strip()

                    for sid in TAN_BINH_ALLOWED_STAFF:

                        if sid in owner:

                            counts[sid] += 1

                            break

            return counts

        except Exception:

            return {}
    with ThreadPoolExecutor(max_workers=2) as executor:

        fut_summary = executor.submit(fetch_summary)

        fut_holdings = executor.submit(fetch_holdings)

        summary = fut_summary.result()

        staff_holdings = fut_holdings.result()
    cached_wards = summary.get("wards", {}) if summary else {}

    

    tb_matched = {}

    for w, count in cached_wards.items():

        w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()

        if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in TAN_BINH_BACKUP_WARDS):

            tb_matched[w] = count
    total_tb = sum(tb_matched.values())
    c_key = "quoc"

    staff_list = staff_dict.get(c_key, [])
    overview_lines = [

        "🏢 **MENU BACKUP: CỤM TÂN BÌNH CŨ (QUANH CÔNG TY)**",

        "📍 **Khu vực**: Hồ Chí Minh (Cụm văn phòng)",

        f"📊 **Tổng data treo cụm Tân Bình**: `{total_tb}` ATC\n",

        "**Chi tiết 6 phường Tân Bình cũ:**"

    ]

    

    for tb_w in TAN_BINH_BACKUP_WARDS:

        cnt = 0

        for w, c in tb_matched.items():

            if tb_w.lower() in w.lower():

                cnt += c

        status = f"`{cnt}` ATC" if cnt > 0 else "`0`"

        overview_lines.append(f"  • {tb_w}: {status}")
    overview_lines.append("\n👉 **Bấm chọn nhân sự bên dưới để chia data:**")

    overview_lines.append("_(Chỉ áp dụng các bạn quanh cty: Duy, Tùng, Minh, Đạt - trừ Hiếu, Khang, Phát)_")
    markup = InlineKeyboardMarkup(row_width=1)

    for sid in TAN_BINH_ALLOWED_STAFF:

        staff_obj = next((s for s in staff_list if s["short_id"] == sid), None)

        raw_name = staff_obj["name"] if staff_obj else sid

        short_name = raw_name.split(" - ")[1] if " - " in raw_name else raw_name

        h_cnt = staff_holdings.get(sid, 0)

        

        btn_text = f"👤 {sid} - {short_name} (Hiện giữ: {h_cnt} ATC)"

        markup.add(InlineKeyboardButton(text=btn_text, callback_data=f"tb_pick:{sid}"))

        

    markup.add(

        InlineKeyboardButton(text="🔄 Cập nhật số liệu", callback_data="tb_menu"),

        InlineKeyboardButton(text="🎯 Menu Gợi ý HCM", callback_data="staff_suggest:hcm"),

        InlineKeyboardButton(text="⬅️ Quay lại khu vực", callback_data="reg:hcm")

    )
    try:

        if message_id:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text="\n".join(overview_lines),

                reply_markup=markup,

                parse_mode="Markdown"

            )

        else:

            bot.send_message(

                chat_id=chat_id,

                text="\n".join(overview_lines),

                reply_markup=markup,

                parse_mode="Markdown"

            )

    except Exception as e:

        if "message is not modified" not in str(e).lower():

            try:

                bot.send_message(

                    chat_id=chat_id,

                    text="\n".join(overview_lines),

                    reply_markup=markup,

                    parse_mode="Markdown"

                )

            except Exception:

                pass
def process_tanbinh_detail(chat_id, message_id, staff_id):

    hcm_reg = next((r for r in regions_list if r['id'].lower() == 'hcm'), None)

    if not hcm_reg:

        return
    c_key = "quoc"

    staff_list = staff_dict.get(c_key, [])

    staff_obj = next((s for s in staff_list if s["short_id"] == str(staff_id)), None)

    raw_name = staff_obj["name"] if staff_obj else str(staff_id)

    short_name = raw_name.split(" - ")[1] if " - " in raw_name else raw_name
    summary = get_region_summary(hcm_reg['url'])

    cached_wards = summary.get("wards", {}) if summary else {}
    tb_matched = {}

    for w, count in cached_wards.items():

        w_clean = w.lower().replace("phường ", "").replace("xã ", "").replace("thị trấn ", "").strip()

        if any(w_clean == kw.lower() or kw.lower() in w_clean for kw in TAN_BINH_BACKUP_WARDS):

            tb_matched[w] = count
    total_tb = sum(tb_matched.values())
    lines = [

        f"🏢 **CHIA DATA CỤM TÂN BÌNH CŨ CHO:** `{raw_name}`",

        f"📍 **Khu vực**: Hồ Chí Minh (Cụm văn phòng)",

        f"📊 **Tổng data treo cụm Tân Bình**: `{total_tb}` ATC\n"

    ]
    markup = InlineKeyboardMarkup(row_width=1)

    if total_tb > 0:

        lines.append("🔥 **CÁC PHƯỜNG ĐANG CÓ DATA TREO:**")

        for w, c in sorted(tb_matched.items(), key=lambda x: x[1], reverse=True):

            lines.append(f"  • **{w}**: `{c}` ATC")

        lines.append(f"\n👉 **Bấm nút bên dưới để chia data cụm Tân Bình cho {short_name}:**")
        markup.add(InlineKeyboardButton(

            text=f"⚡ Chia TẤT CẢ {total_tb} ATC cho {short_name}",

            callback_data=f"tb_assign:{staff_id}:all"

        ))

        if total_tb > 10:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 10 ATC cho {short_name}",

                callback_data=f"tb_assign:{staff_id}:10"

            ))

        if total_tb > 5:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 5 ATC cho {short_name}",

                callback_data=f"tb_assign:{staff_id}:5"

            ))

        if total_tb > 3:

            markup.add(InlineKeyboardButton(

                text=f"⚡ Chia 3 ATC cho {short_name}",

                callback_data=f"tb_assign:{staff_id}:3"

            ))

    else:

        lines.append("⚪ **Hiện tại cụm Tân Bình cũ chưa có data treo mới!**")

        markup.add(InlineKeyboardButton(

            text="🔄 Quét lại live CRM",

            callback_data=f"tb_pick:{staff_id}"

        ))
    markup.add(

        InlineKeyboardButton(text="⬅️ Chọn nhân sự khác", callback_data="tb_menu"),

        InlineKeyboardButton(text="🎯 Menu Gợi ý HCM", callback_data="staff_suggest:hcm"),

        InlineKeyboardButton(text="⬅️ Quay lại khu vực", callback_data="reg:hcm")

    )
    try:

        bot.edit_message_text(

            chat_id=chat_id,

            message_id=message_id,

            text="\n".join(lines),

            reply_markup=markup,

            parse_mode="Markdown"

        )

    except Exception as e:

        if "message is not modified" not in str(e).lower():

            try:

                bot.send_message(

                    chat_id=chat_id,

                    text="\n".join(lines),

                    reply_markup=markup,

                    parse_mode="Markdown"

                )

            except Exception:

                pass
def process_check_atc_callback(chat_id, message_id, coacher_key):
    if coacher_key != "quoc":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ Không có bộ lọc để check data cho Coacher này.",
            reply_markup=get_regions_markup(coacher_key)
        )
        return
        
    def log_status(msg):
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg)
        except:
            pass
            
    log_status("⏳ **Đang kiểm tra số lượng ATC treo cho từng nhân sự (Coacher Quốc)...**")
    
    staff_list = staff_dict.get(coacher_key, [])
    import urllib.parse
    
    results = []
    for st in staff_list:
        staff_name_full = st["name"]
        encoded_name = urllib.parse.quote(staff_name_full)
        url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154&orderby=&sortorder=&search_params=%5B%5B%5B%22assigned_user_id%22%2C%22c%22%2C%22{encoded_name}%22%5D%5D%5D"
        
        summary = get_region_summary(url, update_status=None)
        count = summary.get("total_unassigned", 0) if summary else 0
        results.append((staff_name_full, count))
        
    # Determine top 3 highest
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    top_3_names = [x[0] for x in sorted_results[:3]]

    report = "🔍 **BÁO CÁO ATC TREO CỦA NHÂN SỰ (COACHER QUỐC)**\n\n"
    for name, count in results:
        parts = name.split(" - ")
        short_name = f"{parts[0]} - {parts[1]}" if len(parts) >= 2 else name
        
        icon = "⚪"
        if count < 5:
            icon = "🔴"
        elif name in top_3_names:
            icon = "🟢"
            
        report += f"{icon} **{short_name}**: `{count}` ATC\n"
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="⬅️ Quay lại danh sách khu vực", callback_data=f"coacher:{coacher_key}"))
    
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=report,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except:
        pass

def process_scan_all_callback(chat_id, message_id, coacher_filter="all"):
    def scan_one(region):
        try:
            summary = get_region_summary(region["url"])
            return region["id"], region["name"], summary["total_unassigned"] if summary else 0, region.get("coacher_name", "")
        except Exception as e:
            print(f"Error scanning {region['name']}: {e}")
            return region["id"], region["name"], 0, region.get("coacher_name", "")
            
    try:
        target_regions = regions_list
        if coacher_filter != "all":
            target_regions = [r for r in regions_list if r.get("coacher") == coacher_filter]
            
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(scan_one, target_regions))
            
        report_lines = []
        for r_id, r_name, total, c_name in results:
            prefix = f"[{c_name}] " if coacher_filter == "all" and c_name else ""
            if total > 0:
                report_lines.append(f"• 🟢 **{prefix}{r_name}** (`{r_id}`): `{total}` data")
            else:
                report_lines.append(f"• 🔴 **{prefix}{r_name}** (`{r_id}`): `0` data")
                
        c_title = "CẢ 2 COACHER" if coacher_filter == "all" else ("COACHER QUỐC" if coacher_filter == "quoc" else "COACHER VIỆT ANH")
        reply_text = (
            f"📊 **BÁO CÁO TỔNG HỢP KHU VỰC ({c_title})**\n\n"
            + "\n".join(report_lines) + "\n\n"
            "👉 **Nhấn nút tương ứng bên dưới để xem chi tiết Phường/Xã và phân công:**"
        )
        
        markup = get_regions_markup(coacher_filter)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=reply_text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"❌ **Đã xảy ra lỗi khi quét tổng hợp:** {e}",
            reply_markup=get_regions_markup(coacher_filter),
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if data == "back_coachers":
        markup = get_coachers_markup()
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="👑 **Chọn Coacher để quản lý danh sách khu vực:**",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
        
    if data.startswith("coacher:"):
        c_key = data.split(":")[1]
        c_name = "Quốc" if c_key == "quoc" else ("Việt Anh" if c_key == "vietanh" else "tất cả")
        markup = get_regions_markup(c_key)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📍 **Danh sách các khu vực thuộc Coacher {c_name}:**\nChọn một khu vực bên dưới để bắt đầu:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
        
    if data.startswith("check_atc"):
        c_key = data.split(":")[1]
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="⏳ **Đang chuẩn bị kiểm tra ATC treo...**",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        threading.Thread(
            target=process_check_atc_callback,
            args=(chat_id, message_id, c_key),
            daemon=True
        ).start()
        return

    if data == "checkquoc_refresh":
        threading.Thread(
            target=process_checkquoc_command,
            args=(chat_id, message_id),
            daemon=True
        ).start()
        return

    if data == "sla_refresh":
        threading.Thread(
            target=process_sla_command,
            args=(chat_id, message_id),
            daemon=True
        ).start()
        return
        
    if data.startswith("scan_all"):
        c_key = data.split(":")[1] if ":" in data else "all"
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="⏳ **Đang quét dữ liệu tổng hợp các khu vực, vui lòng chờ...**",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        threading.Thread(
            target=process_scan_all_callback,
            args=(chat_id, message_id, c_key),
            daemon=True
        ).start()
        return
        
    if data.startswith("staff_suggest:"):
        region_id = data.split(":")[1]
        region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
        if region:
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"⏳ **Đang tổng hợp dữ liệu gợi ý theo nhân sự ({region['name']})...**",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            threading.Thread(
                target=process_staff_suggest_menu,
                args=(chat_id, message_id, region),
                daemon=True
            ).start()
        return

    if data.startswith("suggest_pick:"):
        parts = data.split(":")
        region_id = parts[1]
        staff_id = parts[2]
        region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
        if region:
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"⏳ **Đang kiểm tra data CRM cho nhân sự {staff_id}...**",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            threading.Thread(
                target=process_staff_suggest_detail,
                args=(chat_id, message_id, region, staff_id),
                daemon=True
            ).start()
        return

    if data.startswith("assign_suggest:"):

        parts = data.split(":")

        region_id = parts[1]

        staff_id = parts[2]

        ward_type = parts[3]

        qty_str = parts[4]

        qty_val = "all" if qty_str.lower() in ("all", "tatca", "tất cả") else int(qty_str)

        

        region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)

        if region:

            hcm_reg = next((r for r in regions_list if r['id'].lower() == 'hcm'), None)

            w_map = region.get("ward_staff_map") or (hcm_reg.get("ward_staff_map", {}) if hcm_reg else {})

            w_info = w_map.get(str(staff_id), {})

            if ward_type == "backup":

                target_wards = w_info.get("backup", []) if isinstance(w_info, dict) else []

                desc_type = "Phường Backup"

            else:

                target_wards = w_info.get("primary", []) if isinstance(w_info, dict) else w_info

                desc_type = "Phường chính"

                

            qty_display = "Tất cả" if qty_val == "all" else f"{qty_val} data"

            try:

                bot.edit_message_text(

                    chat_id=chat_id,

                    message_id=message_id,

                    text=f"⏳ **Bắt đầu phân công theo gợi ý:** {region['name']}\n- Kho: `{desc_type}`\n- Số lượng: `{qty_display}`\n- Nhân sự: `{staff_id}`\n- Đang chuẩn bị...",

                    parse_mode="Markdown"

                )

            except Exception:

                pass

                

            threading.Thread(

                target=process_region_assignment_callback,

                args=(chat_id, message_id, region, qty_val, staff_id, target_wards),

                daemon=True

            ).start()

        return
    if data.startswith("add_tb_sheet"):
        try: bot.answer_callback_query(call.id, "Đang điền Tân Bình vào Sheet...")
        except: pass
        _execute_add_tb_sheet(chat_id, message_id=message_id)
        return
    elif data.startswith("del_tb_sheet:"):
        try: bot.answer_callback_query(call.id, "Đang xoá Tân Bình khỏi sheet...")
        except: pass
        _execute_del_tb_sheet(chat_id, message_id=message_id)
        return
    elif data == "close_tb_sheet":
        try: bot.delete_message(chat_id, message_id)
        except: pass
        return

    if data == "tb_menu":

        try:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text="⏳ **Đang quét dữ liệu cụm Tân Bình cũ (quanh công ty)...**",

                parse_mode="Markdown"

            )

        except Exception:

            pass

        threading.Thread(target=process_tanbinh_menu, args=(chat_id, message_id), daemon=True).start()

        return
    if data.startswith("tb_pick:"):

        staff_id = data.split(":")[1]

        try:

            bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text=f"⏳ **Đang tải chi tiết cụm Tân Bình cũ cho nhân sự {staff_id}...**",

                parse_mode="Markdown"

            )

        except Exception:

            pass

        threading.Thread(target=process_tanbinh_detail, args=(chat_id, message_id, staff_id), daemon=True).start()

        return
    if data.startswith("tb_assign:"):

        parts = data.split(":")

        staff_id = parts[1]

        qty_str = parts[2]

        qty_val = "all" if qty_str.lower() in ("all", "tatca", "tất cả") else int(qty_str)
        hcm_reg = next((r for r in regions_list if r['id'].lower() == 'hcm'), None)

        if hcm_reg:

            qty_display = "Tất cả" if qty_val == "all" else f"{qty_val} data"

            try:

                bot.edit_message_text(

                    chat_id=chat_id,

                    message_id=message_id,

                    text=f"⏳ **Bắt đầu phân công cụm Tân Bình cũ:**\n- Số lượng: `{qty_display}`\n- Nhân sự: `{staff_id}`\n- Đang chuẩn bị...",

                    parse_mode="Markdown"

                )

            except Exception:

                pass
            threading.Thread(

                target=process_region_assignment_callback,

                args=(chat_id, message_id, hcm_reg, qty_val, staff_id, TAN_BINH_BACKUP_WARDS, "tanbinh"),

                daemon=True

            ).start()

        return
    if data.startswith("reg:"):
        region_id = data.split(":")[1]
        region = next((r for r in regions_list if r['id'] == region_id), None)
        if not region:
            bot.answer_callback_query(call.id, "Khu vực không tồn tại!")
            return
            
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"⏳ **Đang quét dữ liệu CRM khu vực:** {region['name']}...",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        
        threading.Thread(
            target=process_region_scan_callback,
            args=(chat_id, message_id, region),
            daemon=True
        ).start()

    elif data.startswith("px_list:"):
        r_id = data.split(":")[1]
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        if region:
            threading.Thread(
                target=process_ward_list_callback,
                args=(chat_id, message_id, region),
                daemon=True
            ).start()

    elif data.startswith("px_sel:"):
        parts = data.split(":", 2)
        r_id = parts[1]
        w_name = parts[2]
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        
        markup = get_ward_staff_markup(r_id, w_name)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📍 **Khu vực**: {region['name'] if region else r_id}\n🏙️ **Phường/Xã**: `{w_name}`\n\n👉 **Bước 1: Chọn nhân sự muốn bàn giao:**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("show_all_px_staff:"):
        parts = data.split(":", 2)
        r_id = parts[1]
        w_name = parts[2]
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        
        markup = get_ward_staff_markup(r_id, w_name, show_all=True)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📍 **Khu vực**: {region['name'] if region else r_id}\n🏙️ **Phường/Xã**: `{w_name}`\n\n👉 **Bước 1: Chọn nhân sự (Hiển thị tất cả):**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("px_staff:"):
        parts = data.split(":", 3)
        r_id = parts[1]
        w_name = parts[2]
        staff_id = parts[3]
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        
        markup = InlineKeyboardMarkup(row_width=3)
        quantities = [1, 2, 3, 5, 10, 15, 20]
        buttons = [InlineKeyboardButton(text=f"{q} data", callback_data=f"px_ask:{r_id}:{w_name}:{staff_id}:{q}") for q in quantities]
        markup.add(*buttons)
        markup.add(InlineKeyboardButton(text="⬅️ Chọn lại Nhân sự", callback_data=f"px_sel:{r_id}:{w_name}"))
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📍 **Khu vực**: {region['name'] if region else r_id}\n🏙️ **Phường/Xã**: `{w_name}`\n👤 **Nhân sự nhận**: `{staff_id}`\n\n👉 **Bước 2: Chọn số lượng data muốn bàn giao:**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("px_ask:"):
        parts = data.split(":", 4)
        r_id = parts[1]
        w_name = parts[2]
        staff_id = parts[3]
        qty = int(parts[4])
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        
        c_key = region.get("coacher", "quoc") if region else "quoc"
        staff_list = staff_dict.get(c_key, [])
        staff = next((s for s in staff_list if s['short_id'] == staff_id), None)
        staff_name = staff['name'] if staff else staff_id

        text = (
            "⚠️ **XÁC NHẬN PHÂN CÔNG THEO PHƯỜNG / XÃ**\n\n"
            f"📍 Khu vực: **{region['name'] if region else r_id}**\n"
            f"🏙️ Phường/Xã: **{w_name}**\n"
            f"🔢 Số lượng: **{qty}** data\n"
            f"👤 Bàn giao cho: **{staff_name}**\n\n"
            "Bạn có chắc chắn muốn thực hiện phân công này không?"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(text="✅ Đồng ý & Bắt đầu", callback_data=f"px_confirm:{r_id}:{w_name}:{staff_id}:{qty}"),
            InlineKeyboardButton(text="❌ Hủy & Chọn lại", callback_data=f"px_staff:{r_id}:{w_name}:{staff_id}")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("px_confirm:"):
        parts = data.split(":", 4)
        r_id = parts[1]
        w_name = parts[2]
        staff_id = parts[3]
        quantity = int(parts[4])
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        
        bot.answer_callback_query(call.id, "Đang khởi chạy...")
        
        threading.Thread(
            target=process_region_assignment_callback,
            args=(chat_id, message_id, region, quantity, staff_id, w_name),
            daemon=True
        ).start()

    elif data.startswith("px_tog:"):
        parts = data.split(":")
        r_id = parts[1].lower()
        idx = int(parts[2])
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        if not region:
            bot.answer_callback_query(call.id, "❌ Không tìm thấy khu vực.")
            return
            
        cached_wards = ward_cache.get(r_id, [])
        if not (1 <= idx <= len(cached_wards)):
            bot.answer_callback_query(call.id, "❌ Danh sách Phường/Xã đã cũ, vui lòng quét lại.")
            return
            
        w_name = cached_wards[idx - 1]
        selected_set = ward_selection_session.setdefault((chat_id, r_id), set())
        if w_name in selected_set:
            selected_set.remove(w_name)
            is_now_sel = False
        else:
            selected_set.add(w_name)
            is_now_sel = True
            
        sorted_wards = [(w, ward_counts_cache.get(r_id, {}).get(w, 0)) for w in cached_wards]
        markup = build_ward_list_markup(chat_id, region, sorted_wards)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id, f"{'✅ Đã chọn' if is_now_sel else '⬜ Đã bỏ'} {w_name}")

    elif data.startswith("px_all:"):
        r_id = data.split(":")[1].lower()
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        if region:
            cached_wards = ward_cache.get(r_id, [])
            selected_set = ward_selection_session.setdefault((chat_id, r_id), set())
            selected_set.update(cached_wards)
            sorted_wards = [(w, ward_counts_cache.get(r_id, {}).get(w, 0)) for w in cached_wards]
            markup = build_ward_list_markup(chat_id, region, sorted_wards)
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ Đã chọn tất cả Phường/Xã!")

    elif data.startswith("px_none:"):
        r_id = data.split(":")[1].lower()
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        if region:
            cached_wards = ward_cache.get(r_id, [])
            selected_set = ward_selection_session.setdefault((chat_id, r_id), set())
            selected_set.clear()
            sorted_wards = [(w, ward_counts_cache.get(r_id, {}).get(w, 0)) for w in cached_wards]
            markup = build_ward_list_markup(chat_id, region, sorted_wards)
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)
            except Exception:
                pass
            bot.answer_callback_query(call.id, "🔄 Đã bỏ chọn tất cả.")

    elif data.startswith("px_hint:"):
        bot.answer_callback_query(call.id, "💡 Vui lòng bấm vào ô Phường/Xã ở trên để chọn trước khi tiếp tục!", show_alert=True)

    elif data.startswith("px_proceed:"):
        r_id = data.split(":")[1].lower()
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        if not region:
            bot.answer_callback_query(call.id, "❌ Không tìm thấy khu vực.")
            return
            
        selected_set = ward_selection_session.get((chat_id, r_id), set())
        if not selected_set:
            bot.answer_callback_query(call.id, "💡 Vui lòng bấm chọn ít nhất 1 Phường/Xã ở trên!", show_alert=True)
            return
            
        total_data = sum(ward_counts_cache.get(r_id, {}).get(w, 0) for w in selected_set)
        ward_items_text = "\n".join(f"• **{w}** (`{ward_counts_cache.get(r_id, {}).get(w, 0)}` data)" for w in sorted(selected_set))
        
        markup = get_multi_ward_staff_markup(r_id, selected_wards=selected_set, show_all=False)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"📍 **Khu vực**: {region['name']}\n"
                f"🏙️ **Đã chọn {len(selected_set)} Phường/Xã:**\n{ward_items_text}\n"
                f"🔥 *Tổng cộng*: `{total_data}` data chưa xử lý\n\n"
                f"👉 **Bước 1: Chọn nhân sự muốn bàn giao:**"
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("show_all_px_m_stf:"):
        r_id = data.split(":")[1].lower()
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        selected_set = ward_selection_session.get((chat_id, r_id), set())
        total_data = sum(ward_counts_cache.get(r_id, {}).get(w, 0) for w in selected_set)
        ward_items_text = "\n".join(f"• **{w}** (`{ward_counts_cache.get(r_id, {}).get(w, 0)}` data)" for w in sorted(selected_set))
        
        markup = get_multi_ward_staff_markup(r_id, selected_wards=selected_set, show_all=True)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"📍 **Khu vực**: {region['name'] if region else r_id}\n"
                f"🏙️ **Đã chọn {len(selected_set)} Phường/Xã:**\n{ward_items_text}\n"
                f"🔥 *Tổng cộng*: `{total_data}` data chưa xử lý\n\n"
                f"👉 **Bước 1: Chọn nhân sự (Hiển thị tất cả):**"
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("px_m_stf:"):
        parts = data.split(":")
        r_id = parts[1].lower()
        staff_id = parts[2]
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        selected_set = ward_selection_session.get((chat_id, r_id), set())
        total_data = sum(ward_counts_cache.get(r_id, {}).get(w, 0) for w in selected_set)
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(InlineKeyboardButton(text=f"⚡ Tất cả ({total_data} data)", callback_data=f"px_m_ask:{r_id}:{staff_id}:all"))
        
        qty_options = [q for q in [1, 2, 3, 5, 10, 15, 20] if q < total_data]
        if qty_options:
            buttons = [InlineKeyboardButton(text=f"{q} data", callback_data=f"px_m_ask:{r_id}:{staff_id}:{q}") for q in qty_options]
            markup.add(*buttons)
            
        markup.add(InlineKeyboardButton(text="⬅️ Chọn lại Nhân sự", callback_data=f"px_proceed:{r_id}"))
        
        wards_summary = ", ".join(sorted(selected_set))
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                f"📍 **Khu vực**: {region['name'] if region else r_id}\n"
                f"🏙️ **Phường/Xã ({len(selected_set)})**: `{wards_summary}`\n"
                f"👤 **Nhân sự nhận**: `{staff_id}`\n"
                f"🔥 **Tổng data có thể chia**: `{total_data}` data\n\n"
                f"👉 **Bước 2: Chọn số lượng data muốn bàn giao:**"
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("px_m_ask:"):
        parts = data.split(":")
        r_id = parts[1].lower()
        staff_id = parts[2]
        qty_str = parts[3]
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        selected_set = ward_selection_session.get((chat_id, r_id), set())
        total_data = sum(ward_counts_cache.get(r_id, {}).get(w, 0) for w in selected_set)
        
        c_key = region.get("coacher", "quoc") if region else "quoc"
        staff_list = staff_dict.get(c_key, [])
        staff = next((s for s in staff_list if s['short_id'] == staff_id), None)
        staff_name = staff['name'] if staff else staff_id
        
        qty_display = f"Tất cả ({total_data} data)" if qty_str == "all" else f"{qty_str} data"
        ward_items_text = "\n".join(f"• **{w}** (`{ward_counts_cache.get(r_id, {}).get(w, 0)}` data)" for w in sorted(selected_set))
        
        text = (
            "⚠️ **XÁC NHẬN PHÂN CÔNG THEO PHƯỜNG / XÃ**\n\n"
            f"📍 Khu vực: **{region['name'] if region else r_id}**\n"
            f"🏙️ Phường/Xã ({len(selected_set)}):\n{ward_items_text}\n"
            f"🔢 Số lượng: **{qty_display}**\n"
            f"👤 Bàn giao cho: **{staff_name}** ({staff_id})\n\n"
            "Bạn có chắc chắn muốn thực hiện phân công này không?"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(text="✅ Đồng ý & Bắt đầu", callback_data=f"px_m_cfm:{r_id}:{staff_id}:{qty_str}"),
            InlineKeyboardButton(text="❌ Hủy & Chọn lại", callback_data=f"px_m_stf:{r_id}:{staff_id}")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("px_m_cfm:"):
        parts = data.split(":")
        r_id = parts[1].lower()
        staff_id = parts[2]
        qty_str = parts[3]
        region = next((r for r in regions_list if r['id'].lower() == r_id), None)
        selected_set = ward_selection_session.get((chat_id, r_id), set())
        
        if not region or not selected_set:
            bot.answer_callback_query(call.id, "❌ Phiên làm việc đã hết hạn, vui lòng chọn lại.")
            return
            
        bot.answer_callback_query(call.id, "Đang khởi chạy...")
        
        qty_val = "all" if qty_str == "all" else int(qty_str)
        target_wards = list(selected_set)
        
        threading.Thread(
            target=process_region_assignment_callback,
            args=(chat_id, message_id, region, qty_val, staff_id, target_wards),
            daemon=True
        ).start()

    elif data.startswith("qty:"):
        parts = data.split(":")
        region_id = parts[1]
        quantity = int(parts[2])
        region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
        
        markup = get_staff_markup(region_id, quantity)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📍 **Khu vực**: {region['name']}\n🔢 **Số lượng đã chọn**: `{quantity}` data\n\n👉 **Bước 2: Chọn nhân sự muốn bàn giao:**",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif data.startswith("show_all_staff:"):
        parts = data.split(":")
        region_id = parts[1]
        quantity = int(parts[2])
        region = next((r for r in regions_list if r['id'].lower() == region_id.lower()), None)
        
        markup = get_staff_markup(region_id, quantity, show_all=True)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📍 **Khu vực**: {region['name']}\n🔢 **Số lượng đã chọn**: `{quantity}` data\n\n👉 **Bước 2: Chọn nhân sự muốn bàn giao (Hiển thị tất cả):**",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    elif data.startswith("assign:"):
        parts = data.split(":")
        region_id = parts[1]
        quantity = int(parts[2])
        staff_id = parts[3]
        region = next((r for r in regions_list if r['id'] == region_id), None)
        
        c_key = region.get("coacher", "quoc") if region else "quoc"
        staff_list = staff_dict.get(c_key, [])
        staff = next((s for s in staff_list if s['short_id'] == staff_id), None)
        staff_name = staff['name'] if staff else staff_id
        
        bot.answer_callback_query(call.id, f"Chọn nhân sự: {staff_name}")
        
        text = (
            "⚠️ **XÁC NHẬN PHÂN CÔNG**\n\n"
            f"📍 Khu vực: **{region['name']}**\n"
            f"🔢 Số lượng: **{quantity}** data\n"
            f"👤 Bàn giao cho: **{staff_name}**\n\n"
            "Bạn có chắc chắn muốn thực hiện phân công này không?"
        )
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(text="✅ Đồng ý & Bắt đầu", callback_data=f"confirm:{region_id}:{quantity}:{staff_id}"),
            InlineKeyboardButton(text="❌ Hủy & Chọn lại", callback_data=f"qty:{region_id}:{quantity}")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    elif data.startswith("confirm:"):
        parts = data.split(":")
        region_id = parts[1]
        quantity = int(parts[2])
        staff_id = parts[3]
        region = next((r for r in regions_list if r['id'] == region_id), None)
        
        bot.answer_callback_query(call.id, "Đang khởi chạy...")
        
        threading.Thread(
            target=process_region_assignment_callback,
            args=(chat_id, message_id, region, quantity, staff_id),
            daemon=True
        ).start()

def process_checkquoc_command(chat_id, message_id=None):
    loading_text = "⏳ **Đang kiểm tra tổng hợp dữ liệu cho Coacher Ái Quốc (Khu vực treo & ATC nhân sự)...**"
    if message_id:
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=loading_text, parse_mode="Markdown")
        except:
            pass
    else:
        msg = bot.send_message(chat_id, loading_text, parse_mode="Markdown")
        message_id = msg.message_id

    quoc_regions = [r for r in regions_list if r.get("coacher") == "quoc"]
    quoc_staff = staff_dict.get("quoc", [])

    def fetch_all_staff():
        view_url = "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154"
        import crm_api
        rows = crm_api.fetch_crm_export(view_url)
        results = []
        if not rows or len(rows) < 1:
            for s in quoc_staff:
                s_name = s["name"]
                short_name = f"{s_name.split(' - ')[0]} - {s_name.split(' - ')[1]}" if " - " in s_name else s_name
                results.append((s, short_name, 0))
            return results

        headers = rows[0]
        o_idx = headers.index("Người xử lý") if "Người xử lý" in headers else 13
        staff_counts = {s["short_id"]: 0 for s in quoc_staff}
        for r in rows[1:]:
            if len(r) > o_idx:
                owner_val = r[o_idx].strip()
                for s in quoc_staff:
                    if s["short_id"] in owner_val:
                        staff_counts[s["short_id"]] += 1
                        break

        for s in quoc_staff:
            s_name = s["name"]
            short_name = f"{s_name.split(' - ')[0]} - {s_name.split(' - ')[1]}" if " - " in s_name else s_name
            results.append((s, short_name, staff_counts.get(s["short_id"], 0)))
        return results

    def scan_region(region):
        try:
            summary = get_region_summary(region["url"])
            total = summary["total_unassigned"] if summary else 0
            return region, total
        except:
            return region, 0

    with ThreadPoolExecutor(max_workers=12) as executor:
        staff_future = executor.submit(fetch_all_staff)
        region_futures = [executor.submit(scan_region, r) for r in quoc_regions]

        staff_results = staff_future.result()
        region_results = [f.result() for f in region_futures]

    total_region_hanging = sum(r[1] for r in region_results)
    
    # Sort regions descending
    region_results.sort(key=lambda x: x[1], reverse=True)
    part1_lines = []
    for r_obj, total in region_results:
        icon = "🟢" if total > 0 else "🔴"
        part1_lines.append(f"• {icon} **{r_obj['name']}**: `{total}` data")

    # Sort staff descending
    staff_results.sort(key=lambda x: x[2], reverse=True)
    counts = [s[2] for s in staff_results]
    max_c = max(counts) if counts else -1
    min_c = min(counts) if counts else -1

    part2_lines = []
    for s_item, short_name, count in staff_results:
        if count == max_c and max_c > min_c:
            icon = "🔴"
            tag = " *(Cao nhất)*"
        elif count == min_c and max_c > min_c:
            icon = "🟢"
            tag = " *(Thấp nhất)*"
        else:
            icon = "🟡"
            tag = ""
        part2_lines.append(f"• {icon} **{short_name}**: `{count}` ATC treo{tag}")

    total_staff_holding = sum(counts)
    grand_total = total_region_hanging + total_staff_holding

    report_text = (
        f"📊 **BÁO CÁO TỔNG HỢP & GỢI Ý CHIA DATA - COACHER ÁI QUỐC**\n"
        f"⏰ *Thời gian quét*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        f"📍 **1. DATA TREO CÁC KHU VỰC (Tổng: `{total_region_hanging}` data):**\n"
        + "\n".join(part1_lines) + "\n\n"
        f"👤 **2. TỔNG SỐ ATC TREO TỪNG NHÂN SỰ ĐANG GIỮ (Tổng: `{total_staff_holding}` ATC treo):**\n"
        + "\n".join(part2_lines) + "\n\n"
        f"🔥 **TỔNG CỘNG TẤT CẢ DATA TREO & TỒN ĐỌNG: `{grand_total}` data**\n\n"
        f"👉 **3. GỢI Ý CHIA DATA NHANH 1-CLICK (Bấm nút bên dưới để chọn chia ngay):**"
    )

    markup = InlineKeyboardMarkup(row_width=1)
    
    staff_lookup = {}
    for s_item, short_name, count in staff_results:
        s_id = s_item["short_id"]
        first_name = short_name.split(" - ")[1] if " - " in short_name else short_name
        staff_lookup[s_id] = (first_name, count)

    suggest_buttons = []
    active_regions = [r for r, t in region_results if t > 0]
    active_regions.sort(key=lambda x: next(t for r, t in region_results if r["id"] == x["id"]), reverse=True)
    
    for r_obj in active_regions[:5]:
        r_id = r_obj["id"]
        r_name = r_obj["name"]
        r_total = next(t for r, t in region_results if r["id"] == r_id)
        
        allowed_ids = r_obj.get("staff_ids", [])
        if allowed_ids:
            candidate_ids = [sid for sid in allowed_ids if sid in staff_lookup]
            candidate_ids.sort(key=lambda sid: staff_lookup[sid][1])
        else:
            candidate_ids = []

        if not candidate_ids:
            candidate_ids = [s[0]["short_id"] for s in sorted(staff_results, key=lambda x: x[2])]

        for sid in candidate_ids[:1]:
            fname, scount = staff_lookup[sid]
            qty_to_assign = min(5, r_total)
            btn_text = f"⚡ Chia {qty_to_assign} {r_name} ➔ {fname} (hiện giữ ít nhất: {scount})"
            suggest_buttons.append(InlineKeyboardButton(text=btn_text, callback_data=f"assign:{r_id}:{qty_to_assign}:{sid}"))

    for btn in suggest_buttons:
        markup.add(btn)
        
    markup.add(
        InlineKeyboardButton(text="🔄 Quét lại /checkquoc", callback_data="checkquoc_refresh"),
        InlineKeyboardButton(text="📋 Danh sách Khu vực", callback_data="coacher:quoc")
    )

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=report_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

def process_sla_command(chat_id, message_id=None):
    loading_text = "⏳ **Đang quét dữ liệu cảnh báo SLA (>= 10 ngày) các khu vực & nhân sự Coacher Ái Quốc...**"
    if message_id:
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=loading_text, parse_mode="Markdown")
        except:
            pass
    else:
        msg = bot.send_message(chat_id, loading_text, parse_mode="Markdown")
        message_id = msg.message_id

    quoc_regions = [r for r in regions_list if r.get("coacher") == "quoc"]
    quoc_staff = staff_dict.get("quoc", [])
    now = datetime.datetime.now()

    def parse_retailer_id(raw):
        m = re.findall(r'\d{5,}', str(raw))
        return m[-1] if m else str(raw)

    def scan_region_sla(region):
        items = []
        rows = fetch_crm_export(region['url'])
        if not rows or len(rows) < 2: return items
        headers = rows[0]
        try:
            r_idx = headers.index('Retailer ID')
            t_idx = headers.index('Thời gian tạo')
            c_idx = headers.index('Tỉnh/Thành phố')
            w_idx = headers.index('Xã/Phường/Thị trấn')
            o_idx = headers.index('Người xử lý')
        except: return items
        for row in rows[1:]:
            if len(row) <= max(r_idx, t_idx, c_idx, w_idx, o_idx): continue
            r_id = parse_retailer_id(row[r_idx])
            c_str = row[t_idx].strip()
            try:
                date_str = c_str.split()[0]
                c_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                sla_days = (now - c_date).days
                fmt_date = c_date.strftime('%d/%m/%Y')
            except: continue
            if sla_days >= 10:
                items.append({
                    'retailer_id': r_id,
                    'created_time': c_str,
                    'fmt_date': fmt_date,
                    'city': row[c_idx].strip(),
                    'ward': row[w_idx].strip(),
                    'sla_days': sla_days,
                    'owner': row[o_idx].strip(),
                    'source': region['name']
                })
        return items

    def scan_staff_sla(staff_item):
        items = []
        staff_full_name = staff_item['name']
        short_name = staff_full_name
        if ' - ' in staff_full_name:
            parts = staff_full_name.split(' - ')
            short_name = f"{parts[0]} - {parts[1]}"
        encoded_name = urllib.parse.quote(staff_full_name)
        staff_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154&orderby=&sortorder=&search_params=%5B%5B%5B%22assigned_user_id%22%2C%22c%22%2C%22{encoded_name}%22%5D%5D%5D"
        rows = fetch_crm_export(staff_url)
        if not rows or len(rows) < 2: return items
        headers = rows[0]
        try:
            r_idx = headers.index('Retailer ID')
            t_idx = headers.index('Thời gian tạo')
            c_idx = headers.index('Tỉnh/Thành phố')
            w_idx = headers.index('Xã/Phường/Thị trấn')
            o_idx = headers.index('Người xử lý')
        except: return items
        for row in rows[1:]:
            if len(row) <= max(r_idx, t_idx, c_idx, w_idx, o_idx): continue
            r_id = parse_retailer_id(row[r_idx])
            c_str = row[t_idx].strip()
            try:
                date_str = c_str.split()[0]
                c_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                sla_days = (now - c_date).days
                fmt_date = c_date.strftime('%d/%m/%Y')
            except: continue
            if sla_days >= 10:
                items.append({
                    'retailer_id': r_id,
                    'created_time': c_str,
                    'fmt_date': fmt_date,
                    'city': row[c_idx].strip(),
                    'ward': row[w_idx].strip(),
                    'sla_days': sla_days,
                    'owner': short_name,
                    'source': short_name
                })
        return items

    with ThreadPoolExecutor(max_workers=8) as executor:
        r_results = list(executor.map(scan_region_sla, quoc_regions))
        s_results = list(executor.map(scan_staff_sla, quoc_staff))

    all_region_sla = [item for sub in r_results for item in sub]
    all_staff_sla = [item for sub in s_results for item in sub]

    total_region_count = len(all_region_sla)
    total_staff_count = len(all_staff_sla)
    grand_total_sla = total_region_count + total_staff_count

    staff_groups = {}
    for item in all_staff_sla:
        owner = item['owner']
        if owner not in staff_groups: staff_groups[owner] = []
        staff_groups[owner].append(item)

    sorted_staff = sorted(staff_groups.items(), key=lambda x: len(x[1]), reverse=True)

    part_staff_lines = []
    for owner, items_list in sorted_staff:
        items_list.sort(key=lambda x: x['sla_days'], reverse=True)
        part_staff_lines.append(f"👤 **{owner}** (trễ `{len(items_list)}` data):")
        for it in items_list[:5]:
            part_staff_lines.append(f"  • Retailer ID: `{it['retailer_id']}` | **{it['fmt_date']}({it['sla_days']})** | {it['city']} - {it['ward']}")
        if len(items_list) > 5:
            part_staff_lines.append(f"  _... và {len(items_list)-5} data trễ SLA khác_")
        part_staff_lines.append("")

    region_groups = {}
    for item in all_region_sla:
        reg_name = item['source']
        if reg_name not in region_groups: region_groups[reg_name] = []
        region_groups[reg_name].append(item)

    sorted_regions = sorted(region_groups.items(), key=lambda x: len(x[1]), reverse=True)

    part_region_lines = []
    for reg_name, items_list in sorted_regions:
        items_list.sort(key=lambda x: x['sla_days'], reverse=True)
        part_region_lines.append(f"📍 **{reg_name}** (trễ `{len(items_list)}` data chưa chia):")
        for it in items_list[:5]:
            part_region_lines.append(f"  • Retailer ID: `{it['retailer_id']}` | **{it['fmt_date']}({it['sla_days']})** | {it['city']} - {it['ward']} | {it['owner']}")
        if len(items_list) > 5:
            part_region_lines.append(f"  _... và {len(items_list)-5} data trễ SLA chưa chia khác_")
        part_region_lines.append("")

    header_text = (
        f"🚨 **BÁO CÁO CẢNH BÁO SLA (DỮ LIỆU TẠO >= 10 NGÀY)**\n"
        f"⏰ *Thời gian quét*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n"
        f"👥 *Coacher*: **Ái Quốc**\n\n"
        f"📊 **TỔNG QUAN:**\n"
        f"• Data trễ SLA Nhân sự đang giữ: `{total_staff_count}` data\n"
        f"• Data trễ SLA Khu vực chưa chia: `{total_region_count}` data\n"
        f"🔥 **TỔNG CỘNG TRỄ SLA >= 10 NGÀY: `{grand_total_sla}` data**\n\n"
    )

    full_text = header_text
    if part_staff_lines:
        full_text += "💼 **I. CÁC CÁ NHÂN ĐANG GIỮ DATA TRỄ SLA:**\n" + "\n".join(part_staff_lines) + "\n"
    if part_region_lines:
        full_text += "📍 **II. KHU VỰC CÒN DATA TRỄ SLA CHƯA CHIA:**\n" + "\n".join(part_region_lines) + "\n"

    if grand_total_sla == 0:
        full_text += "🎉 _Hiện tại không có data nào bị trễ SLA >= 10 ngày!_"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(text="🔄 Quét lại /sla", callback_data="sla_refresh"),
        InlineKeyboardButton(text="📋 Báo cáo /checkquoc", callback_data="checkquoc_refresh")
    )

    try:
        if len(full_text) > 4000:
            mid_point = full_text[:4000].rfind("\n\n")
            if mid_point == -1: mid_point = 3900
            msg1 = full_text[:mid_point]
            msg2 = full_text[mid_point:]
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msg1, parse_mode="Markdown")
            bot.send_message(chat_id=chat_id, text=msg2, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=full_text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id=chat_id, text=full_text[:4000], reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['sla'])
def handle_sla_command(message):
    threading.Thread(target=process_sla_command, args=(message.chat.id,), daemon=True).start()

@bot.message_handler(commands=['checkquoc'])
def handle_checkquoc_command(message):
    threading.Thread(target=process_checkquoc_command, args=(message.chat.id,), daemon=True).start()

@bot.message_handler(commands=['report', 'gchat'])
def handle_report_command(message):
    status_msg = bot.reply_to(message, "⏳ **Đang tổng hợp báo cáo và bắn lên Google Chat Space...**", parse_mode="Markdown")
    def update_log(txt):
        try:
            bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=f"⏳ {txt}", parse_mode="Markdown")
        except:
            pass
            
    def run_report():
        success, res_text = send_google_chat_report(log_callback=update_log)
        if success:
            bot.send_message(
                message.chat.id,
                f"🎉 **ĐÃ GỬI BÁO CÁO THÀNH CÔNG LÊN GOOGLE CHAT!**\n\n{res_text}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ **LỖI GỬI BÁO CÁO GOOGLE CHAT:** {res_text}",
                parse_mode="Markdown"
            )
            
    threading.Thread(target=run_report, daemon=True).start()

@bot.message_handler(commands=['checktk', 'ticket', 'gchat_tk'])
def handle_checktk_command(message):
    status_msg = bot.reply_to(message, "⏳ **Đang tổng hợp Ticket treo và bắn lên Google Chat Space...**", parse_mode="Markdown")
    def run_checktk():
        import quick_action
        success, res_text = quick_action.do_send_ticket_gchat()
        if success:
            bot.send_message(
                message.chat.id,
                f"🎉 **ĐÃ GỬI BÁO CÁO TICKET TREO LÊN GOOGLE CHAT THÀNH CÔNG!**\n\n{res_text[:3500]}",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ **LỖI GỬI BÁO CÁO TICKET TREO:** {res_text}",
                parse_mode="Markdown"
            )
    threading.Thread(target=run_checktk, daemon=True).start()

@bot.message_handler(commands=['checkrenew', 'taiky', 'sctaiky'])
def handle_checkrenew_command(message):
    status_msg = bot.reply_to(message, "⏳ **Đang quét Ticket SC Group từ Team Tái Ký...**", parse_mode="Markdown")
    def run_checkrenew():
        import sc_renew_monitor
        cnt = sc_renew_monitor.scan_and_notify_sc_renew(is_warmup=False)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            text=f"✅ **Đã quét xong Ticket SC Group Tái Ký!**\n- Số ticket mới được gửi Google Chat: `{cnt}`",
            parse_mode="Markdown"
        )
    threading.Thread(target=run_checkrenew, daemon=True).start()

@bot.message_handler(commands=['updatesheet', 'sheet', 'capnhatsheet'])
def handle_updatesheet_command(message):
    status_msg = bot.reply_to(message, "⏳ **Đang quét CRM và tự động cập nhật Google Sheet Miền Nam...**", parse_mode="Markdown")
    def run_sheet():
        try:
            import auto_sheet_updater
            import importlib
            importlib.reload(auto_sheet_updater)
            success, r_msg = auto_sheet_updater.run_auto_update_hcm_sheet()
            try:
                bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=r_msg, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=r_msg, disable_web_page_preview=True)
        except Exception as e:
            bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=f"❌ Lỗi cập nhật sheet: {e}")
    threading.Thread(target=run_sheet, daemon=True).start()

def get_tanbinh_sheet_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👤 8447 - Võ Khánh Duy", callback_data="add_tb_sheet:8447"),
        InlineKeyboardButton("👤 8440 - Doãn Việt Tùng", callback_data="add_tb_sheet:8440")
    )
    markup.add(
        InlineKeyboardButton("👤 8448 - Nguyễn Đỗ Nhật Minh", callback_data="add_tb_sheet:8448"),
        InlineKeyboardButton("👤 8467 - Nguyễn Thành Đạt", callback_data="add_tb_sheet:8467")
    )
    markup.add(
        InlineKeyboardButton("🗑️ Xoá cụm Tân Bình khỏi Sheet", callback_data="del_tb_sheet:all"),
        InlineKeyboardButton("❌ Đóng", callback_data="close_tb_sheet")
    )
    return markup

@bot.message_handler(commands=['themtb', 'addtb', 'themtanbinh', 'add_tb', 'dientb'])
def handle_themtb_command(message):
    _execute_add_tb_sheet(message.chat.id)

@bot.message_handler(commands=['xoatb', 'deltb', 'xoatanbinh', 'del_tb', 'xoatb_sheet'])
def handle_xoatb_command(message):
    _execute_del_tb_sheet(message.chat.id)

def _execute_add_tb_sheet(chat_id, message_id=None):
    wait_text = "⏳ **Đang điền thêm 6 phường cụm Tân Bình cũ (Cột D: `backup Tân Bình cũ`) vào Google Sheet...**"
    if message_id:
        status_msg_id = message_id
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=wait_text, parse_mode="Markdown")
        except: pass
    else:
        st_msg = bot.send_message(chat_id, wait_text, parse_mode="Markdown")
        status_msg_id = st_msg.message_id

    def run_worker():
        try:
            import auto_sheet_updater
            import importlib
            importlib.reload(auto_sheet_updater)
            success, r_msg = auto_sheet_updater.add_tan_binh_backup_sheet()
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=r_msg, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=r_msg, disable_web_page_preview=True)
        except Exception as e:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"❌ Lỗi điền sheet: {e}")

    threading.Thread(target=run_worker, daemon=True).start()

def _execute_del_tb_sheet(chat_id, message_id=None):
    wait_text = "⏳ **Đang xoá 6 phường cụm Tân Bình cũ khỏi Google Sheet...**"
    if message_id:
        status_msg_id = message_id
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=wait_text, parse_mode="Markdown")
        except: pass
    else:
        st_msg = bot.send_message(chat_id, wait_text, parse_mode="Markdown")
        status_msg_id = st_msg.message_id

    def run_worker():
        try:
            import auto_sheet_updater
            import importlib
            importlib.reload(auto_sheet_updater)
            success, r_msg = auto_sheet_updater.remove_tan_binh_backup_sheet()
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=r_msg, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=r_msg, disable_web_page_preview=True)
        except Exception as e:
            bot.edit_message_text(chat_id=chat_id, message_id=status_msg_id, text=f"❌ Lỗi xoá sheet: {e}")

    threading.Thread(target=run_worker, daemon=True).start()

REGION_ALIASES = {
    "cto": "cantho",
    "cantho": "cantho",
    "cần thơ": "cantho",
    "hcm": "hcm",
    "sgn": "hcm",
    "sg": "hcm",
    "sài gòn": "hcm",
    "sai gon": "hcm",
    "hồ chí minh": "hcm",
    "gialai": "gialai",
    "gli": "gialai",
    "gia lai": "gialai",
    "lamdong": "lamdong",
    "ldg": "lamdong",
    "lâm đồng": "lamdong",
    "vungtau": "vungtau",
    "vtu": "vungtau",
    "vũng tàu": "vungtau",
    "soctrang": "soctrang",
    "sóc trăng": "soctrang",
    "camau": "camau",
    "cà mau": "camau",
    "quynhon": "quynhon",
    "bdh": "quynhon",
    "quy nhơn": "quynhon",
    "sapnhap": "sapnhap",
    "sáp nhập": "sapnhap",
    "hanoi": "hanoi",
    "hni": "hanoi",
    "hà nội": "hanoi",
    "danang": "danang",
    "dng": "danang",
    "đà nẵng": "danang",
    "hue": "hue",
    "huế": "hue",
    "haiphong": "haiphong",
    "hpg": "haiphong",
    "hải phòng": "haiphong",
    "thainguyen": "thainguyen",
    "thái nguyên": "thainguyen",
    "thanhhoa": "thanhhoa",
    "thanh hóa": "thanhhoa",
    "quangninh": "quangninh",
    "quảng ninh": "quangninh",
    "dongnai": "dongnai",
    "dn": "dongnai",
    "đn": "dongnai",
    "đồng nai": "dongnai",
    "dong nai": "dongnai",
    "bacninh": "bacninh",
    "bn": "bacninh",
    "bắc ninh": "bacninh",
    "bac ninh": "bacninh",
    "bnh": "bacninh",
}

def normalize_region_id(raw_id, known_region_ids):
    if not raw_id:
        return None
    c = raw_id.strip().lower()
    mapped = REGION_ALIASES.get(c, c)
    for r_id in known_region_ids:
        if r_id.lower() == mapped.lower():
            return r_id
    for r_id in known_region_ids:
        if c == r_id.lower():
            return r_id
    return None

def parse_ward_command(text, known_region_ids):
    raw = text.strip()
    for prefix in ["/px", "px ", "chia "]:
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix):].strip()
            
    parts = raw.split()
    if len(parts) < 3:
        return None
        
    norm_rid = normalize_region_id(parts[0], known_region_ids)
    if not norm_rid:
        return None
    region_id = norm_rid
        
    staff_id = parts[-1]
    if not (staff_id.isdigit() and len(staff_id) >= 4):
        if len(parts) >= 4 and parts[-2].lower() == 'cho' and parts[-1].isdigit():
            staff_id = parts[-1]
            parts = parts[:-2]
        else:
            return None
    else:
        parts = parts[:-1]
        if parts and parts[-1].lower() == 'cho':
            parts = parts[:-1]
            
    middle = parts[1:]
    if not middle:
        return None
        
    last_m = middle[-1].lower()
    if last_m in ('all', 'tatca', 'tất cả') or last_m.isdigit():
        qty = last_m
        ward_parts = middle[:-1]
    else:
        qty = 'all'
        ward_parts = middle
        
    if not ward_parts:
        return None
        
    ward_str = " ".join(ward_parts).strip()
    return {
        "region_id": region_id,
        "ward_str": ward_str,
        "quantity": qty,
        "staff_id": staff_id
    }

def parse_region_command(text, known_region_ids):
    raw = text.strip()
    for prefix in ["/chia ", "chia ", "/assign ", "assign "]:
        if raw.lower().startswith(prefix):
            raw = raw[len(prefix):].strip()
            break
            
    parts = raw.split()
    if not (2 <= len(parts) <= 5):
        return None
        
    filtered_parts = [p for p in parts if p.lower() != "cho"]
    if len(filtered_parts) < 2:
        return None
        
    region_id = None
    region_idx = -1
    for idx, p in enumerate(filtered_parts):
        matched = normalize_region_id(p, known_region_ids)
        if matched:
            region_id = matched
            region_idx = idx
            break
            
    if not region_id:
        return None
        
    rem = filtered_parts[:region_idx] + filtered_parts[region_idx + 1:]
    if not rem:
        return None
        
    staff_id = None
    staff_idx = -1
    for idx, token in enumerate(rem):
        if token.isdigit() and len(token) >= 4:
            staff_id = token
            staff_idx = idx
            break
            
    if not staff_id:
        return None
        
    rem_after_staff = rem[:staff_idx] + rem[staff_idx + 1:]
    qty = 'all'
    if rem_after_staff:
        qty_token = rem_after_staff[0].lower()
        if qty_token in ('all', 'tatca', 'tất cả'):
            qty = 'all'
        elif qty_token.isdigit():
            qty = int(qty_token)
        else:
            return None
            
    return {
        "region_id": region_id,
        "staff_id": staff_id,
        "quantity": qty
    }

def resolve_ward_names(ward_str, cached_wards):
    parts = [p.strip() for p in ward_str.split(',') if p.strip()]
    resolved = []
    is_indices = True
    indices = []
    for p in parts:
        if '-' in p and p.replace('-', '').isdigit():
            try:
                start, end = map(int, p.split('-', 1))
                indices.extend(range(start, end + 1))
            except Exception:
                is_indices = False
                break
        elif p.isdigit():
            indices.append(int(p))
        else:
            is_indices = False
            break
            
    if is_indices and indices:
        for idx in indices:
            if 1 <= idx <= len(cached_wards):
                resolved.append(cached_wards[idx - 1])
    else:
        resolved = [w.strip() for w in ward_str.split(',') if w.strip()]
    return resolved

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text.strip()

    # Lưu chat_id mới nhất để gửi thông báo tự động (06:30 & 20:30)
    try:
        last_chat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_chat_id.txt")
        with open(last_chat_file, "w", encoding="utf-8") as f:
            f.write(str(message.chat.id))
    except Exception:
        pass
    
    if text.lower() in ["sla", "/sla"]:
        threading.Thread(target=process_sla_command, args=(message.chat.id,), daemon=True).start()
        return

    if text.lower() in ["checkquoc", "/checkquoc"]:
        threading.Thread(target=process_checkquoc_command, args=(message.chat.id,), daemon=True).start()
        return

    if text.lower() in ["autoassign", "/autoassign", "chiatudong", "/chiatudong", "chia tu dong"]:
        def run_auto_cmd():
            status_msg = bot.send_message(message.chat.id, "⏳ **Đang quét và tự động phân công data (< 10 ATC)...**", parse_mode="Markdown")
            import quick_action
            success, r_msg, _ = quick_action.do_auto_assign_under_10(batch_size=8, threshold=10, dry_run=False)
            bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=r_msg, parse_mode="Markdown")
        threading.Thread(target=run_auto_cmd, daemon=True).start()
        return

    if text.lower() in ["checkauto", "/checkauto", "check chia", "/checkchia", "test chia"]:
        def run_check_auto_cmd():
            status_msg = bot.send_message(message.chat.id, "⏳ **Đang kiểm tra mô phỏng chia data (< 10 ATC - Dry Run)...**", parse_mode="Markdown")
            import quick_action
            success, r_msg, _ = quick_action.do_auto_assign_under_10(batch_size=8, threshold=10, dry_run=True)
            bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=r_msg, parse_mode="Markdown")
        threading.Thread(target=run_check_auto_cmd, daemon=True).start()
        return

    if text.lower() in ["report", "/report", "gchat", "/gchat"]:
        handle_report_command(message)
        return

    if text.lower() in ["checktk", "/checktk", "ticket", "/ticket", "gchat_tk", "/gchat_tk"]:
        handle_checktk_command(message)
        return

    if text.lower() in ["checkrenew", "/checkrenew", "taiky", "/taiky", "sctaiky", "/sctaiky"]:
        handle_checkrenew_command(message)
        return

    if text.lower() in [
        "updatesheet", "/updatesheet", "sheet", "/sheet", "capnhatsheet", "/capnhatsheet",
        "update sheet", "/update sheet", "cập nhật sheet", "cap nhat sheet",
        "điền phường xã", "dien phuong xa", "điền sheet", "dien sheet", "chạy sheet", "chay sheet"
    ]:
        handle_updatesheet_command(message)
        return

    # Lệnh thêm / điền cụm Tân Bình cũ vào Google Sheet
    match_themtb = re.match(r"^(?:themtb|addtb|themtanbinh|dientb|dien_tb|them_tb|thêm\s*tb|them\s*tb|thêm\s*tân\s*bình|them\s*tan\s*binh|điền\s*tb|dien\s*tb|điền\s*tân\s*bình|dien\s*tan\s*binh|điền\s*backup\s*tân\s*bình|dien\s*backup\s*tan\s*binh|điền\s*backup\s*tb|dien\s*backup\s*tb)(?:\s+.*)?$", text, re.IGNORECASE)
    if match_themtb:
        _execute_add_tb_sheet(message.chat.id)
        return

    # Lệnh xoá / gỡ cụm Tân Bình cũ khỏi Google Sheet
    match_xoatb = re.match(r"^(?:xoatb|deltb|xoatanbinh|del_tb|xoa_tb|xóa\s*tb|xoa\s*tb|xóa\s*tân\s*bình|xoa\s*tan\s*binh|xáo\s*tb|xao\s*tb|xáo\s*tân\s*bình|xao\s*tan\s*binh|xóa\s*backup\s*tân\s*bình|xoa\s*backup\s*tan\s*binh|xóa\s*backup\s*tb|xoa\s*backup\s*tb)$", text, re.IGNORECASE)
    if match_xoatb:
        _execute_del_tb_sheet(message.chat.id)
        return

    match_goiy = re.match(r"^(?:goiy|goi\s*y|gợi\s*ý|gơi\s*y|suggest)\s*([a-zA-Z0-9_-]+)?$", text, re.IGNORECASE)
    if match_goiy:
        r_raw = match_goiy.group(1) or "hcm"
        r_norm = normalize_region_id(r_raw, [r['id'] for r in regions_list])
        target_reg = next((r for r in regions_list if r['id'].lower() == (r_norm or r_raw).lower()), None)
        if target_reg:
            msg = bot.reply_to(
                message,
                f"⏳ **Đang chuẩn bị bảng gợi ý data theo nhân sự (Chính + Backup): {target_reg['name']}...**",
                parse_mode="Markdown"
            )
            threading.Thread(
                target=process_staff_suggest_menu,
                args=(message.chat.id, msg.message_id, target_reg),
                daemon=True
            ).start()
            return

    match_tb = re.match(r"^(?:tanbinh|tan\s*binh|tân\s*bình|tb|backup\s*cty|backup\s*tan\s*binh)\s*$", text, re.IGNORECASE)
    if match_tb:
        msg = bot.reply_to(message, "⏳ **Đang quét dữ liệu cụm Tân Bình cũ (quanh công ty)...**", parse_mode="Markdown")
        threading.Thread(target=process_tanbinh_menu, args=(message.chat.id, msg.message_id), daemon=True).start()
        return

    match_tb_cmd = re.match(r"^(?:tanbinh|tan\s*binh|tân\s*bình|tb)\s+(\d{4,5})\s+(\d+|all|tatca|tất cả)$", text, re.IGNORECASE)
    if match_tb_cmd:
        s_id = match_tb_cmd.group(1)
        q_str = match_tb_cmd.group(2)
        if s_id not in TAN_BINH_ALLOWED_STAFF:
            bot.reply_to(message, f"❌ Cụm Tân Bình cũ chỉ áp dụng cho nhân sự quanh cty (Duy 8447, Tùng 8440, Minh 8448, Đạt 8467). Nhân sự {s_id} không thuộc danh sách này!", parse_mode="Markdown")
            return
        qty_val = "all" if q_str.lower() in ("all", "tatca", "tất cả") else int(q_str)
        hcm_reg = next((r for r in regions_list if r['id'].lower() == 'hcm'), None)
        if hcm_reg:
            qty_display = "Tất cả" if qty_val == "all" else f"{qty_val} data"
            status_msg = bot.reply_to(
                message,
                f"⏳ **Bắt đầu phân công cụm Tân Bình cũ:**\n- Số lượng: `{qty_display}`\n- Nhân sự: `{s_id}`...",
                parse_mode="Markdown"
            )
            threading.Thread(
                target=process_region_assignment_callback,
                args=(message.chat.id, status_msg.message_id, hcm_reg, qty_val, s_id, TAN_BINH_BACKUP_WARDS, "tanbinh"),
                daemon=True
            ).start()
            return

    match_px_list = re.match(r"^(?:px|phuong|xa)\s+([a-zA-Z0-9_-]+)$", text, re.IGNORECASE)
    if match_px_list:
        r_id = match_px_list.group(1)
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        if region:
            scan_msg = bot.reply_to(
                message,
                f"⏳ **Đang quét danh sách Phường/Xã khu vực:** {region['name']}...",
                parse_mode="Markdown"
            )
            threading.Thread(
                target=process_ward_list_callback,
                args=(message.chat.id, scan_msg.message_id, region),
                daemon=True
            ).start()
            return

        
    known_rids = [r['id'] for r in regions_list]
    parsed_ward_cmd = parse_ward_command(text, known_rids)
    if parsed_ward_cmd:
        r_id = parsed_ward_cmd["region_id"]
        ward_raw = parsed_ward_cmd["ward_str"]
        qty_str = parsed_ward_cmd["quantity"]
        staff_id = parsed_ward_cmd["staff_id"]
        
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        if region:
            cached_wards = ward_cache.get(r_id.lower(), [])
            if not cached_wards:
                # Load from CRM if not in memory
                rows = fetch_crm_export(region['url'])
                if rows and len(rows) > 1:
                    w_idx = rows[0].index('Xã/Phường/Thị trấn') if 'Xã/Phường/Thị trấn' in rows[0] else 4
                    o_idx = rows[0].index('Người xử lý') if 'Người xử lý' in rows[0] else 11
                    allowed_kw = ["sc group", "chăm sóc khách hàng hỗ trợ trực tiếp", "hỗ trợ trực tiếp", "chăm sóc khách hàng", "direct support", "cskh"]
                    w_counts = {}
                    for row in rows[1:]:
                        if len(row) <= max(w_idx, o_idx): continue
                        if not any(kw in row[o_idx].lower() for kw in allowed_kw): continue
                        wv = row[w_idx].strip() or "Chưa cập nhật Phường/Xã"
                        w_counts[wv] = w_counts.get(wv, 0) + 1
                    sorted_w = sorted(w_counts.items(), key=lambda x: x[1], reverse=True)
                    ward_cache[r_id.lower()] = [w for w, c in sorted_w]
                    ward_counts_cache[r_id.lower()] = dict(sorted_w)
                    cached_wards = ward_cache[r_id.lower()]

            target_wards = resolve_ward_names(ward_raw, cached_wards)
            if not target_wards:
                bot.reply_to(message, f"❌ Không tìm thấy Phường/Xã `{ward_raw}` trong khu vực {region['name']}.")
                return
                
            qty_val = "all" if str(qty_str).lower() in ("all", "tatca", "tất cả") else int(qty_str)
            if isinstance(qty_val, int) and qty_val <= 0:
                bot.reply_to(message, "❌ Số lượng data cần phân công phải lớn hơn 0!")
                return
                
            ward_display = ", ".join(target_wards) if len(target_wards) <= 3 else f"{len(target_wards)} Phường/Xã ({', '.join(target_wards[:2])}...)"
            qty_display = "Tất cả" if qty_val == "all" else f"{qty_val} data"
            
            status_msg = bot.reply_to(
                message,
                f"⏳ **Bắt đầu phân công theo Phường/Xã:** {region['name']}\n- Phường/Xã: `{ward_display}`\n- Số lượng: `{qty_display}`\n- Nhân sự: `{staff_id}`...",
                parse_mode="Markdown"
            )
            
            threading.Thread(
                target=process_region_assignment_callback,
                args=(message.chat.id, status_msg.message_id, region, qty_val, staff_id, target_wards),
                daemon=True
            ).start()
            return

    parsed_reg_cmd = parse_region_command(text, known_rids)
    if parsed_reg_cmd:
        r_id = parsed_reg_cmd["region_id"]
        qty_val = parsed_reg_cmd["quantity"]
        staff_id = parsed_reg_cmd["staff_id"]
        
        region = next((r for r in regions_list if r['id'].lower() == r_id.lower()), None)
        if region:
            if isinstance(qty_val, int) and qty_val <= 0:
                bot.reply_to(message, "❌ Số lượng data cần phân công phải lớn hơn 0!")
                return
                
            w_map = region.get("ward_staff_map", {})
            val = w_map.get(str(staff_id))
            target_wards_arg = None
            ward_desc = ""
            if isinstance(val, dict):
                pri = val.get("primary", [])
                bak = val.get("backup", [])
                ward_desc = f" ({len(pri)} Phường chính + {len(bak)} Backup)"
                target_wards_arg = None  # Let process_region_assignment_callback handle primary + backup fallback
            elif isinstance(val, list):
                target_wards_arg = val
                if len(val) <= 3:
                    ward_desc = f" ({', '.join(val)})"
                else:
                    ward_desc = f" ({len(val)} Phường/Xã: {', '.join(val[:2])}...)"
                
            qty_display = "Tất cả" if qty_val == "all" else f"{qty_val} data"
            status_msg = bot.reply_to(
                message,
                f"⏳ **Bắt đầu phân công khu vực:** {region['name']}{ward_desc}\n- Số lượng: `{qty_display}`\n- Nhân sự: `{staff_id}`\n- Trạng thái: Đang chuẩn bị...",
                parse_mode="Markdown"
            )
            
            threading.Thread(
                target=process_region_assignment_callback,
                args=(message.chat.id, status_msg.message_id, region, qty_val, staff_id, target_wards_arg),
                daemon=True
            ).start()
            return

    norm_text_rid = normalize_region_id(text, [r['id'] for r in regions_list])

    matched_region = next((r for r in regions_list if r['id'].lower() == (norm_text_rid or text).lower()), None)
    if matched_region:
        scan_msg = bot.reply_to(
            message,
            f"⏳ **Đang quét dữ liệu CRM khu vực:** {matched_region['name']}...",
            parse_mode="Markdown"
        )
        threading.Thread(
            target=process_region_scan_callback,
            args=(message.chat.id, scan_msg.message_id, matched_region),
            daemon=True
        ).start()
        return
            
    # 1. Bàn giao có từ khóa đầu dòng: chuyen TT8802410 8460 / transfer nhanongcafe 8460 / ban giao 500123456 8460
    match_transfer_exp = re.match(r"^(?:chuyen|transfer|bàn\s*giao|ban\s*giao)\s+(.+?)\s+(\d{4,5})$", text, re.IGNORECASE)
    if match_transfer_exp:
        q_str = match_transfer_exp.group(1).strip()
        s_code = match_transfer_exp.group(2).strip()
        threading.Thread(target=process_transfer_thread, args=(message.chat.id, q_str, s_code), daemon=True).start()
        return

    # 2. Bàn giao có từ khóa ở giữa: TT8802410 chuyen 8460 / nhanongcafe cho 8460 / 500123456 sang 8460
    match_transfer_mid = re.match(r"^(.+?)\s+(?:chuyen|transfer|bàn\s*giao|ban\s*giao|cho|sang)\s+(\d{4,5})$", text, re.IGNORECASE)
    if match_transfer_mid:
        q_str = match_transfer_mid.group(1).strip()
        s_code = match_transfer_mid.group(2).strip()
        threading.Thread(target=process_transfer_thread, args=(message.chat.id, q_str, s_code), daemon=True).start()
        return

    # 3. Bàn giao theo mã Ticket trực tiếp: TT8802410 8460 / TT-107009062 8460
    match_ticket = re.match(r"^(TT\d+[\w-]*)\s+(\d{4,5})$", text, re.IGNORECASE)
    if match_ticket:
        q_str = match_ticket.group(1).strip()
        s_code = match_ticket.group(2).strip()
        threading.Thread(target=process_transfer_thread, args=(message.chat.id, q_str, s_code), daemon=True).start()
        return

    # 4. Cú pháp 2 từ chung: [Tên_Gian_Hàng / Retailer_ID / Mã_ATC] [Mã_NV] (Ví dụ: nhanongcafe 8460, 500988791 8460, 106887969 8460)
    match_general = re.match(r"^([a-zA-Z0-9_.-]+)\s+(\d{4,5})$", text)
    if match_general:
        token1 = match_general.group(1).strip()
        s_code = match_general.group(2).strip()
        reg_check = next((r for r in regions_list if r['id'].lower() == token1.lower()), None)
        if not reg_check:
            threading.Thread(target=process_transfer_thread, args=(message.chat.id, token1, s_code), daemon=True).start()
            return
        
    bot.reply_to(
        message, 
        "⚠️ Không khớp cú pháp lệnh nào!\n\n"
        "👉 **Bàn giao Ticket / ATC / Tên gian hàng:**\n"
        "• `[Tên Gian Hàng / Mã Ticket / Retailer ID] [Mã nhân sự]`\n"
        "  _Ví dụ_: `TT8802410 8460` hoặc `nhanongcafe 8460` hoặc `500988791 8460`\n"
        "  _Ví dụ_: `chuyen TT8802410 8460` hoặc `nhanongcafe chuyển 8460`\n\n"
        "👉 **Phân công data khu vực:**\n"
        "• Xem danh sách khu vực: `ds`\n"
        "• Xem Phường/Xã khu vực: `px [ID viết tắt]`\n"
        "• Chia theo Phường/Xã: `[ID viết tắt] [TênPhường/SốSTT] [Số lượng] [Mã nhân sự]`\n"
        "• Quét khu vực: `[ID viết tắt]`\n"
        "• Phân công khu vực: `[ID viết tắt] [Số lượng] [Mã nhân sự]`\n\n"
        "👉 **Báo cáo & Tiện ích:**\n"
        "• Báo cáo Coacher Quốc: `/checkquoc`\n"
        "• Báo cáo Ticket (TK) treo (tag Google Chat): `/checktk`\n"
        "• Cảnh báo SLA (>= 10 ngày): `/sla`\n"
        "• Bắn báo cáo Google Chat: `/report`",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    print("Bot tự động phân công ATC đang khởi động...")
    
    try:
        print("Đang xóa Webhook đang active (nếu có)...")
        bot.remove_webhook()
        print("Đã dọn dẹp Webhook thành công.")
    except Exception as e:
        print(f"Lỗi khi dọn dẹp Webhook: {e}")

    try:
        from selenium_helper import SeleniumHelper
        SeleniumHelper.kill_orphaned_chrome_processes()
        print("Đã dọn dẹp sạch Chrome chạy ngầm.")
    except Exception as e:
        print(f"Lỗi dọn dẹp Chrome khởi động: {e}")
        
    try:
        print("Đang cấu hình menu lệnh (commands list) cho Telegram...")
        bot.set_my_commands([
            telebot.types.BotCommand("chuyen", "Bàn giao Ticket / ATC / Gian hàng"),
            telebot.types.BotCommand("ds", "Danh sách khu vực"),
            telebot.types.BotCommand("px", "Xem & Chọn Phường/Xã khu vực"),
            telebot.types.BotCommand("checkquoc", "Check số lượng ATC treo của NS"),
            telebot.types.BotCommand("checktk", "Báo cáo Ticket treo & tag Google Chat"),
            telebot.types.BotCommand("sla", "Báo cáo cảnh báo trễ SLA (>= 10 ngày)"),
            telebot.types.BotCommand("report", "Bắn báo cáo Google Chat ngay"),
            telebot.types.BotCommand("updatesheet", "Cập nhật Google Sheet Miền Nam"),
            telebot.types.BotCommand("admincoacher", "Menu quản lý Coacher"),
            telebot.types.BotCommand("getcookie", "Lấy Cookie/Session mới từ CRM")
        ])
        print("Đã cấu hình menu lệnh thành công.")
    except Exception as e:
        print(f"Lỗi khi cấu hình menu lệnh: {e}")
        
    def send_sla_gchat_report():
        gchat_webhook = config.get("gchat_webhook")
        if not gchat_webhook:
            return False, "Chưa cấu hình gchat_webhook trong config.json"
            
        quoc_regions = [r for r in regions_list if r.get("coacher") == "quoc"]
        quoc_staff = staff_dict.get("quoc", [])
        now = datetime.datetime.now()

        def parse_retailer_id(raw):
            m = re.findall(r'\d{5,}', str(raw))
            return m[-1] if m else str(raw)

        def scan_region_sla(region):
            items = []
            rows = fetch_crm_export(region['url'])
            if not rows or len(rows) < 2: return items
            headers = rows[0]
            try:
                r_idx = headers.index('Retailer ID')
                t_idx = headers.index('Thời gian tạo')
                c_idx = headers.index('Tỉnh/Thành phố')
                w_idx = headers.index('Xã/Phường/Thị trấn')
                o_idx = headers.index('Người xử lý')
            except: return items
            for row in rows[1:]:
                if len(row) <= max(r_idx, t_idx, c_idx, w_idx, o_idx): continue
                r_id = parse_retailer_id(row[r_idx])
                c_str = row[t_idx].strip()
                try:
                    date_str = c_str.split()[0]
                    c_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    sla_days = (now - c_date).days
                    fmt_date = c_date.strftime('%d/%m/%Y')
                except: continue
                if sla_days >= 10:
                    items.append({
                        'retailer_id': r_id,
                        'created_time': c_str,
                        'fmt_date': fmt_date,
                        'city': row[c_idx].strip(),
                        'ward': row[w_idx].strip(),
                        'sla_days': sla_days,
                        'owner': row[o_idx].strip(),
                        'source': region['name']
                    })
            return items

        def scan_staff_sla(staff_item):
            items = []
            staff_full_name = staff_item['name']
            short_name = staff_full_name
            if ' - ' in staff_full_name:
                parts = staff_full_name.split(' - ')
                short_name = f"{parts[0]} - {parts[1]}"
            encoded_name = urllib.parse.quote(staff_full_name)
            staff_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=20154&orderby=&sortorder=&search_params=%5B%5B%5B%22assigned_user_id%22%2C%22c%22%2C%22{encoded_name}%22%5D%5D%5D"
            rows = fetch_crm_export(staff_url)
            if not rows or len(rows) < 2: return items
            headers = rows[0]
            try:
                r_idx = headers.index('Retailer ID')
                t_idx = headers.index('Thời gian tạo')
                c_idx = headers.index('Tỉnh/Thành phố')
                w_idx = headers.index('Xã/Phường/Thị trấn')
                o_idx = headers.index('Người xử lý')
            except: return items
            for row in rows[1:]:
                if len(row) <= max(r_idx, t_idx, c_idx, w_idx, o_idx): continue
                r_id = parse_retailer_id(row[r_idx])
                c_str = row[t_idx].strip()
                try:
                    date_str = c_str.split()[0]
                    c_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    sla_days = (now - c_date).days
                    fmt_date = c_date.strftime('%d/%m/%Y')
                except: continue
                if sla_days >= 10:
                    items.append({
                        'retailer_id': r_id,
                        'created_time': c_str,
                        'fmt_date': fmt_date,
                        'city': row[c_idx].strip(),
                        'ward': row[w_idx].strip(),
                        'sla_days': sla_days,
                        'owner': short_name,
                        'source': short_name
                    })
            return items

        with ThreadPoolExecutor(max_workers=8) as executor:
            r_results = list(executor.map(scan_region_sla, quoc_regions))
            s_results = list(executor.map(scan_staff_sla, quoc_staff))

        all_region_sla = [item for sub in r_results for item in sub]
        all_staff_sla = [item for sub in s_results for item in sub]

        total_region_count = len(all_region_sla)
        total_staff_count = len(all_staff_sla)
        grand_total_sla = total_region_count + total_staff_count

        staff_groups = {}
        for item in all_staff_sla:
            owner = item['owner']
            if owner not in staff_groups: staff_groups[owner] = []
            staff_groups[owner].append(item)

        gchat_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gchat_user_map.json")
        gchat_map = {}
        if os.path.exists(gchat_map_file):
            try:
                with open(gchat_map_file, "r", encoding="utf-8") as f:
                    gchat_map = json.load(f)
            except:
                gchat_map = {}

        sorted_staff = sorted(staff_groups.items(), key=lambda x: len(x[1]), reverse=True)

        tagged_users = []
        part_staff_lines = []
        for owner, items_list in sorted_staff:
            items_list.sort(key=lambda x: x['sla_days'], reverse=True)
            m_code = re.search(r'(\d{4})', owner)
            code = m_code.group(1) if m_code else ""
            if code and code in gchat_map and gchat_map[code].get("gchat_id"):
                gid = gchat_map[code]["gchat_id"]
                user_label = f"👤 <users/{gid}> (*{owner}*)"
                tagged_users.append(f"<users/{gid}>")
            else:
                user_label = f"👤 *{owner}*"

            part_staff_lines.append(f"{user_label} (trễ *{len(items_list)}* data):")
            for it in items_list[:5]:
                part_staff_lines.append(f"  • Retailer ID: *{it['retailer_id']}* | *{it['fmt_date']}({it['sla_days']})* | {it['city']} - {it['ward']}")
            if len(items_list) > 5:
                part_staff_lines.append(f"  _... và {len(items_list)-5} data trễ SLA khác_")
            part_staff_lines.append("")

        region_groups = {}
        for item in all_region_sla:
            reg_name = item['source']
            if reg_name not in region_groups: region_groups[reg_name] = []
            region_groups[reg_name].append(item)

        sorted_regions = sorted(region_groups.items(), key=lambda x: len(x[1]), reverse=True)

        part_region_lines = []
        for reg_name, items_list in sorted_regions:
            items_list.sort(key=lambda x: x['sla_days'], reverse=True)
            part_region_lines.append(f"📍 *{reg_name}* (trễ *{len(items_list)}* data chưa chia):")
            for it in items_list[:5]:
                part_region_lines.append(f"  • Retailer ID: *{it['retailer_id']}* | *{it['fmt_date']}({it['sla_days']})* | {it['city']} - {it['ward']} | {it['owner']}")
            if len(items_list) > 5:
                part_region_lines.append(f"  _... và {len(items_list)-5} data trễ SLA chưa chia khác_")
            part_region_lines.append("")

        header_text = (
            f"🚨 *BÁO CÁO CẢNH BÁO SLA (DỮ LIỆU TẠO >= 10 NGÀY)*\n"
            f"⏰ *Thời gian quét*: {time.strftime('%H:%M:%S %d/%m/%Y')}\n"
            f"👥 *Coacher*: *Ái Quốc*\n\n"
            f"📊 *TỔNG QUAN:*\n"
            f"• Data trễ SLA Nhân sự đang giữ: *{total_staff_count}* data\n"
            f"• Data trễ SLA Khu vực chưa chia: *{total_region_count}* data\n"
            f"🔥 *TỔNG CỘNG TRỄ SLA >= 10 NGÀY: {grand_total_sla} data*\n\n"
        )

        full_text = header_text
        if part_staff_lines:
            full_text += "💼 *I. CÁC CÁ NHÂN ĐANG GIỮ DATA TRỄ SLA:*\n" + "\n".join(part_staff_lines) + "\n"
        if part_region_lines:
            full_text += "📍 *II. KHU VỰC CÒN DATA TRỄ SLA CHƯA CHIA:*\n" + "\n".join(part_region_lines) + "\n"

        if grand_total_sla == 0:
            full_text += "🎉 _Hiện tại không có data nào bị trễ SLA >= 10 ngày!_"
        elif tagged_users:
            full_text += "⚡ _Nhờ các bạn được tag đích danh ở trên chủ động kiểm tra và hoàn thành sớm các data trễ SLA nhé!_\n"

        def send_chunk(text_chunk):
            payload = {"text": text_chunk}
            req = urllib.request.Request(
                gchat_webhook,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=UTF-8'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.getcode() == 200

        try:
            if len(full_text) > 4000:
                mid = full_text[:4000].rfind('\n\n')
                if mid == -1: mid = 3900
                send_chunk(full_text[:mid])
                send_chunk(full_text[mid:])
            else:
                send_chunk(full_text)
            return True, "Đã gửi báo cáo SLA lên Google Chat thành công."
        except Exception as e:
            return False, f"Lỗi gửi Google Chat: {e}"

    def send_auto_assign_notification(report_text):
        # 1. Gửi lên Google Chat
        gchat_webhook = config.get("gchat_webhook")
        if gchat_webhook:
            try:
                req = urllib.request.Request(
                    gchat_webhook,
                    data=json.dumps({"text": report_text}).encode('utf-8'),
                    headers={'Content-Type': 'application/json; charset=UTF-8'}
                )
                urllib.request.urlopen(req, timeout=10)
            except Exception as e:
                print(f"⚠️ [AutoAssign] Lỗi gửi Google Chat: {e}", flush=True)

        # 2. Gửi về Telegram nếu có chat_id đã lưu
        last_chat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_chat_id.txt")
        if os.path.exists(last_chat_file):
            try:
                with open(last_chat_file, "r", encoding="utf-8") as f:
                    saved_chat_id = f.read().strip()
                if saved_chat_id:
                    bot.send_message(saved_chat_id, report_text, parse_mode="Markdown")
            except Exception as e:
                print(f"⚠️ [AutoAssign] Lỗi gửi Telegram tự động: {e}", flush=True)

    def daily_report_scheduler():
        reported_today_18h = None
        reported_today_07h = None
        reported_today_20h = None
        auto_assigned_today_06h30 = None
        auto_assigned_today_20h30 = None
        auto_sheet_updated_today_21h = None
        while True:
            try:
                now_str = time.strftime("%H:%M")
                today_str = time.strftime("%Y-%m-%d")
                
                # 07:00 AM SLA Report
                if now_str == "07:00" and reported_today_07h != today_str:
                    print(f"⏰ [Scheduler] Đã đến 07:00 ({today_str}), bắt đầu tự động gửi báo cáo SLA lên Google Chat...")
                    success, res_msg = send_sla_gchat_report()
                    if success:
                        reported_today_07h = today_str
                        print(f"🎉 [Scheduler] Báo cáo SLA 07:00 ngày {today_str} đã gửi Google Chat thành công!")

                # 06:30 AM Auto-assign (< 10 ATC treo -> Đẩy thêm 8 data)
                if now_str == "06:30" and auto_assigned_today_06h30 != today_str:
                    print(f"⏰ [Scheduler] Đã đến 06:30 ({today_str}), bắt đầu tự động quét & chia data (< 10 ATC)...")
                    auto_assigned_today_06h30 = today_str
                    import quick_action
                    success, r_msg, _ = quick_action.do_auto_assign_under_10(batch_size=8, threshold=10, dry_run=False)
                    send_auto_assign_notification(r_msg)
                    print(f"🎉 [Scheduler] Đã hoàn thành tự động chia data 06:30 sáng ngày {today_str}!")

                # 18:00 PM Daily Report
                if now_str == "18:00" and reported_today_18h != today_str:
                    print(f"⏰ [Scheduler] Đã đến 18:00 ({today_str}), bắt đầu tự động bắn báo cáo lên Google Chat...")
                    success, res_msg = send_google_chat_report()
                    if success:
                        reported_today_18h = today_str
                        print(f"🎉 [Scheduler] Báo cáo 18:00 ngày {today_str} đã gửi Google Chat thành công!")

                # 20:00 PM Ticket Treo Report (tag đích danh)
                if now_str == "20:00" and reported_today_20h != today_str:
                    print(f"⏰ [Scheduler] Đã đến 20:00 ({today_str}), bắt đầu tự động bắn báo cáo Ticket treo lên Google Chat...")
                    import quick_action
                    success, res_msg = quick_action.do_send_ticket_gchat()
                    if success:
                        reported_today_20h = today_str
                        print(f"🎉 [Scheduler] Báo cáo Ticket treo 20:00 ngày {today_str} đã gửi Google Chat thành công!")
                    else:
                        print(f"❌ [Scheduler] Báo cáo Ticket treo 20:00 thất bại: {res_msg}")

                # 20:30 PM Auto-assign (< 10 ATC treo -> Đẩy thêm 8 data)
                if now_str == "20:30" and auto_assigned_today_20h30 != today_str:
                    print(f"⏰ [Scheduler] Đã đến 20:30 ({today_str}), bắt đầu tự động quét & chia data (< 10 ATC)...")
                    auto_assigned_today_20h30 = today_str
                    import quick_action
                    success, r_msg, _ = quick_action.do_auto_assign_under_10(batch_size=8, threshold=10, dry_run=False)
                    send_auto_assign_notification(r_msg)
                    print(f"🎉 [Scheduler] Đã hoàn thành tự động chia data 20:30 tối ngày {today_str}!")

                # 21:00 PM Auto-update Google Sheet Miền Nam (Sau khi auto-assign 20h30 xong)
                if now_str == "21:00" and auto_sheet_updated_today_21h != today_str:
                    print(f"⏰ [Scheduler] Đã đến 21:00 ({today_str}), bắt đầu tự động cập nhật Google Sheet Miền Nam...")
                    auto_sheet_updated_today_21h = today_str
                    try:
                        import auto_sheet_updater
                        saved_chat_id = None
                        last_chat_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_chat_id.txt")
                        if os.path.exists(last_chat_file):
                            try:
                                with open(last_chat_file, "r", encoding="utf-8") as f:
                                    saved_chat_id = f.read().strip()
                            except: pass
                        success, res_msg = auto_sheet_updater.run_auto_update_hcm_sheet(bot=bot, chat_id=saved_chat_id)
                        if success:
                            print(f"🎉 [Scheduler] Đã tự động cập nhật Google Sheet 21:00 ngày {today_str} thành công!")
                        else:
                            print(f"❌ [Scheduler] Cập nhật Google Sheet 21:00 thất bại: {res_msg}")
                    except Exception as e:
                        print(f"❌ [Scheduler] Lỗi cập nhật Google Sheet 21:00: {e}")
            except Exception as e:
                print(f"❌ [Scheduler] Lỗi trong scheduler: {e}")
            time.sleep(30)

    threading.Thread(target=daily_report_scheduler, daemon=True).start()
    print("⏰ Đã kích hoạt bộ đếm thời gian gửi báo cáo tự động (06h30 Chia data, 07h00 SLA, 18h00 Báo cáo ngày, 20h00 Ticket treo, 20h30 Chia data & 21h00 Update Sheet).")

    def crm_keep_alive_daemon():
        time.sleep(10)
        while True:
            try:
                cookie_str, csrf_token = get_session()
                if not cookie_str or not check_cookie_valid(cookie_str):
                    print("🔄 [Keep-Alive] Phiên CRM hết hạn, đang tự động đăng nhập ngầm làm mới...")
                    acquire_session_via_selenium(viewname="16309", update_status=None, allow_gui_fallback=True)
                else:
                    print("💚 [Keep-Alive] CRM session active & healthy.")
            except Exception as e:
                print(f"⚠️ [Keep-Alive] Lỗi kiểm tra phiên CRM: {e}")
            time.sleep(300)

    threading.Thread(target=crm_keep_alive_daemon, daemon=True).start()
    print("💚 Đã kích hoạt luồng tự động nuôi phiên CRM 24/7 (Keep-Alive Heartbeat).")

    # Kích hoạt luồng quét tự động Ticket Tái Ký SC Group mỗi 3 phút bắn Google Chat
    try:
        import sc_renew_monitor
        threading.Thread(target=sc_renew_monitor.sc_renew_monitor_loop, args=(180,), daemon=True).start()
        print("🔔 Đã kích hoạt luồng tự động quét Ticket Tái Ký SC Group mỗi 3 phút bắn Google Chat.")
    except Exception as me:
        print(f"⚠️ [SC Renew Monitor] Lỗi kích hoạt luồng: {me}")

    print("Bot đang chạy và lắng nghe tin nhắn...")
    while True:
        try:
            if hasattr(bot, '_TeleBot__stop_polling'):
                bot._TeleBot__stop_polling.clear()
            bot.infinity_polling(timeout=30, long_polling_timeout=20, restart_on_change=False)
        except Exception as e:
            print(f"⚠️ [Telegram Polling] Mạng gián đoạn hoặc gặp lỗi: {e}. Đang tự động kết nối lại sau 3s...", flush=True)
            time.sleep(3)
        except BaseException as be:
            if isinstance(be, (KeyboardInterrupt, SystemExit)):
                print(f"🛑 [Telegram Polling] Nhận lệnh dừng tiến trình: {be}", flush=True)
                break
            print(f"⚠️ [Telegram Polling] Ngoại lệ hệ thống: {be}. Đang tự động kết nối lại sau 3s...", flush=True)
            time.sleep(3)
