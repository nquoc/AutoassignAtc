#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
KIOTVIET CRM - LOCAL DASHBOARD WEB SERVER
=============================================================================
Web Server nội bộ siêu nhẹ dùng thư viện chuẩn Python (không cần cài thêm framework).
Kết nối Google Sheets qua credentials.json và cung cấp API phân tích nhân sự thời gian thực.
=============================================================================
"""

import os
import sys
import re
import json
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import Counter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(CURRENT_DIR, "credentials.json")
if not os.path.exists(CREDENTIALS_FILE):
    CREDENTIALS_FILE = os.path.join(os.path.dirname(CURRENT_DIR), "credentials.json")

SPREADSHEET_ID = "1DLBiD2kPO6Piw0kapG5W3quIEdc0XdVhRON4F8sxsi0"

def get_live_data_from_sheet(target_gid=1647379928):
    """
    Kéo dữ liệu trực tiếp từ Google Sheet và tổng hợp số lượng dòng theo nhân sự.
    """
    try:
        import gspread
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.get_worksheet_by_id(int(target_gid))
        if not ws:
            ws = sh.worksheet("tudaunam")

        headers = ws.row_values(1)
        rows = ws.get_all_values()[1:]

        col_staff = headers.index('Người xử lý') if 'Người xử lý' in headers else -1
        if col_staff == -1:
            return {"error": "Không tìm thấy cột 'Người xử lý'"}

        col_status = headers.index('Tình trạng xử lý') if 'Tình trạng xử lý' in headers else -1
        col_impact = headers.index('impact') if 'impact' in headers else -1

        staff_counts = Counter()
        staff_done = Counter()
        staff_impact = Counter()

        total_rows = 0
        for r in rows:
            if len(r) > col_staff and r[col_staff].strip():
                name = r[col_staff].strip()
                staff_counts[name] += 1
                total_rows += 1
                if col_status != -1 and len(r) > col_status and 'đã làm' in r[col_status].lower():
                    staff_done[name] += 1
                if col_impact != -1 and len(r) > col_impact and str(r[col_impact]).strip() in ['1', '1.0']:
                    staff_impact[name] += 1

        result = []
        for rank, (name, count) in enumerate(staff_counts.most_common(), 1):
            result.append({
                'rank': rank,
                'name': name,
                'count': count,
                'percentage': round((count / total_rows) * 100, 2) if total_rows > 0 else 0,
                'done': staff_done.get(name, 0),
                'impact': staff_impact.get(name, 0)
            })

        return {
            'sheet_title': sh.title,
            'tab_name': ws.title,
            'gid': target_gid,
            'total_rows': total_rows,
            'total_staff': len(staff_counts),
            'staff_data': result
        }
    except Exception as e:
        print(f"❌ Lỗi đọc Google Sheet: {e}")
        # Đọc dữ liệu backup từ file dashboard_data.json nếu rớt mạng
        cache_file = os.path.join(CURRENT_DIR, "dashboard_data.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"error": str(e)}

def update_dashboard_html_cache(data=None):
    """
    Cập nhật dữ liệu mới nhất vào dashboard_data.json và file dashboard.html
    giúp người dùng khi mở offline vẫn có dữ liệu mới nhất từ lần đồng bộ trước.
    """
    if not data:
        data = get_live_data_from_sheet(1647379928)
    if not data or data.get("error"):
        return False

    # 1. Lưu vào dashboard_data.json
    paths = [
        os.path.join(CURRENT_DIR, "dashboard_data.json"),
        os.path.join(os.path.dirname(CURRENT_DIR), "dashboard_data.json")
    ]
    for p in paths:
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # 2. Cập nhật INITIAL_DATA trong dashboard.html
    html_paths = [
        os.path.join(CURRENT_DIR, "dashboard.html"),
        os.path.join(os.path.dirname(CURRENT_DIR), "dashboard.html")
    ]
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    for hp in html_paths:
        if os.path.exists(hp):
            try:
                with open(hp, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = re.sub(
                    r'const INITIAL_DATA = \{.*?\};\n\n',
                    f'const INITIAL_DATA = {json_str};\n\n',
                    content,
                    flags=re.DOTALL
                )
                with open(hp, "w", encoding="utf-8") as f:
                    f.write(new_content)
            except Exception:
                pass

    return True

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html", "/dashboard.html"]:
            html_file = os.path.join(CURRENT_DIR, "dashboard", "index.html")
            if not os.path.exists(html_file):
                html_file = os.path.join(CURRENT_DIR, "dashboard.html")
            if os.path.exists(html_file):
                with open(html_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "dashboard/index.html not found")

        elif path == "/api/data":
            qs = urllib.parse.parse_qs(parsed.query)
            gid = qs.get("gid", [1647379928])[0]
            data = get_live_data_from_sheet(target_gid=gid)

            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        else:
            # Phục vụ các file tĩnh trong thư mục dashboard/ (css, js, ...)
            clean_path = path.lstrip("/\\")
            static_file = os.path.join(CURRENT_DIR, "dashboard", clean_path)
            if not os.path.exists(static_file):
                static_file = os.path.join(CURRENT_DIR, clean_path)

            if os.path.exists(static_file) and os.path.isfile(static_file):
                content_type = "text/plain"
                if static_file.endswith(".css"):
                    content_type = "text/css; charset=utf-8"
                elif static_file.endswith(".js"):
                    content_type = "application/javascript; charset=utf-8"
                elif static_file.endswith(".html"):
                    content_type = "text/html; charset=utf-8"
                elif static_file.endswith(".json"):
                    content_type = "application/json; charset=utf-8"

                with open(static_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, f"File not found: {path}")

    def log_message(self, format, *args):
        # Rút ngắn nhật ký console
        print(f"🌐 [Web Request] {self.address_string()} - {args[0]}")

def main():
    port = 5050
    server_address = ('', port)
    httpd = HTTPServer(server_address, DashboardHandler)
    url = f"http://localhost:{port}"

    print("=" * 70)
    print(f"🚀 KIOTVIET CRM - DASHBOARD SERVER ĐÃ SẴN SÀNG!")
    print(f"👉 Địa chỉ Web: {url}")
    print(f"👉 Nhấn Ctrl + C để dừng server.")
    print("=" * 70)

    # Mở trình duyệt web tự động
    try:
        webbrowser.open(url)
    except:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Đã tắt Web Server.")

if __name__ == "__main__":
    main()
