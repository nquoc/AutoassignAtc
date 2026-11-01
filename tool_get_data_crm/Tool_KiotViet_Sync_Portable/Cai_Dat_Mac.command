#!/bin/bash
cd "$(dirname "$0")"

echo "=========================================================="
echo "   CÀI ĐẶT THƯ VIỆN CHO TOOL KIOTVIET CRM TRÊN MACBOOK"
echo "=========================================================="

# 1. Cấp quyền thực thi cho các file script trên Mac
chmod +x Chay_Tool_Mac.command Cai_Dat_Mac.command 2>/dev/null

# 2. Kiểm tra Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Máy Mac của bạn chưa cài đặt Python 3!"
    echo "👉 Hãy tải bản cài đặt Python chính thức cho macOS tại:"
    echo "   https://www.python.org/downloads/macos/"
    echo "   (Tải file 'macOS 64-bit universal2 installer' và cài đặt)."
    echo ""
    read -p "Nhấn phím Enter để thoát..."
    exit 1
fi

PY_VER=$(python3 -V 2>&1)
echo "🔍 Đã phát hiện: $PY_VER"

# 3. Kiểm tra Tkinter (đặc biệt cần thiết nếu dùng Python từ Homebrew)
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "⚠️ CẢNH BÁO: Python trên máy bạn đang thiếu thư viện giao diện Tkinter."
    echo "👉 Nếu dùng Homebrew, hãy mở Terminal chạy lệnh: brew install python-tk"
    echo "👉 Hoặc cài bản Python chính thức từ python.org để có sẵn Tkinter."
    echo ""
fi

# 4. Tạo môi trường ảo venv độc lập
echo "📦 Đang thiết lập môi trường ảo venv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv 2>/dev/null
fi

# 5. Cài đặt các thư viện cần thiết
if [ -f "venv/bin/pip" ]; then
    echo "⬇️ Đang tải và cài đặt thư viện vào venv..."
    ./venv/bin/pip install --upgrade pip --quiet 2>/dev/null
    ./venv/bin/pip install -r requirements.txt
    PIP_STATUS=$?
else
    echo "⬇️ Đang cài đặt thư viện trực tiếp..."
    python3 -m pip install -r requirements.txt --break-system-packages 2>/dev/null || python3 -m pip install -r requirements.txt
    PIP_STATUS=$?
fi

echo ""
if [ $PIP_STATUS -eq 0 ]; then
    echo "=========================================================="
    echo "✅ ĐÃ CÀI ĐẶT THÀNH CÔNG TẤT CẢ THƯ VIỆN!"
    echo "👉 Giờ bạn có thể nhấp đúp vào Chay_Tool_Mac.command để mở Tool."
    echo "=========================================================="
else
    echo "=========================================================="
    echo "⚠️ Cài đặt hoàn tất nhưng có thể một số gói chưa tải xong."
    echo "👉 Bạn hãy thử nhấp đúp vào Chay_Tool_Mac.command để kiểm tra."
    echo "=========================================================="
fi

read -p "Nhấn phím Enter để đóng..."
