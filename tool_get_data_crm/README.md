# 📦 BỘ CÔNG CỤ XUẤT DỮ LIỆU BỘ LỌC KIOTVIET CRM RA EXCEL & GOOGLE SHEETS
*(Dành cho AI khác và Lập trình viên tiếp nhận dự án)*

Thư mục này chứa trọn bộ công cụ và tài liệu hướng dẫn độc lập để **lấy dữ liệu từ bất kỳ bộ lọc nào trên KiotViet CRM** (100% Read-Only, không sửa đổi hay active dữ liệu).

---

## 📂 DANH MỤC TỆP TIN TRONG THƯ MỤC NÀY:

| Tên File / Thư mục | Chức năng |
| :--- | :--- |
| **`Chay_Giao_Dien.bat`** | ⚡ **Khởi động 1-Click**: Nhấp đúp chuột để mở giao diện đồ họa quản lý đồng bộ hàng loạt. |
| **`gui_crm_tool.py`** | 🖥️ **Ứng dụng giao diện (GUI)**: Quản lý Cookie, thêm/xóa động các cặp `[Link CRM]` ➔ `[Link Google Sheet]`, chạy đồng bộ đa luồng. |
| **`crm_export_tool.py`** | 🚀 **Công cụ CLI độc lập**: Script Python chạy trực tiếp từ dòng lệnh hoặc gọi ngầm. |
| **`chrome_extension_get_cookie/`** | 🧩 **Tiện ích mở rộng Chrome v2.0**: Extension cài vào Chrome để copy Cookie CRM chuẩn 100% chỉ bằng 1 click. |
| **`credentials.json`** | 🔑 **Khóa Service Account**: Cấp quyền ghi dữ liệu tự động vào Google Sheets qua thư viện `gspread`. |
| **`HUONG_DAN_GET_DATA_CRM.md`** | 📖 **Tài liệu kỹ thuật toàn diện**: Giải thích chi tiết kiến trúc CRM, cơ chế Cookie + CSRF Token, đặc tả API `ExportData`, mã hóa UTF-16, và code mẫu. |

---

## ⚡ HƯỚNG DẪN SỬ DỤNG NHANH:

### Cách 1: Sử dụng Giao diện đồ họa (Khuyên dùng - Cực dễ):
1. Nhấp đúp chuột vào file **`Chay_Giao_Dien.bat`**.
2. Ô Cookie sẽ tự động nạp phiên hợp lệ từ `cookie.txt` (hoặc bấm *Dán từ Clipboard*).
3. Thêm các cặp **Link CRM bộ lọc** và **Link Google Sheet** cần xuất (bấm `➕ Thêm Cặp Mới` hoặc `🗑️ Xóa`).
4. Bấm nút xanh **`🚀 BẮT ĐẦU CHẠY ĐỒNG BỘ TẤT CẢ`** và theo dõi tiến trình trực tiếp.

### Cách 2: Chạy dòng lệnh (CLI):
```bash
python crm_export_tool.py "<LINK_BỘ_LỌC_CRM>" "" "<LINK_GOOGLE_SHEET>"
```
*(Nếu không nhập cookie, tool sẽ tự động đọc từ `cookie.txt` hoặc clipboard).*

---

## 🎯 DÀNH CHO AI MỚI TIẾP NHẬN:
Nếu bạn là một AI Agent mới tiếp nhận yêu cầu liên quan đến việc lấy dữ liệu từ link bộ lọc KiotViet CRM, hãy đọc file [`HUONG_DAN_GET_DATA_CRM.md`](file:///g:/My%20Drive/tools/AutoassignAtc/tool_get_data_crm/HUONG_DAN_GET_DATA_CRM.md) để nắm toàn bộ quy trình kỹ thuật.
