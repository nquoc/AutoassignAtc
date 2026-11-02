# 🤖 ANTIGRAVITY AGENT INSTRUCTIONS FOR KV CRM (AutoassignAtc)

Chào mừng bạn đến với dự án tự động hóa **KV CRM (KiotViet CRM / VTiger Framework)**!
File này cung cấp toàn bộ kiến thức, quy tắc nghiệp vụ, bảng mã nhân viên và CLI có sẵn để thực thi **NGAY LẬP TỨC TRONG 1 GIÂY** mà không cần viết lại script từ đầu.

---

## ⚡ 1. CÁC LỆNH CLI SIÊU TỐC CÓ SẴN (BẮT BUỘC DÙNG NGAY)

> ⚠️ **QUY TẮC TỐC ĐỘ SỐ 1**: Khi nhận yêu cầu từ User qua Telegram/IDE, **HÃY CHẠY NGAY 1 LỆNH CLI DUY NHẤT DƯỚI ĐÂY**, tuyệt đối **KHÔNG tự viết file script scratch tạm bợ** gây mất thời gian!

| Yêu cầu của User | Lệnh CLI thực thi ngay lập tức | Kết quả đạt được |
| :--- | :--- | :--- |
| **Bàn giao / Kéo Ticket/ATC về SC** *(Ví dụ: `TT8802410 chuyển 8460`, `TT8944429 kéo về sc`, `nhanongcafe chuyển 8460`)* | `python quick_action.py transfer <TICKET_ATC_HOẶC_TÊN_GH> <MÃ_NV_HOẶC_SC>` | Tự tìm Ticket & ATC của gian hàng, check pool SC group/CSKH/Marketing và chuyển Owner (hỗ trợ cả mã NV và `sc` / `8845`). Tự động bắn thông báo sang Google Chat và tag đích danh `<users/{gid}>` nhân sự nhận. |
| **Hủy / Từ chối đơn** *(Ví dụ: `500897558 hủy`, `TT8887286 từ chối`)* | `python quick_action.py reject <TICKET_HOẶC_ATC> [NỘI_DUNG_LÝ_DO]` | Đổi `cskhcs_status="Huy"`, nối lý do vào `Mô tả`, thêm ModComment (Mặc định: `"khu vực không có SC"`). |
| **Chuyển Hỗ Trợ Online** *(Ví dụ: `500668446 online`, `107672641 online NA`, `109451241 online T15`)* | `python quick_action.py online <TICKET_ATC_HOẶC_RET_ID> [OI/NA/T15/NI]` | Gọi `checkCanChangeForm` và `SwitchOnlineSupport` chuyển về nhóm CSKH OI (`CSKHOI_DVKH`), NA (`CSKHNA_DVKH`), T15 (`CSKHOI_T15_DVKH`) hoặc NI (`CSKHNI_DVKH`). |
| **Chia data tỉnh / Phường Xã** *(Ví dụ: `chia 5 gialai cho 8469`, `cto 1,2 all 8460`)* | `python quick_action.py region <TỈNH> <SỐ_LƯỢNG/all> <MÃ_NV> [PHƯỜNG_1,PHƯỜNG_2]` | Phân công data tỉnh/phường hàng loạt (hỗ trợ chọn nhiều phường cùng lúc qua checkbox Telegram hoặc cú pháp tin nhắn/CLI) & ghi lịch sử log. |
| **Báo cáo Coacher Quốc** *(Ví dụ: `checkquoc`)* | `python quick_action.py checkquoc` | Quét live ATC treo từng NV + tồn đọng các tỉnh. |
| **Cảnh báo trễ SLA** *(Ví dụ: `check sla`, `sla 10 ngày`)* | `python quick_action.py sla [SỐ_NGÀY]` | Quét phân loại chi tiết data trễ SLA >= N ngày. |
| **Đối chiếu địa chỉ OTP (View 17629)** | `python quick_action.py checkaddr <YYYY-MM-DD> <YYYY-MM-DD>` | Đối chiếu Địa điểm thực tế ATC vs Địa chỉ kinh doanh HĐ. |
| **Tra cứu Ticket theo SĐT hàng loạt** *(Ví dụ: `checkphone 0779543777,0908... 8222`)* | `python quick_action.py checkphone <DANH_SÁCH_SĐT> [MÃ_NV]` | Quét Global Search tìm Ticket, bóc tách Số TK, TG sửa, Mô tả, TT, Tiêu đề, GH. |
| **Tra cứu chi tiết 1 Ticket** *(Ví dụ: `check TT8883164`)* | `python quick_action.py checktk <MÃ_TICKET>` | Tra cứu siêu tốc 1s: Tên GH, Retailer ID, Khách, SĐT, Owner, Trạng thái, Mô tả, ModComments. |
| **Quét Ticket treo ở SC Group (View 20322)** *(Ví dụ: `check sc group`, `checksc`)* | `python quick_action.py checksc` | Quét live toàn bộ Ticket treo trong SC Group kèm Người tạo, Tên GH, SĐT, Tiêu đề, Mô tả. |
| **Tra cứu & Giải mã KYC Potentials (Đơn lẻ hoặc Hàng loạt)** *(Ví dụ: `checkpot 500439310`, `checkpot 500439310,500111222`, `checkpot list.xlsx`)* | `python quick_action.py checkpot <DANH_SÁCH_ID_HOẶC_FILE>` | Quét song song đa luồng (multi-thread), tự động bóc tách & giải mã KYC (Địa chỉ kinh doanh chi tiết, SĐT, CCCD, Email), hiển thị bảng tổng hợp và tự động xuất ra file Excel `potentials_kyc_export.xlsx`. |
| **Lấy thông tin xuất hóa đơn Potentials** *(Ví dụ: `invoice 108704258`, `invoice 500840906`, `invoice 108704258 mail`)* | `python quick_action.py invoice <POT_ID_HOẶC_LINK_HOẶC_RET_ID> [mail]` | Tự động giải mã KYC bóc tách chuẩn: Tên gian hàng, Số hợp đồng, Tên công ty, Mã số thuế, Địa chỉ xuất hóa đơn, Primary Email (thêm tham số `mail` để xuất trọn gói mẫu email gửi P. Kế toán & anh Tuấn). |
| **Bắn báo cáo Ticket treo qua Google Chat (Tag đích danh)** | `python quick_action.py gchat_tk` | Quét View 17811 + 20322, map mã NV với `gchat_user_map.json` và tag đích danh `<users/{gid}>`. |
| **Cập nhật Tình trạng Potentials (Chờ Xét Duyệt)** *(Ví dụ: `pot_stage 109968614`)* | `python quick_action.py pot_stage <POT_ID> [TÌNH_TRẠNG]` | Dùng SaveAjax đơn trường đổi trạng thái (Mặc định: `"Chờ Xét Duyệt"`), tuyệt đối an toàn 100% không ảnh hưởng các trường khác. |
| **Cập nhật Ghi chú sao kê Potentials** *(Ví dụ: `pot_note 109968614 "sao ke..."`)* | `python quick_action.py pot_note <POT_ID> <NỘI_DUNG>` | Dùng SaveAjax đơn trường ghi đè nội dung sao kê vào trường `cf_pot_note`. |
| **Tìm theo PXK & Đổi Chờ Xét Duyệt (Đơn lẻ hoặc Hàng loạt)** *(Ví dụ: `pxk PXK/SG/430/10/2026`, `pxk PXK/SG/111... PXK/SG/222...`)* | `python quick_action.py pxk <DANH_SÁCH_PXK>` | Tự động search tìm Record ID theo số PXK `cf_pot_contractid`, bóc tách Tên GH và dùng `SaveAjax` chuyển sang `"Chờ Xét Duyệt"` an toàn 100%. |
| **Tự động chia data (< 10 ATC đẩy thêm 8 data)** *(Ví dụ: `chia tự động`, `autoassign`, `check chia`)* | `python quick_action.py auto_assign [dry/run]` | Quét View 20154, tự chia thêm 8 data cho NV giữ < 10 ATC (chạy cố định 06:30 & 20:30 hàng ngày, ưu tiên kho riêng Cà Mau/Sóc Trăng -> Cần Thơ; Cần Thơ/Lâm Đồng ưu tiên NV ít data nhất). |
| **Quét data tồn HCM & Điền Google Sheet (Phân tầng Tier)** *(Ví dụ: `sheet`, `updatesheet`, `cập nhật sheet`, `điền phường xã`)* | `python quick_action.py sheet` *(hoặc nhắn Telegram: `sheet` / `cập nhật sheet`)* | Tự động quét CRM live (View 20154 + data treo HCM), tính tổng tải (ATC + tồn), phân tầng Tier 0-4 và điền danh sách phường chính/backup chuẩn xác vào Google Sheet Miền Nam (Tự chạy cố định 21:00 hàng ngày). |
| **Điền thêm backup cụm Tân Bình cũ vào Google Sheet** *(Ví dụ: `themtb 8447`, `themtb`, `thêm tb`, `điền tb`)* | `python quick_action.py themtb <MÃ_NV>` *(hoặc Telegram: `/themtb [MÃ_NV]` hoặc bấm menu)* | Điền thêm 6 phường cụm Tân Bình cũ vào hàng của NV được chỉ định trên Google Sheet Miền Nam (Chỉ áp dụng cho 4 bạn quanh cty: Duy `8447`, Tùng `8440`, Minh `8448`, Đạt `8467`; tuyệt đối cấm Khang, Hiếu, Phát). Tự động lưu cấu hình duy trì qua các lần cập nhật. |
| **Xoá backup cụm Tân Bình cũ khỏi Google Sheet** *(Ví dụ: `xoatb`, `xóa tb`, `xáo tb`, `xoatanbinh`)* | `python quick_action.py xoatb` *(hoặc Telegram: `/xoatb`)* | Gỡ bỏ 6 phường cụm Tân Bình cũ khỏi Google Sheet Miền Nam và xóa cấu hình lưu trữ. |
| **Xuất dữ liệu bộ lọc bất kỳ ra Excel / Google Sheets (100% Read-Only)** *(Ví dụ: view 17559, 16309, HelpDesk...)* | `python crm_export_tool.py "<LINK_BỘ_LỌC>" [COOKIE] [FILE.xlsx]` | Gọi trực tiếp API `ExportData` ngầm, lấy toàn bộ hàng nghìn dòng trong 1-2s, xuất Excel đẹp hoặc đẩy Google Sheets (Xem thêm [`HUONG_DAN_GET_DATA_CRM.md`](file:///h:/My%20Drive/tools/AutoassignAtc/HUONG_DAN_GET_DATA_CRM.md) & Extension 1-click tại `chrome_extension_get_cookie/`). |

---

## 🧠 2. QUY TẮC TỰ ĐỘNG GHI NHỚ VÀ HỌC TẬP (SELF-LEARNING & MEMORY)

> 💡 **KHI USER YÊU CẦU MỘT THAO TÁC / QUY TRÌNH MỚI CHƯA CÓ TRONG DANH SÁCH**:
> 1. **Thực thi ngay**: Viết mã giải quyết xong yêu cầu của User.
> 2. **Tự động lưu vào bộ nhớ vĩnh viễn**:
>    - Nếu là thao tác lặp lại ➔ Thêm hàm CLI tương ứng vào [`quick_action.py`](file:///h:/My%20Drive/tools/AutoassignAtc/quick_action.py).
>    - Cập nhật cú pháp và quy tắc mới vào file [`AGENTS.md`](file:///H:/My%20Drive/tools/AutoassignAtc/AGENTS.md) này ngay lập tức.
> 3. **Lần sau User hỏi lại**: Agent sẽ tự động nhận diện và gọi ngay lệnh CLI 1 dòng siêu tốc đã học, tuyệt đối không giải thích dông dài hay viết lại script từ đầu!

---

## 🛡️ 3. NGUYÊN TẮC BẢO VỆ DỮ LIỆU & AN TOÀN TUYỆT ĐỐI (BẮT BUỘC)

1. 🔍 **MẶC ĐỊNH 100% READ-ONLY KHI CHECK / TRA CỨU**:
   - Khi người dùng gửi Link CRM hoặc dùng từ `check`, `xem`, `kiểm tra`, `thế nào`, `đã...chưa`, `đếm data`...
   - **TUYỆT ĐỐI CHỈ ĐỌC DỮ LIỆU VÀ BÁO CÁO**, không tự ý bàn giao hay đóng/hủy bất kỳ bản ghi nào!

2. 🔒 **QUY TẮC KHÓA NGƯỜI XỬ LÝ (OWNER POOL VALIDATION - BẮT BUỘC)**:
   - **CHỈ ĐƯỢC CHUYỂN** khi Ticket hoặc đơn ATC đang thuộc nhóm chung/hàng đợi pool:
     - `Chăm sóc khách hàng trực tiếp` (hoặc `Chăm sóc khách hàng hỗ trợ trực tiếp`)
     - `SC group` / `SC_Group` / `Nhóm SC`
     - (hoặc chưa có ai nhận).
   - ⛔ **NẾU ĐÃ CÓ NHÂN SỰ CỤ THỂ NÀO NHẬN/ĐỨNG TÊN** (ví dụ: `8178 - Phan Ngọc Nguyên`, `8464 - Lê Minh`, `8460`,...) ➔ **TUYỆT ĐỐI KHÔNG ĐƯỢC CHUYỂN, BÁO LẠI NGAY CHO USER!**

3. 🔒 **KHÔNG BÀN GIAO ĐƠN ĐÃ LÀM / ĐÃ ĐÓNG (COMPLETED / CLOSED)**:
   - Nếu Ticket HelpDesk hoặc đơn ATC CSKHSC đang ở trạng thái `Đã làm`, `Completed`, `Closed`, `Đã đóng`, `Hủy` ➔ **KHÔNG ĐƯỢC PHÉP CHUYỂN CHO NGƯỜI KHÁC**!
   - `quick_action.py` đã tự động kiểm tra và khóa an toàn 100%.

4. ✍️ **CHỈ CHỈNH SỬA KHI CÓ LỆNH ĐÍCH DANH**:
   - Chỉ thực hiện bàn giao hoặc hủy khi người dùng ra lệnh rõ ràng cho mã ATC / Ticket cụ thể.

5. 📝 **QUY TẮC THUẬT NGỮ CHUẨN (TERMINOLOGY RULE - BẮT BUỘC)**:
   - Luôn gọi bản ghi CSKHSC là **ATC** (ví dụ: `64 ATC`, `13 ATC`, `ATC treo`, `ATC đổi thông tin`).
   - ⛔ **TUYỆT ĐỐI KHÔNG DÙNG TỪ "ĐƠN"** (vì đây là tác vụ chăm sóc/hỗ trợ ATC, không phải đơn hàng)!

6. 📝 **QUY TẮC BÁO CÁO BÀN GIAO CRM (TRANSFER REPORTING RULE - BẮT BUỘC)**:
   - Khi báo cáo kết quả bàn giao Ticket/ATC ("CHI TIẾT BÀN GIAO CRM"), **BẮT BUỘC PHẢI LUÔN CÓ CẢ 2 TRƯỜNG**:
     1. 🏪 **`TÊN GIAN HÀNG (TÊN GH)`**: Trường `cf_website` trên Ticket (ví dụ: `mekongnhahang`, `mekonghotelcm`...) kèm Retailer ID. (Tuyệt đối không nhầm sang tên cá nhân ở `contact_id`).
     2. 💬 **`MÔ TẢ (DESCRIPTION)`**: Toàn bộ nội dung vấn đề khách hàng cần hỗ trợ để người dùng nắm bắt ngay mà không cần mở lại link!

7. 👤 **QUY TẮC BÁO CÁO TICKET SC GROUP (CREATOR REPORTING RULE - BẮT BUỘC)**:
   - Khi quét / báo cáo danh sách Ticket treo ở SC Group (View 20322), **BẮT BUỘC PHẢI HIỂN THỊ TRƯỜNG `NGƯỜI TẠO` (CREATOR)** kèm bộ phận để người dùng nắm rõ nguồn gốc phát sinh ticket và tiện phối hợp.

8. 🔒 **QUY TẮC CẬP NHẬT TRƯỜNG POTENTIALS / CRM (CHỈ DÙNG SAVEAJAX ĐƠN TRƯỜNG - TUYỆT ĐỐI KHÔNG DÙNG FORM SAVE TOÀN BỘ)**:
   - Khi cập nhật bất kỳ trường nào trên CRM (ví dụ: `sales_stage`, `cf_pot_note`,...): **BẮT BUỘC DÙNG ENDPOINT `SaveAjax` ĐƠN TRƯỜNG** (`POST index.php?module={MODULE}&action=SaveAjax&record={ID}&field={FIELD}&value={VALUE}`).
   - Nếu cần cập nhật đồng thời nhiều trường (ví dụ vừa sửa Ghi chú sao kê vừa đổi Tình trạng sang Chờ Xét Duyệt): **BẮT BUỘC TÁCH THÀNH 2 (HOẶC NHIỀU) REQUEST `SaveAjax` RIÊNG BIỆT**.
   - ⛔ **TUYỆT ĐỐI KHÔNG SUBMIT FORM EDITVIEW TOÀN PHẦN (`action=Save`)**: vì trên giao diện form web CRM, các trường dropdown khác (như `Cơ hội` / `potentialname`, `Trạng thái bảo lưu`, `Đối thủ`,...) thường có giá trị mặc định (như auto-select *"Hợp đồng phần mềm"* thay vì *"Hợp đồng phần cứng"*), nếu submit toàn form sẽ làm ghi đè sai lệch dữ liệu!

9. 📢 **QUY TẮC BẮN THÔNG BÁO BÀN GIAO GOOGLE CHAT (TRANSFER NOTIFICATION RULE - BẮT BUỘC)**:
   - Khi bàn giao thành công Ticket & ATC (qua tin nhắn Bot Telegram hoặc lệnh CLI `transfer`): **TỰ ĐỘNG BẮN THÔNG BÁO LÊN GOOGLE CHAT VÀ TAG ĐÍCH DANH NHÂN SỰ NHẬN** (`<users/{gid}>`) qua hàm `send_transfer_gchat` dựa trên bảng ánh xạ `gchat_user_map.json`.
   - Giúp nhân sự phụ trách nhận được thông báo push ngay tức thì trên điện thoại / máy tính để vào xử lý ticket kịp thời.

---

## 👥 4. BẢNG MÃ NHÂN VIÊN (STAFF CODE MAPPING)

> `quick_action.STAFF_MAP` tự động nạp toàn bộ 209 nhân sự từ `staff_mapping_cache.json`. Dưới đây là các mã thông dụng:

| Mã NV (Short Code) | ID Nội Bộ CRM (`changeOwnerId`) | Họ Tên & Bộ Phận |
| :--- | :--- | :--- |
| **8201** | `11216` | Nguyễn Ái Quốc - Coacher |
| **8466** | `12147` | Lê Cao Minh Đức - CTO |
| **8460** | `12080` | Lê Minh Hiển - CTO |
| **8458** | `12032` | Đặng Duy Khương - CTO |
| **8470** | `12146` | Lương Trọng Đạo - CTO |
| **8482** | `12982` | Lê Đức Nhật - HUE |
| **8457** | `12031` | Đặng Lê Tiến Thành - HPG |
| **8486** | `12432` | Mai Đức Minh - DNG |
| **8465** | `13410` | Hồ Ngọc Thiên Hy - NTG |
| **8469** | `11670` | Nguyễn Hưng Hải - GLI |
| **8178** | `11212` | Phan Ngọc Nguyên - BĐH |
| **8461** | `12079` | Trịnh Đức Phong - LĐG |
| **8489** | `12464` | Nguyễn Hà Anh Vũ - LĐG |
| **8484** | `13759` | Trần Thanh Nam - VTU |
| **8231** | `7487` | Thượng Thái Hiếu - SGN |
| **8437** | `11161` | Nguyễn Đoàn Hưng Phát - SGN |
| **8440** | `11197` | Doãn Việt Tùng - SGN |
| **8447** | `11196` | Võ Khánh Duy - SGN |
| **8448** | `13457` | Nguyễn Đỗ Nhật Minh - CS |
| **8462** | `13488` | Nguyễn Hoàng Khang - CS |
| **8467** | `13456` | Nguyễn Thành Đạt - CS |
| **8456** | `12030` | Nguyễn Việt Anh - HNI |
| **8280** | `10675` | Vũ Minh Đức - HNI |
| **8246** | `6881` | Lê Văn Bách - HNI |
| **8492** | `13460` | Nguyễn Thành Nam - HNI |
| **8845** / `sc` | `8845` | SC Group (Hàng đợi chung SC) |

---

## ⚡ 5. CÚ PHÁP API & QUY TRÌNH THỰC THI CHUẨN

### A. Bàn giao Ticket & ATC (`do_transfer`):
1. Cập nhật Ticket HelpDesk: `POST index.php` -> `module=HelpDesk&action=SaveAjax&field=assigned_user_id&value={USER_ID}&record={REC_ID}`
2. Đồng bộ đơn ATC liên quan (trừ đơn đã hoàn thành hoặc đã có nhân sự cụ thể): `POST index.php` -> `module=CSKHSC&action=ChangeOwnerAction&changeOwnerId={USER_ID}&selected_ids[]={ATC_ID}`

### B. Hủy / Từ chối (`do_reject`):
1. **Ticket HelpDesk**:
   - `field="ticketdenyreason"`, `value="Khách hàng hủy yêu cầu"`.
   - `field="ticketstatus"`, `value="Rejected"`.
   - Thêm bình luận vào `ModComments`: (Mặc định: `"khu vực không có SC"`).
2. **Đơn CSKHSC**:
   - `field="cskhcs_status"`, `value="Huy"` (Lưu ý: Mã picklist bắt buộc là `Huy`, không dùng `Cancelled`).
   - Nối lý do vào trường `description` (`Mô tả`): `- Lý do hủy: {comment}` (Mặc định: `"khu vực không có SC"`).
   - Thêm bình luận vào `ModComments`: `action=SaveAjax&related_to={REC_ID}&commentcontent={comment}` (Mặc định: `"khu vực không có SC"`).

### C. Chuyển Hỗ Trợ Online (`SwitchOnlineSupport`):
- URL GET: `index.php?module=CSKHSC&action=SwitchOnlineSupport&record={ATC_ID}&cskhcs_type={TYPE}`
- `TYPE`: `CSKHOI_DVKH` (CSKH OI), `CSKHOI_T15_DVKH` (CSKH T15), `CSKHNA_DVKH` (CSKH NA) hoặc `CSKHNI_DVKH` (CSKH NI).

### D. Cập nhật Hợp đồng / Potentials (`do_update_pot_field`):
1. **Đổi trạng thái Potentials**: `python quick_action.py pot_stage <POT_ID> [Chờ Xét Duyệt]`
   - API: `POST index.php` -> `module=Potentials&action=SaveAjax&record={POT_ID}&field=sales_stage&value={STAGE}`
2. **Cập nhật Ghi chú sao kê**: `python quick_action.py pot_note <POT_ID> <NỘI_DUNG_SAO_KÊ>`
   - API: `POST index.php` -> `module=Potentials&action=SaveAjax&record={POT_ID}&field=cf_pot_note&value={NOTE}`
   - *(Quy tắc bất biến: Luôn gọi từng request `SaveAjax` đơn lẻ cho từng trường để bảo toàn 100% các trường còn lại, kể cả khi phải chạy 2 requests)*.
3. **Tìm & chuyển Chờ Xét Duyệt theo mã PXK**: `python quick_action.py pxk <DANH_SÁCH_PXK>`
   - Tự động tìm Record ID qua `cf_pot_contractid` trên CRM, bóc tách tên gian hàng và cập nhật `sales_stage="Chờ Xét Duyệt"` qua `SaveAjax` siêu tốc (hỗ trợ 1 hoặc nhiều mã PXK cùng lúc).

---

## 📍 6. CẤU HÌNH ĐỊA BÀN & GỢI Ý PHÂN CÔNG HCM & CỤM TÂN BÌNH CŨ

### A. Danh sách 7 nhân sự và Phường chính / Backup:
1. **8437 - Nguyễn Đoàn Hưng Phát** (Đồng Nai):
   - **Phường chính (Đồng Nai)**: `Hố Nai`, `Trấn Biên`, `Tam Hiệp`, `Trảng Bom`, `Bình Minh`, `Biên Hòa` [IN ĐẬM]; `Trảng Dài`, `Long Bình`, `Tân Triều` [BÌNH THƯỜNG]. *(Đổ trực tiếp từ kho Đồng Nai)*.
   - **Phường Backup (Thủ Đức, Q9)**: `Thủ Đức`, `Linh Xuân`, `Tăng Nhơn Phú`, `Long Bình`.
   - *Quy tắc*: Luôn ưu tiên duy trì đổ kho Đồng Nai cho Hưng Phát.
2. **8231 - Thượng Thái Hiếu** (TP. Thủ Đức, Q9 cũ):
   - **Phường chính**: `Hiệp Bình`, `Thủ Đức`, `Tam Bình`, `Linh Xuân`, `Tăng Nhơn Phú`, `Long Bình` [100% IN ĐẬM].
   - **Phường Backup (Q2, Bình Dương)**: `Bình Trưng`, `Phước Long`, `An Khánh` [IN ĐẬM]; `Dĩ An`, `Đông Hòa` [BÌNH THƯỜNG].
3. **8447 - Võ Khánh Duy** (Quận Tân Phú):
   - **Phường chính**: `Phú Thạnh`, `Tây Thạnh`, `Tân Sơn Nhì`, `Phú Thọ Hòa`, `Tân Phú` [100% IN ĐẬM].
   - **Phường Backup (Quận Bình Tân)**: `An Lạc`, `Bình Trị Đông`, `Bình Hưng Hòa`, `Bình Tân` [IN ĐẬM]; `Tân Tạo` [BÌNH THƯỜNG].
4. **8440 - Doãn Việt Tùng** (Quận Gò Vấp):
   - **Phường chính**: `Hạnh Thông`, `Gò Vấp`, `An Hội Đông`, `Thông Tây Hội`, `An Hội Tây` [100% IN ĐẬM].
   - **Phường Backup (Bình Thạnh, Q12)**: `Bình Thạnh`, `Bình Lợi Trung`, `Thới An`, `An Phú Đông` [IN ĐẬM]; `Gia Định`, `Thạnh Mỹ Tây` [BÌNH THƯỜNG].
5. **8448 - Nguyễn Đỗ Nhật Minh** (Quận Bình Thạnh, Phú Nhuận):
   - **Phường chính**: `Gia Định`, `Bình Thạnh`, `Thạnh Mỹ Tây` [IN ĐẬM]; `Cầu Kiệu`, `Phú Nhuận`, `Đức Nhuận` [BÌNH THƯỜNG].
   - **Phường Backup (Q2, Bình Thạnh mở rộng)**: `An Khánh`, `Cầu Kiệu`, `Phú Nhuận`, `Bình Quới`, `Bình Lợi Trung` [IN ĐẬM].
   - *Quy tắc đặc thù*: Mọi ticket phát sinh ở Quận 4 & Quận 7 ưu tiên điều phối trực tiếp cho 8448.
6. **8467 - Nguyễn Thành Đạt** (Quận 11, Quận 3):
   - **Phường chính**: `Minh Phụng`, `Bình Thới`, `Hòa Bình`, `Phú Thọ`, `Bàn Cờ` [IN ĐẬM]; `Chợ Lớn`, `Hòa Hưng` [BÌNH THƯỜNG].
   - **Phường Backup (Quận 10, Quận 1)**: `Diên Hồng`, `Vườn Lài`, `Bến Thành`, `Xuân Hòa` [IN ĐẬM].
7. **8462 - Nguyễn Hoàng Khang** (Quận 12):
   - **Phường chính**: `Thới An`, `Tân Thới Hiệp`, `Gò Vấp`, `Đông Hưng Thuận` [IN ĐẬM]; `Trung Mỹ Tây`, `Đông Thạnh` [BÌNH THƯỜNG].
   - **Phường Backup (Gò Vấp, Hóc Môn, Bình Dương)**: `Thông Tây Hội`, `An Hội Tây` [IN ĐẬM]; `Lái Thiêu`, `Bà Điểm`, `Cầu Kiệu` [BÌNH THƯỜNG].

### B. Cụm Tân Bình Cũ (Quanh Cty) - Tách Menu Riêng:
- **6 Phường cụm Tân Bình cũ**: `Tân Sơn Hòa`, `Tân Sơn Nhất`, `Tân Hòa`, `Bảy Hiền`, `Tân Bình`, `Tân Sơn`.
- **Quy tắc tuyệt đối**:
  1. Trong menu Gợi ý chung của HCM, **KHÔNG** gợi ý hoặc chia các phường này vào danh sách của nhân sự nào cả.
  2. Có **Menu riêng** (`tb_menu` hoặc lệnh `tanbinh`, `tb`) để quét và chia riêng cho các bạn quanh cty.
  3. **Nhân sự được phép nhận**: `8447` (Khánh Duy), `8440` (Việt Tùng), `8448` (Nhật Minh), `8467` (Thành Đạt).
  4. ⛔ **Tuyệt đối loại trừ**: `8231` (Thái Hiếu), `8462` (Hoàng Khang), `8437` (Hưng Phát).
  5. **Quản lý trên Google Sheet Miền Nam**:
     - Lệnh điền thêm: `themtb <MÃ_NV>` hoặc `/themtb` (bấm chọn menu 4 bạn quanh cty). Lưu trạng thái vào `tb_sheet_assignment.json` và duy trì qua các lần quét 21h tự động.
     - Lệnh xoá: `xoatb` hoặc `/xoatb` (gỡ bỏ khỏi sheet ngay lập tức).

