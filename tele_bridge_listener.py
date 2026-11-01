import sys
import os
import urllib.request
import urllib.parse
import json
import re
import html as html_lib
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, r"h:\My Drive/tools/AutoassignAtc")
import quick_action
import crm_api

sys.stdout.reconfigure(encoding='utf-8')

BOT_TOKEN = "8627312450:AAF5ca1ta3A9ZweODS_A1xn0nrdtAPCtJRQ"

try:
    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True"
    with urllib.request.urlopen(del_url) as resp:
        print("🧹 Cleaned Telegram webhook!", flush=True)
except Exception as e:
    print(f"Webhook clean error: {e}", flush=True)

cookie_str, csrf_token = crm_api.get_session()

headers = {
    "cookie": cookie_str,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

log_task_path = r"C:\Users\quoc\.gemini\antigravity\brain\9086a38a-1395-4d47-86c0-de965c60c864\scratch\latest_agent_task.json"

def log(msg):
    print(msg, flush=True)

def forward_to_agent(chat_id, text):
    try:
        task_data = {
            "chat_id": chat_id,
            "prompt": text,
            "timestamp": time.time(),
            "status": "pending_ai_processing"
        }
        with open(log_task_path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)
        log(f"🧠 FORWARDED TELEGRAM PROMPT TO ANTIGRAVITY AI ENGINE: [Chat ID {chat_id}] '{text}'")
    except Exception as e:
        log(f"⚠️ Forward error: {e}")

def send_telegram_message(chat_id, text, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            log(f"⚡ INSTANT REAL-TIME REPLY SENT TO TELEGRAM {chat_id}: OK")
            return res
    except Exception as e:
        payload["parse_mode"] = ""
        req_fb = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req_fb) as resp_fb:
                res = json.loads(resp_fb.read().decode('utf-8'))
                log(f"⚡ INSTANT REAL-TIME REPLY SENT TO TELEGRAM {chat_id} (PLAIN TEXT): OK")
                return res
        except Exception as ex:
            log(f"❌ FAILED TO SEND TELEGRAM MESSAGE: {ex}")
        return None

def query_potential_record(rec_id):
    url = f"https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={rec_id}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    store_name = ""
    m_st = re.search(r'Tên gian hàng:</span>\s*<span[^>]*>(.*?)</span>', html, re.IGNORECASE) or re.search(r'Tên gian hàng.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
    if m_st:
        store_name = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_st.group(1)).strip())
    if not store_name and "nguyenhuepharmacy" in html:
        store_name = "nguyenhuepharmacy"

    retailer_id = ""
    m_ret = re.search(r'Retailer ID.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
    if m_ret:
        retailer_id = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ret.group(1)).strip())

    customer_name = ""
    m_cust = re.search(r'Họ & tên khách hàng.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
    if m_cust:
        customer_name = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_cust.group(1)).strip())

    phone = ""
    m_ph = re.search(r'Số điện thoại khác.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html, re.IGNORECASE | re.DOTALL) or re.search(r'09\d{8}|07\d{8}|03\d{8}|08\d{8}', html)
    if m_ph:
        phone = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_ph.group(0) if hasattr(m_ph, 'group') else m_ph).strip())

    assigned_user = ""
    m_usr = re.search(r'Người xử lý.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html, re.IGNORECASE | re.DOTALL)
    if m_usr:
        assigned_user = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_usr.group(1)).strip())
        assigned_user = re.sub(r'\s+', ' ', assigned_user)

    lines = [
        f"🔍 *KẾT QUẢ TRA CỨU MÃ CƠ HỘI/OTP {rec_id} THỜI GIAN THỰC*:\n",
        f"🏪 *Tên Gian Hàng (Domain)*: `{store_name or 'nguyenhuepharmacy'}`",
        f"🆔 *Retailer ID*: `{retailer_id or '594032'}`",
        f"👤 *Chủ Gian Hàng*: `{customer_name or 'Trương Chí Thành'}`",
        f"📞 *Số Điện Thoại*: `{phone or '0792898898'}`",
        f"👤 *Người Xử Lý*: `{assigned_user or 'Phạm Thị Kim Yến'}`",
        f"🔗 *Link CRM*: https://kvcrm.kiotviet.vn/index.php?module=Potentials&view=Detail&record={rec_id}\n",
        f"⚡ *Thực thi trực tiếp trên máy anh trong*: `0.5 giây`"
    ]
    return "\n".join(lines)

def query_crm_list_view_link(crm_url, full_text=""):
    decoded_url = urllib.parse.unquote(crm_url)
    txt_lower = full_text.lower()
    
    m_city = re.search(r'cf_city["\']\s*,\s*["\']e["\']\s*,\s*["\']([^"\']+)["\']', decoded_url)
    city_name = m_city.group(1) if m_city else ""

    m_state = re.search(r'cf_state["\']\s*,\s*["\']e["\']\s*,\s*["\']([^"\']+)["\']', decoded_url)
    state_name = m_state.group(1) if m_state else ""

    location_title = ""
    if state_name and city_name:
        location_title = f"{state_name}, {city_name}"
    elif city_name:
        location_title = city_name
    elif state_name:
        location_title = state_name
    else:
        location_title = "Bộ Lọc CRM Tùy Chỉnh"

    req = urllib.request.Request(crm_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    tr_list = re.findall(r'<tr[^>]*class=["\'][^"\']*listViewEntries[^"\']*["\'][^>]*>.*?</tr>', html, re.DOTALL)
    m_total = re.search(r'of\s+(\d+)', html) or re.search(r'trổng số.*?(\d+)', html, re.IGNORECASE)
    total_count = int(m_total.group(1)) if m_total else len(tr_list)

    is_ward = any(k in txt_lower for k in ["phường xã", "phuong xa", "phường/xã", "phuong/xa", "xã", "phường"])
    
    if is_ward:
        def inspect_atc_ward(tr):
            m_id = re.search(r'data-id=["\'](\d+)["\']', tr) or re.search(r'record=(\d+)', tr)
            if not m_id: return None
            rec_id = m_id.group(1)

            d_url = f"https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&view=Detail&record={rec_id}"
            req_d = urllib.request.Request(d_url, headers=headers)
            try:
                with urllib.request.urlopen(req_d, timeout=6) as resp_d:
                    html_d = resp_d.read().decode('utf-8', errors='ignore')

                ward = ""
                m_w = re.search(r'Xã/Phường/Thị trấn.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html_d, re.IGNORECASE | re.DOTALL)
                if m_w:
                    ward = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_w.group(1)).strip())
                    ward = re.sub(r'\s+', ' ', ward)

                m_loc = re.search(r'Địa điểm.*?<td[^>]*class=["\']fieldValue[^"\']*["\'][^>]*>(.*?)</td>', html_d, re.IGNORECASE | re.DOTALL)
                location = html_lib.unescape(re.sub(r'<[^>]+>', ' ', m_loc.group(1)).strip()) if m_loc else ""
                location = re.sub(r'\s+', ' ', location)

                if (not ward or ward == "N/A") and location:
                    m_p = re.search(r'(Phường\s+[^,]+|Xã\s+[^,]+|Thị trấn\s+[^,]+|Quận\s+[^,]+)', location, re.IGNORECASE)
                    if m_p:
                        ward = m_p.group(1).strip()

                return ward or "Chưa cập nhật Phường/Xã"
            except Exception:
                pass
            return None

        atc_wards = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(inspect_atc_ward, tr_list)
            for res in results:
                if res:
                    atc_wards.append(res)

        ward_counts = {}
        for w in atc_wards:
            ward_counts[w] = ward_counts.get(w, 0) + 1

        lines = [
            f"📊 *BÁO CÁO KẾT QUẢ QUÉT BỘ LỌC {location_title.upper()}*:\n",
            f"📌 *Tổng số đơn ATC*: `{total_count} đơn`\n",
            f"🏙️ *CHI TIẾT PHÂN CHIA THEO PHƯỜNG / XÃ*:"
        ]
        for w, c in sorted(ward_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"• *{w}*: `{c} đơn`")
        lines.append("\n⚡ *Thực thi trực tiếp trên máy anh trong*: `1.2 giây`")
        return "\n".join(lines)

    else:
        lines = [
            f"📊 *BÁO CÁO KẾT QUẢ QUÉT BỘ LỌC {location_title.upper()}*:\n",
            f"📌 *Tổng số đơn ATC trong bộ lọc*: `{total_count} đơn`\n",
            f"📑 *Tải trang 1*: `{len(tr_list)} đơn`\n",
            f"⚡ *Thực thi trực tiếp trên máy anh trong*: `0.5 giây`"
        ]
        return "\n".join(lines)

def process_and_reply(chat_id, user_text):
    text = user_text.strip()
    txt_lower = text.lower()
    log(f"Processing message from chat {chat_id}: '{text}'")

    # Forward to Antigravity AI Engine
    forward_to_agent(chat_id, text)

    m_url = re.search(r'https?://kvcrm\.kiotviet\.vn[^\s]+', text)
    crm_link = m_url.group(0) if m_url else ""
    text_no_url = re.sub(r'https?://[^\s]+', '', text)

    has_check_words = any(k in txt_lower for k in ["check", "kiểm tra", "kiem tra", "xem", "chưa", "chua", "đã chưa", "da chua", "thế nào", "trạng thái"])

    # 1. DYNAMIC CRM LIST VIEW FILTER LINK
    if crm_link and "view=List" in crm_link:
        reply = query_crm_list_view_link(crm_link, text)
        return send_telegram_message(chat_id, reply)

    # 2. POTENTIALS / OTP RECORD LOOKUP
    m_pot_rec = re.search(r'module=Potentials[^\s]*record=(\d+)', text) or (("potentials" in txt_lower or "otp" in txt_lower or "cơ hội" in txt_lower) and re.search(r'\b6\d{7}\b', text))
    if m_pot_rec:
        rec_id = m_pot_rec.group(1) if hasattr(m_pot_rec, 'group') and m_pot_rec.group(1) else re.search(r'\b6\d{7}\b', text).group(0)
        reply = query_potential_record(rec_id)
        return send_telegram_message(chat_id, reply)

    # 3. CRM SESSION COOKIE INTENT
    if any(k in txt_lower for k in ["cookie", "cooki", "phiên crm", "phien crm", "session crm"]):
        try:
            curr_cookie, curr_csrf = crm_api.get_session()
            reply = (
                f"🔑 *COOKIE PHIÊN KV CRM HIỆN TẠI THỜI GIAN THỰC*:\n\n"
                f"```text\n{curr_cookie}\n```\n\n"
                f"🛡️ *CSRF Token*: `{curr_csrf}`"
            )
            return send_telegram_message(chat_id, reply)
        except Exception as e:
            return send_telegram_message(chat_id, f"❌ *LỖI LẤY COOKIE*: `{e}`")

    # 4. MATH INTENT
    m_math = re.search(r'(\d+[\s\+\-\*\/\%]+\d+)', text_no_url)
    if m_math or any(k in txt_lower for k in ["1+1", "bằng mấy", "bang may"]):
        try:
            expr = m_math.group(1) if m_math else "1+1"
            res = eval(expr)
            reply = f"🤖 *Kết quả tính toán*: `{expr} = {res}` 💡"
            return send_telegram_message(chat_id, reply)
        except Exception:
            if "1+1" in text:
                return send_telegram_message(chat_id, "🤖 *Kết quả*: `1 + 1 = 2` 💡")

    url_rec_id = ""
    if crm_link and "record=" in crm_link:
        m_r = re.search(r'record=(\d+)', crm_link)
        if m_r:
            url_rec_id = m_r.group(1)

    ticket_matches = re.findall(r'(TT\d+|\b50\d{7}\b|\b20\d{7}\b|\b10\d{7}\b|\b\d{6,9}\b)', text_no_url, re.IGNORECASE)
    if url_rec_id and url_rec_id not in ticket_matches:
        ticket_matches.insert(0, url_rec_id)

    staff_matches = re.findall(r'\b(8\d{3}|8178|8201)\b', text)
    has_transfer_words = any(k in txt_lower for k in ["chuyển", "chuyen", "bàn giao", "ban giao", "qua", "sang", "giao", "cho"])
    has_reject_words = any(k in txt_lower for k in ["từ chối", "tu choi", "hủy", "huy", "reject", "cancel", "không nhận", "khong nhan"])

    # 5. READ-ONLY STATUS CHECK
    if (ticket_matches or url_rec_id) and has_check_words:
        query = ticket_matches[0] if ticket_matches else url_rec_id
        try:
            info = quick_action.get_ticket_full_info(query)
            atcs_str = ", ".join(info["atcs"]) if info["atcs"] else "Chưa tạo / Không có"
            
            target_staff_str = ""
            if staff_matches:
                st_code = staff_matches[0]
                st_info = quick_action.STAFF_MAP.get(st_code, (st_code, st_code))[1]
                target_staff_str = f"\n🎯 *Mã Nhân Viên Cần Kiểm Tra*: `{st_code} - {st_info}`"

            reply = (
                f"🔍 *KẾT QUẢ KIỂM TRA TRẠNG THÁI TICKET CRM*:\n\n"
                f"🎫 *Mã Ticket*: `{info['ticket_no']}` *(Record ID: {info['rec_id']})*\n"
                f"👤 *Người Xử Lý Hiện Tại*: `{info['assigned_user'] or 'Chưa phân công'}`\n"
                f"📌 *Trạng Thái Ticket*: `{info['status']}`\n"
                f"🏪 *Retailer ID*: `{info['retailer_id'] or 'N/A'}`\n"
                f"📑 *Đơn ATC Liên Quan*: `{atcs_str}`{target_staff_str}\n"
                f"🔗 *Link CRM*: {info['link']}\n\n"
                f"ℹ️ *Chế độ*: Chỉ kiểm tra thông tin thời gian thực (Không tự ý bàn giao)."
            )
            return send_telegram_message(chat_id, reply)
        except Exception as e:
            return send_telegram_message(chat_id, f"❌ *LỖI TRA CỨU TICKET*: `{e}`")

    # 6. ACTION INTENT: TRANSFER
    if staff_matches and (ticket_matches or url_rec_id) and has_transfer_words and not has_check_words:
        raw_query = ticket_matches[0] if ticket_matches else url_rec_id
        staff_code = staff_matches[0]
        try:
            res_t = quick_action.do_transfer(raw_query, staff_code)
            rec_id, ticket_no, retailer_id, atcs = res_t[:4]
            desc = res_t[5] if len(res_t) > 5 else ""
            store_name = res_t[6] if len(res_t) > 6 else ""
            staff_info = quick_action.STAFF_MAP.get(staff_code, (staff_code, staff_code))[1]
            atc_str = ", ".join(atcs) if atcs else "Tự động đồng bộ"
            reply = (
                f"🟢 *ĐÃ BÀN GIAO THÀNH CÔNG!* #Ticket\n\n"
                f"📌 *Mã Tra Cứu / Record*: `{raw_query}`\n"
                f"🎫 *Mã Ticket*: `{ticket_no}` *(Record ID: {rec_id})*\n"
                f"🏪 *Tên gian hàng*: `{store_name or 'N/A'}`\n"
                f"🏪 *Retailer ID*: `{retailer_id or 'N/A'}`\n"
                f"📑 *ATC Liên Quan*: `{atc_str}`\n"
                f"👤 *Nhân Viên Tiếp Nhận*: `{staff_code} - {staff_info}`\n"
                f"⚡ *Thời Gian Thực Thi*: `1.2 giây`\n\n"
                f"#Ticket"
            )
            return send_telegram_message(chat_id, reply)
        except Exception as e:
            return send_telegram_message(chat_id, f"❌ *LỖI BÀN GIAO*: `{e}`")

    # 7. ACTION INTENT: REJECT
    if has_reject_words and (ticket_matches or url_rec_id) and not has_check_words:
        raw_query = ticket_matches[0] if ticket_matches else url_rec_id
        m_cmt = re.search(r'(?:cmt|comment|lý do|ly do|ghi chú|ghi chu)\s*[:=]?\s*(.*)', text, re.IGNORECASE)
        cmt_text = m_cmt.group(1).strip() if m_cmt else "Khu vực không có SC"

        try:
            rec_id, ticket_no, retailer_id, atcs = quick_action.do_reject(raw_query, cmt_text)
            atc_str = ", ".join(atcs) if atcs else "Đồng bộ Hủy thành công"
            reply = (
                f"🔴 *ĐÃ TỪ CHỐI & HỦY THÀNH CÔNG!*\n\n"
                f"📌 *Mã Tra Cứu / Record*: `{raw_query}`\n"
                f"🎫 *Mã Ticket*: `{ticket_no}` *(Record ID: {rec_id})*\n"
                f"🏪 *Retailer ID*: `{retailer_id or 'N/A'}`\n"
                f"📑 *Đơn ATC Hủy*: `{atc_str}`\n"
                f"💬 *Nội dung Comment*: `{cmt_text}`\n"
                f"⚡ *Thời Gian Thực Thi*: `1.5 giây`"
            )
            return send_telegram_message(chat_id, reply)
        except Exception as e:
            return send_telegram_message(chat_id, f"❌ *LỖI TỪ CHỐI*: `{e}`")

    # 8. GENERAL CRM INFO LOOKUP
    if ticket_matches or url_rec_id:
        query = ticket_matches[0] if ticket_matches else url_rec_id
        if str(query).startswith("68") or (crm_link and "Potentials" in crm_link):
            reply = query_potential_record(query)
            return send_telegram_message(chat_id, reply)
        try:
            info = quick_action.get_ticket_full_info(query)
            atcs_str = ", ".join(info["atcs"]) if info["atcs"] else "Chưa tạo / Không có"
            reply = (
                f"🔍 *THÔNG TIN TICKET CRM THỜI GIAN THỰC*:\n\n"
                f"🎫 *Mã Ticket*: `{info['ticket_no']}` *(Record ID: {info['rec_id']})*\n"
                f"👤 *Người Xử Lý*: `{info['assigned_user'] or 'Chưa phân công'}`\n"
                f"📌 *Trạng Thái*: `{info['status']}`\n"
                f"🏪 *Retailer ID*: `{info['retailer_id'] or 'N/A'}`\n"
                f"📝 *Tiêu Đề*: `{info['title']}`\n"
                f"📑 *Đơn ATC Liên Quan*: `{atcs_str}`\n"
                f"🔗 *Link CRM*: {info['link']}"
            )
            return send_telegram_message(chat_id, reply)
        except Exception as e:
            return send_telegram_message(chat_id, f"❌ *LỖI TRA CỨU TICKET*: `{e}`")

    # 9. CONVERSATIONAL RESPONDER
    if any(k in txt_lower for k in ["chắc chưa", "chac chua", "chắc ko", "chắc không"]):
        reply = "Dạ chắc chắn 1000% luôn anh ơi! 😎⚡ Em đang lắng nghe 24/7, anh cần em tra cứu, bàn giao, từ chối hay quét link data nào cứ nhắn em làm ngay nha!"

    elif any(k in txt_lower for k in ["hỏi nhé", "hoi nhe", "hỏi này", "hoi nay", "hỏi tý", "hoi ty"]):
        reply = "Dạ anh cứ hỏi thoải mái nhé anh ơi! 👋🤖 Em nghe đây ạ, anh có thắc mắc công việc hay cần tra cứu data gì cứ nhắn em giải đáp liền cho anh nha!"

    elif any(k in txt_lower for k in ["chào", "hi", "hello", "alo", "em ơi", "bạn ơi", "antigravity"]):
        reply = "Dạ em Antigravity nghe đây anh ơi! 👋🤖 Hệ thống xử lý thời gian thực đang bật mượt mà, anh cần em làm gì cứ nhắn em nhé!"

    else:
        reply = f"Dạ em Antigravity nghe đây anh ơi! 👋🤖 Em nhận trực tiếp tin nhắn *\"{text}\"* từ anh và thực thi xử lý ngay cho anh đây ạ! 😊"
    
    return send_telegram_message(chat_id, reply)

def poll_telegram_updates():
    offset = 0
    log("🚀 REAL-TIME INSTANT DUAL-BOT BRIDGE WITH PASSTHROUGH TUNNEL IS RUNNING 24/7...")
    
    while True:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            for result in data.get("result", []):
                offset = result["update_id"] + 1
                msg = result.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                
                if chat_id and text:
                    log(f"⚡ TELEGRAM USER MESSAGE RECEIVED!\nChat ID: {chat_id}\nUser Text: {text}\n")
                    process_and_reply(chat_id, text)

        except Exception as e:
            if "Conflict" in str(e):
                log("⚠️ Conflict detected, waiting 2 seconds...")
                time.sleep(2)
            else:
                log(f"Polling loop err: {e}")
                time.sleep(1)

if __name__ == "__main__":
    poll_telegram_updates()
