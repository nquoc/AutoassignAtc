import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

def add_check_atc():
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 1. Update get_regions_markup
    old_markup = '        markup.add(InlineKeyboardButton(text=f"📊 Quét tất cả của Coacher {coacher_name}", callback_data=f"scan_all:{coacher_key}"))'
    new_markup = '''        markup.add(InlineKeyboardButton(text=f"📊 Quét tất cả của Coacher {coacher_name}", callback_data=f"scan_all:{coacher_key}"))
        markup.add(InlineKeyboardButton(text="🔍 Check ATC Treo", callback_data=f"check_atc:{coacher_key}"))'''
    content = content.replace(old_markup, new_markup)
    
    # 2. Add process_check_atc_callback
    check_atc_func = '''
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
        
    report = "🔍 **BÁO CÁO ATC TREO CỦA NHÂN SỰ (COACHER QUỐC)**\\n\\n"
    for name, count in results:
        parts = name.split(" - ")
        short_name = f"{parts[0]} - {parts[1]}" if len(parts) >= 2 else name
        report += f"• **{short_name}**: `{count}` ATC\\n"
        
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

def process_scan_all_callback(chat_id, message_id, coacher_filter="all"):'''
    
    content = content.replace('def process_scan_all_callback(chat_id, message_id, coacher_filter="all"):', check_atc_func)
    
    # 3. Add callback handler
    handler_code = '''
    if data.startswith("scan_all"):'''
    
    new_handler = '''
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
        
    if data.startswith("scan_all"):'''
    content = content.replace(handler_code, new_handler)
    
    with open('bot.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Added check_atc feature.")

if __name__ == "__main__":
    add_check_atc()
