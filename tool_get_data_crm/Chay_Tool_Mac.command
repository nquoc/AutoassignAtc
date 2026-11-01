#!/bin/bash
cd "$(dirname "$0")"

# Cấp quyền thực thi tự động
chmod +x Chay_Tool_Mac.command Cai_Dat_Mac.command 2>/dev/null

echo "=========================================================="
echo "   ĐANG KHỞI ĐỘNG TOOL KIOTVIET CRM SYNC TRÊN MACBOOK"
echo "=========================================================="

if [ -f "venv/bin/python3" ]; then
    ./venv/bin/python3 gui_crm_tool.py
    EXIT_CODE=$?
elif command -v python3 &> /dev/null; then
    python3 gui_crm_tool.py
    EXIT_CODE=$?
else
    echo "❌ Không tìm thấy Python 3!"
    echo "👉 Vui lòng nhấp đúp vào file Cai_Dat_Mac.command trước để cài đặt."
    EXIT_CODE=1
fi

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "=========================================================="
    echo "❌ Có lỗi xảy ra trong quá trình khởi chạy (Mã lỗi: $EXIT_CODE)."
    echo "💡 Hãy thử nhấp đúp vào Cai_Dat_Mac.command để cài đặt lại thư viện."
    echo "=========================================================="
    read -p "Nhấn phím Enter để đóng..."
fi
