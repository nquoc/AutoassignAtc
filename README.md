# AutoAssign ATC & KiotViet CRM Assistant Bot

Hệ thống Bot Telegram tự động hóa điều phối, phân công data ATC/Ticket CRM và cập nhật kế hoạch Google Sheet cho đội ngũ Customer Success KiotViet.

## 🚀 Tính năng chính

1. **Phân phối & Bàn giao Ticket / ATC:**
   - Hỗ trợ bàn giao đơn nhanh chóng theo Mã gian hàng, Ticket ID, hoặc Retailer ID.
   - Cơ chế bảo vệ và kiểm tra trạng thái đơn trước khi chuyển giao.

2. **Tự động phân công (< 10 ATC treo):**
   - Bộ đếm thời gian tự động quét và phân chia thêm data vào các khung giờ: `06:30` sáng và `18:20` tối.
   - Hỗ trợ chạy mô phỏng dry-run (`/checkauto`) và phân công ngay lập tức (`/autoassign`).

3. **Tự động cập nhật Google Sheet Miền Nam (18:30 hàng ngày):**
   - Quét trực tiếp dữ liệu tồn và số lượng ATC đang giữ của nhân sự trên CRM.
   - Tự động tính Tổng tải (`ATC + Tồn`) và phân bổ theo 5 tầng tải (Tier 0 – Tier 4).
   - Bảo toàn các tuyến tỉnh cố định (Vũng Tàu, Đồng Nai) và cập nhật động các tuyến Hồ Chí Minh từ dòng 52.
   - Cho phép kích hoạt thủ công qua lệnh Telegram: `/updatesheet`.

4. **Báo cáo & Giám sát SLA:**
   - Gửi báo cáo cảnh báo trễ hạn SLA (≥ 10 ngày) lên Google Chat Space lúc `07:00` sáng (`/sla`).
   - Tổng hợp và gửi báo cáo tiến độ ngày lên Google Chat lúc `18:00` tối (`/report`).
   - Báo cáo danh sách Ticket treo đích danh lúc `18:10` tối (`/checktk`).

5. **Duy trì phiên đăng nhập CRM 24/7 (Keep-Alive Daemon):**
   - Luồng chạy ngầm liên tục kiểm tra cookie phiên CRM.
   - Tự động làm mới phiên đăng nhập qua Selenium khi phiên hết hạn.

---

## 🛠️ Cài đặt & Cấu hình

### 1. Yêu cầu môi trường
- Python 3.10+ (khuyên dùng Python 3.11)
- Google Chrome và ChromeDriver tương thích

### 2. Cài đặt thư viện
```bash
pip install -r requirements.txt
```
Hoặc nhấp đúp file: `Cai_Dat_Thu_Vien.bat`

### 3. Cấu hình thông tin
- Sao chép file cấu hình mẫu:
  ```bash
  copy config.example.json config.json
  copy service_account.example.json service_account.json
  ```
- Cập nhật các thông số trong `config.json`:
  - `bot_token`: Telegram Bot Token do BotFather cấp.
  - `gchat_webhook`: Webhook URL của Google Chat Space nhận báo cáo.
- Cập nhật thông tin Service Account Google Cloud trong `service_account.json` để cấp quyền đọc/ghi vào Google Sheets.

---

## 💻 Khởi động hệ thống

- **Chạy trực tiếp (cửa sổ console):**
  Nhấp đúp `Chay_Bot.bat` hoặc lệnh:
  ```bash
  python bot.py
  ```

- **Chạy ngầm dưới nền Windows (không hiện cửa sổ):**
  Nhấp đúp `Chay_Bot_Ngam.vbs`

- **Kiểm tra trạng thái bot đang chạy:**
  Nhấp đúp `Kiem_Tra_Trang_Thai_Bot.bat`

- **Dừng bot đang chạy ngầm:**
  Nhấp đúp `Dung_Bot.bat`
