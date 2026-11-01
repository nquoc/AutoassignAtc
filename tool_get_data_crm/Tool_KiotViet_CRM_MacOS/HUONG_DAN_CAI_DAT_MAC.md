# 🍎 Hướng Dẫn Cài Đặt & Sử Dụng Tool KiotViet CRM Kéo Data Về Excel Trên macOS

> **Hỗ trợ đầy đủ**: MacBook Air / MacBook Pro chạy chip Apple Silicon (**M1, M2, M3, M4**) và MacBook / iMac chip **Intel** chạy macOS (Sonoma, Sequoia, Ventura, Monterey).

---

## 📋 Danh Sách Các Tệp Cần Thiết Cho macOS

Trong gói công cụ dành cho Mac, các tệp chính gồm có:

| Tệp / Thư mục | Chức năng |
| :--- | :--- |
| `Chay_Tool_Mac.command` | **Script 1-click khởi chạy giao diện Tool trên Mac** (nhấp đúp chuột để mở). |
| `Cai_Dat_Mac.command` | **Script 1-click tự động tạo môi trường ảo và cài đặt thư viện** (chỉ chạy 1 lần đầu). |
| `gui_crm_tool.py` | Giao diện đồ họa người dùng (CustomTkinter) quản lý danh sách bộ lọc CRM và tiến trình xuất dữ liệu. |
| `crm_export_tool.py` | Module lõi: gọi API CRM, giải mã dữ liệu, xuất file Excel (`.xlsx`) và đồng bộ Google Sheets. |
| `requirements.txt` | Danh sách thư viện Python tương thích chuẩn cho macOS (`customtkinter`, `openpyxl`, `gspread`, `google-auth`). |
| `tasks_config.json` | Danh sách cấu hình các bộ lọc CRM, liên kết Google Sheet và tab tương ứng. |
| `credentials.json` | Khóa xác thực Google Service Account (để đẩy dữ liệu lên Google Sheets nếu cần). |
| `cookie.txt` | Tệp lưu trữ mã phiên đăng nhập CRM (`KVCRM_PHPSESSID`). |
| `chrome_extension_get_cookie/` | Thư mục tiện ích mở rộng Google Chrome giúp lấy Cookie CRM chỉ với 1 cú nhấp chuột. |

---

## 🚀 Hướng Dẫn Cài Đặt Chi Tiết Từng Bước

### Bước 1: Kiểm tra hoặc cài đặt Python 3 trên Mac

1. Mở ứng dụng **Terminal** trên Mac (nhấn `Cmd + Space`, gõ `Terminal` rồi nhấn `Enter`).
2. Gõ lệnh kiểm tra phiên bản:
   ```bash
   python3 --version
   ```
3. **Kết quả**:
   - Nếu hiển thị `Python 3.10.x`, `3.11.x`, `3.12.x` hoặc `3.13.x`: Máy đã có Python.
   - Nếu chưa có hoặc báo lỗi `command not found`:
     👉 Tải bộ cài chính thức tại: [https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/)
     - Tải file **macOS 64-bit universal2 installer** (`.pkg`).
     - Nhấp đúp mở file `.pkg` và bấm *Next/Tiếp tục* để cài đặt (mất khoảng 1 phút).

---

### Bước 2: Cấp quyền chạy file Script (Chỉ làm 1 lần đầu)

Do cơ chế bảo mật Gatekeeper của macOS khi tải file từ Google Drive / Internet:
1. Mở **Terminal**.
2. Gõ chữ `cd ` *(có dấu cách phía sau)*.
3. Kéo và thả thư mục Tool này vào cửa sổ Terminal, rồi nhấn `Enter`.
4. Gõ lệnh sau rồi nhấn `Enter`:
   ```bash
   chmod +x *.command
   ```
> [!TIP]
> Nếu máy hiển thị cảnh báo file bị kiểm dịch (*quarantine*), bạn chạy thêm lệnh:
> ```bash
> xattr -d com.apple.quarantine *.command 2>/dev/null
> ```

---

### Bước 3: Cài đặt thư viện tự động

1. Trong thư mục Tool, nhấp đúp (double-click) vào file:
   👉 **`Cai_Dat_Mac.command`**
2. Cửa sổ Terminal sẽ tự động:
   - Tạo môi trường ảo cách ly (`venv`).
   - Tải và cài đặt các thư viện: `customtkinter`, `openpyxl`, `gspread`, `google-auth`.
3. Khi Terminal hiện thông báo:
   ```
   ✅ ĐÃ CÀI ĐẶT THÀNH CÔNG TẤT CẢ THƯ VIỆN!
   👉 Giờ bạn có thể nhấp đúp vào Chay_Tool_Mac.command để mở Tool.
   ```
4. Nhấn phím `Enter` để đóng cửa sổ.

---

### Bước 4: Cài đặt tiện ích lấy Cookie trên Chrome của Mac

1. Mở trình duyệt **Google Chrome** trên Mac.
2. Nhập vào thanh địa chỉ:
   ```
   chrome://extensions/
   ```
3. Bật công tắc **"Developer mode"** (Chế độ cho nhà phát triển) ở góc trên bên phải.
4. Bấm nút **"Load unpacked"** (Tải tiện ích đã giải nén) ở góc trên bên trái.
5. Chọn thư mục `chrome_extension_get_cookie` nằm ngay trong thư mục Tool này.
6. Icon tiện ích KiotViet CRM sẽ xuất hiện trên thanh công cụ của Chrome.

---

### Bước 5: Khởi động và sử dụng Tool kéo Data về Excel

#### 🔹 Cách 1: Sử dụng giao diện đồ họa (Khuyên dùng)
1. Nhấp đúp chuột vào file:
   👉 **`Chay_Tool_Mac.command`**
2. **Lấy Cookie**:
   - Truy cập trang CRM KiotViet ([https://kvcrm.kiotviet.vn/](https://kvcrm.kiotviet.vn/)) trên Chrome và đăng nhập.
   - Bấm vào icon tiện ích KiotViet CRM trên thanh Chrome ➔ Chọn **"Copy Cookie CRM"**.
   - Quay lại giao diện Tool, bấm nút **"📋 Dán từ Clipboard"** (Tool sẽ tự nhận diện và chuyển sang đèn 🟢 **ĐÃ KẾT NỐI**).
3. **Xuất dữ liệu**:
   - Tích chọn các bộ lọc cần xuất trong bảng tác vụ.
   - Bật checkbox **"Lưu Excel dự phòng"** nếu muốn tự động xuất file `.xlsx` về thư mục.
   - Bấm nút **"🚀 BẮT ĐẦU CHẠY ĐỒNG BỘ TẤT CẢ"**.
   - Tool sẽ kéo data từ CRM, định dạng màu sắc cột, viền bảng và lưu thành file Excel `.xlsx` ngay tại thư mục Tool.

#### 🔹 Cách 2: Sử dụng dòng lệnh Terminal (CLI) siêu nhanh
Nếu bạn muốn xuất nhanh một bộ lọc CRM bất kỳ mà không cần mở giao diện:
```bash
./venv/bin/python3 crm_export_tool.py "https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&viewname=17629..."
```
File Excel sẽ được tạo tự động với tên bộ lọc chuẩn tiếng Việt không dấu.

---

## 🛠️ Hướng Dẫn Khắc Phục Các Lỗi Phổ Biến Trên macOS

| Hiện tượng | Nguyên nhân | Cách xử lý |
| :--- | :--- | :--- |
| **"The file could not be executed because you do not have appropriate access privileges"** | File script tải về chưa có cờ thực thi `+x`. | Mở Terminal tại thư mục Tool, chạy lệnh: `chmod +x *.command`. |
| **"App can't be opened because it is from an unidentified developer"** | Cơ chế Gatekeeper của Apple bảo vệ file bên ngoài App Store. | Nhấp **chuột phải** (hoặc giữ `Control` + Click) vào file `.command` ➔ Chọn **Open** (Mở) ➔ Chọn **Open** lần nữa. |
| **"No module named '_tkinter'"** | Cài Python bằng Homebrew (`brew install python`) không kèm Tkinter theo mặc định. | Chạy lệnh: `brew install python-tk` trong Terminal, hoặc cài Python từ file `.pkg` chính thức của `python.org`. |
| **Báo lỗi "Cookie hết hạn" hoặc "Invalid request"** | Phiên đăng nhập trên CRM KiotViet đã hết hạn. | Vào lại `kvcrm.kiotviet.vn` trên Chrome, bấm icon tiện ích lấy Cookie mới và dán lại vào Tool. |
| **Terminal mở lên rồi tắt ngay trong tích tắc** | Thiếu thư viện hoặc lỗi đường dẫn. | Script mới đã có cơ chế giữ Terminal hiển thị mã lỗi. Hãy nhấp đúp vào `Cai_Dat_Mac.command` để cài đặt lại thư viện. |
