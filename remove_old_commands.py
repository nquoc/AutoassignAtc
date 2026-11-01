import sys

def run():
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove @bot.message_handler(commands=['all']) block
    all_cmd_block = """@bot.message_handler(commands=['all'])
def handle_all_command(message):
    scan_msg = bot.reply_to(
        message,
        "⏳ **Đang quét dữ liệu toàn bộ các khu vực, vui lòng chờ...**",
        parse_mode="Markdown"
    )
    threading.Thread(
        target=process_scan_all_callback,
        args=(message.chat.id, scan_msg.message_id),
        daemon=True
    ).start()

"""
    content = content.replace(all_cmd_block, "")

    # 2. Remove "ds" fallback
    ds_fallback = """    if text.lower() in ["ds", "danh sach", "khu vuc", "khuvuc", "/ds", "/regions"]:
        markup = get_regions_markup()
        bot.reply_to(
            message, 
            "📍 **Danh sách các khu vực hiện tại:**\\nChọn một khu vực bên dưới để bắt đầu:", 
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
        
"""
    content = content.replace(ds_fallback, "")

    # 3. Remove "all" fallback
    all_fallback = """    if text.lower() in ["all", "scanall", "scan all", "quetall", "quet all", "/all", "/scanall"]:
        scan_msg = bot.reply_to(
            message,
            "⏳ **Đang quét dữ liệu toàn bộ các khu vực, vui lòng chờ...**",
            parse_mode="Markdown"
        )
        threading.Thread(
            target=process_scan_all_callback,
            args=(message.chat.id, scan_msg.message_id),
            daemon=True
        ).start()
        return
        
"""
    content = content.replace(all_fallback, "")

    with open('bot.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Cleaned up old commands.")

if __name__ == "__main__":
    run()
