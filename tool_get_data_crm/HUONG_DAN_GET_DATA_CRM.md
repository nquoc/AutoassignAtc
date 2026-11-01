# 📖 TÀI LIỆU KỸ THUẬT: GET DỮ LIỆU TỪ BỘ LỌC KIOTVIET CRM RA EXCEL & GOOGLE SHEETS
*(Dành cho AI, Kỹ sư phần mềm và Lập trình viên xây dựng công cụ tự động hóa)*

---

## 📌 1. TỔNG QUAN KIẾN TRÚC & NGUYÊN LÝ HOẠT ĐỘNG

* **Nền tảng CRM**: KiotViet CRM được phát triển trên lõi **VTiger CRM Framework**.
* **Cơ chế xác thực (Authentication)**: 
  * CRM **không** dùng API Key / Bearer Token tĩnh độc lập.
  * Toàn bộ xác thực chạy bằng **Session Cookie** (`KVCRM_PHPSESSID`, `current_user`, `kv-session`...) được tạo ra sau khi người dùng đăng nhập tài khoản SSO KiotViet trên trình duyệt Chrome.
  * Đi kèm là **CSRF Token** (`__vtrftk` hoặc `csrfMagicToken`).
* **Cơ chế trích xuất dữ liệu (Export Engine)**:
  * Không cào HTML phân trang thủ công (bị giới hạn 20-50 dòng/trang và rất chậm).
  * Gọi trực tiếp vào **API `ExportData` ngầm** của CRM: Lấy **toàn bộ dữ liệu của bộ lọc (hàng nghìn dòng)** trong **1 đến 2 giây**, bảo toàn đúng các cột hiển thị trong View.
  * Chế độ hoạt động: **100% Read-Only**, không ghi đè, không sửa đổi hay active bất kỳ trạng thái nào trên CRM.

---

## 🧩 2. EXTENSION CHROME 1-CLICK LẤY COOKIE

Thư mục Extension đã được đóng gói sẵn tại:  
👉 **`h:\My Drive\tools\AutoassignAtc\chrome_extension_get_cookie\`**

### Cách cài đặt vào Chrome trên máy bất kỳ:
1. Mở Chrome, truy cập đường dẫn: `chrome://extensions/`
2. Bật công tắc **"Developer mode" (Chế độ cho nhà phát triển)** ở góc trên bên phải.
3. Bấm nút **"Load unpacked" (Tải tiện ích đã giải nén)**.
4. Chọn thư mục `chrome_extension_get_cookie`.
5. Đăng nhập vào `https://kvcrm.kiotviet.vn`, sau đó bấm vào icon Extension trên thanh công cụ và bấm nút **"Sao chép Cookie (1-Click)"**. Cookie sẽ nằm ngay trong Clipboard sẵn sàng để dán vào Tool.

---

## ⚙️ 3. ĐẶC TẢ KỸ THUẬT API EXPORTDATA CỦA CRM

### A. Phân tích Link bộ lọc CRM (URL Query Parameters)
Một đường link bộ lọc trên CRM có cấu trúc như sau:
```text
https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=17559&orderby=&sortorder=&search_params=%5B%5B%5B%22sc_source_data%22%2C%22e%22%2C%22Old+expand%22%5D%5D%5D
```

Khi tool nhận URL này, cần bóc tách các tham số bằng `urllib.parse.parse_qs`:
* `module`: Tên module CRM (Mặc định: `CSKHSC`, hoặc `HelpDesk`, `Potentials`, `Accounts`...).
* `viewname`: ID của bộ lọc tùy chỉnh (Ví dụ: `17559`, `16309`, `20322`...).
* `search_params`: JSON điều kiện lọc nâng cao (URL-encoded). Nếu không có thì là `'[[]]'`.
* `search_key`: Cột tìm kiếm nhanh (nếu có).
* `operator`: Toán tử so sánh (`e`, `c`, `s`...).
* `search_value`: Giá trị tìm kiếm.

---

### B. Bước 1: Lấy CSRF Token (`__vtrftk`)
Gửi một request `GET` đến trang Export của view tương ứng:
* **URL**:
  ```text
  GET https://kvcrm.kiotviet.vn/index.php?module={module}&view=Export&selected_ids=[]&excluded_ids=[]&viewname={viewname}&page=1&search_params=%5B%5B%5D%5D
  ```
* **Headers**:
  ```http
  Cookie: {COOKIE_STRING}
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
  ```
* **Regex bóc tách Token từ HTML trả về**:
  ```python
  import re
  csrf_token = ""
  m = (re.search(r'csrfMagicToken\s*=\s*["\']([^"\']+)["\']', html) or 
       re.search(r'name=["\']__vtrftk["\']\s+value=["\']([^"\']+)["\']', html) or 
       re.search(r'(sid:[a-zA-Z0-9,]+)', html))
  if m:
      csrf_token = m.group(1)
  ```

---

### C. Bước 2: Gửi POST Request `ExportData`
Gửi request `POST` mang đầy đủ thông tin bộ lọc:
* **URL**: `https://kvcrm.kiotviet.vn/index.php`
* **Method**: `POST`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded
  Cookie: {COOKIE_STRING}
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
  Origin: https://kvcrm.kiotviet.vn
  Referer: {FILTER_URL}
  ```
* **Form Data Payload** (Url-encoded):
  | Field | Value | Ghi chú |
  | :--- | :--- | :--- |
  | `__vtrftk` | `{csrf_token}` | Lấy từ Bước 1 |
  | `module` | `{module}` | Ví dụ: `CSKHSC` |
  | `source_module` | `{module}` | Ví dụ: `CSKHSC` |
  | `action` | `ExportData` | Action xuất dữ liệu |
  | `viewname` | `{viewname}` | ID bộ lọc (Ví dụ `17559`) |
  | `selected_ids` | `[]` | Trống = xuất tất cả |
  | `excluded_ids` | `[]` | Trống |
  | `mode` | `ExportAllData` | Xuất toàn bộ dòng của bộ lọc |
  | `page` | `1` | |
  | `search_key` | `{search_key}` | Trích xuất từ URL bộ lọc |
  | `operator` | `{operator}` | Trích xuất từ URL bộ lọc |
  | `search_value` | `{search_value}` | Trích xuất từ URL bộ lọc |
  | `search_params`| `{search_params}`| Trích xuất từ URL bộ lọc |
  | `phong_ban` | `""` | |

---

### D. Bước 3: Giải mã Dữ liệu trả về (Quan trọng)
* ⚠️ **Encoding UTF-16**: Dữ liệu phản hồi của KiotViet CRM là file dạng **Tab-Delimited (TSV)** được mã hóa bằng **`UTF-16`** (hoặc `UTF-8` tùy cấu hình).
* **Code xử lý chuẩn**:
  ```python
  import csv
  try:
      content_str = data_bytes.decode('utf-16')
  except Exception:
      content_str = data_bytes.decode('utf-8', errors='ignore')

  lines = content_str.splitlines()
  reader = csv.reader(lines, delimiter='\t')
  rows = list(reader)
  ```
* ⚠️ **Làm sạch công thức Excel của CRM**:
  CRM thường bọc ID trong công thức `=TEXT("0","500690073")`. Cần regex làm sạch:
  ```python
  import re
  def clean_cell(val):
      if isinstance(val, str):
          m = re.match(r'=TEXT\([^,]+,\s*"([^"]+)"\)', val.strip())
          if m:
              return m.group(1)
          if val.startswith('="') and val.endswith('"'):
              return val[2:-1]
      return val
  ```

---

## 💻 4. MÃ NGUỒN HOÀN CHỈNH: TOOL GET DATA CRM RA EXCEL & GOOGLE SHEETS

File mã nguồn độc lập đã được lưu sẵn tại:  
👉 **`h:\My Drive\tools\AutoassignAtc\crm_export_tool.py`**

### Cú pháp chạy cực nhanh từ dòng lệnh:
```bash
python crm_export_tool.py "<LINK_BỘ_LỌC>" [COOKIE] [TÊN_FILE_EXCEL.xlsx]
```
*(Nếu không nhập cookie, tool sẽ tự động đọc từ file `cookie.txt` hoặc yêu cầu dán cookie vào).*

### Code Python mẫu cho AI / Lập trình viên khác kế thừa:
```python
import sys, os, urllib.request, urllib.parse, re, csv
import openpyxl

def get_crm_data_to_excel(cookie_str, filter_url, output_excel="CRM_Export.xlsx"):
    # 1. Parse URL
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(filter_url).query)
    module = qs.get('module', ['CSKHSC'])[0]
    viewname = qs.get('viewname', ['16309'])[0]
    search_params = qs.get('search_params', ['[[]]'])[0]

    # 2. Get CSRF Token
    token_url = f"https://kvcrm.kiotviet.vn/index.php?module={module}&view=Export&viewname={viewname}&page=1"
    req_t = urllib.request.Request(token_url, headers={"cookie": cookie_str, "User-Agent": "Mozilla/5.0"})
    csrf_token = ""
    try:
        with urllib.request.urlopen(req_t, timeout=10) as r:
            h = r.read().decode('utf-8', errors='ignore')
        m = re.search(r'csrfMagicToken\s*=\s*["\']([^"\']+)["\']', h) or re.search(r'(sid:[a-zA-Z0-9,]+)', h)
        if m: csrf_token = m.group(1)
    except: pass

    # 3. Post ExportData
    post_data = urllib.parse.urlencode({
        "__vtrftk": csrf_token,
        "module": module,
        "source_module": module,
        "action": "ExportData",
        "viewname": viewname,
        "mode": "ExportAllData",
        "page": "1",
        "search_params": search_params
    }).encode('utf-8')

    req_p = urllib.request.Request("https://kvcrm.kiotviet.vn/index.php", data=post_data, headers={
        "content-type": "application/x-www-form-urlencoded",
        "cookie": cookie_str,
        "user-agent": "Mozilla/5.0"
    })

    with urllib.request.urlopen(req_p, timeout=30) as r:
        raw_bytes = r.read()

    try: text = raw_bytes.decode('utf-16')
    except: text = raw_bytes.decode('utf-8', errors='ignore')

    rows = list(csv.reader(text.splitlines(), delimiter='\t'))
    
    # 4. Save to Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append([re.sub(r'=TEXT\([^,]+,\s*"([^"]+)"\)', r'\1', c).strip() for c in r])
    wb.save(output_excel)
    print(f"✅ Đã xuất {len(rows)-1} dòng ra file {output_excel}")
```

---

## ☁️ 5. HƯỚNG DẪN TÍCH HỢP ĐẨY LÊN GOOGLE SHEETS

Để tự động đẩy mảng `rows` lên Google Sheet thay vì chỉ lưu Excel:

1. **Cài đặt thư viện**:
   ```bash
   pip install gspread oauth2client
   ```
2. **Thiết lập Service Account (1 lần duy nhất)**:
   * Tạo Service Account trên Google Cloud Console, tải file `credentials.json`.
   * Mở Google Sheet cần đẩy, bấm nút **Share (Chia sẻ)** và thêm email của Service Account (dạng `...@...iam.gserviceaccount.com`) quyền **Editor**.
3. **Mã nguồn đẩy data lên Google Sheets**:
   ```python
   import gspread

   def push_to_gsheet(rows, credentials_file, sheet_url, tab_name="Sheet1"):
       gc = gspread.service_account(filename=credentials_file)
       sh = gc.open_by_url(sheet_url)
       ws = sh.worksheet(tab_name)
       ws.clear()
       ws.update('A1', rows)
       print(f"🚀 Đã cập nhật thành công {len(rows)} dòng lên Google Sheet!")
   ```

---

## 🎯 6. CHECKLIST TỔNG KẾT CHO AI MỚI TIẾP NHẬN DỰ ÁN

Khi gặp một yêu cầu kiểu: *"Lấy data từ link CRM https://... ra file Excel hoặc GG Sheet"*:
1. **Lấy Cookie**: Dán cookie từ Extension Chrome hoặc đọc từ file `cookie.txt`.
2. **Gọi Tool**: Chạy trực tiếp `python crm_export_tool.py "<URL>"`.
3. **Kết quả**: File Excel tự sinh ra sau 1-2 giây với đầy đủ dữ liệu nguyên bản từ CRM.
