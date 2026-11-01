import json
import os
import sys
from crm_api import get_staff_mapping

sys.stdout.reconfigure(encoding='utf-8')

def show_staff():
    staff_file = os.path.join(os.path.dirname(__file__), "staff.json")
    with open(staff_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for coacher in ["quoc", "vietanh"]:
        staff_list = data.get(coacher, [])
        print(f"\nDanh sách nhân sự Coacher {coacher.upper()} và ID nội bộ:")
        for st in staff_list:
            short_id = st["short_id"]
            name = st["name"]
            internal_id = get_staff_mapping(short_id)
            if internal_id:
                print(f"- {name} (Mã nhân viên: {short_id}) => ID nội bộ CRM: {internal_id}")
            else:
                print(f"- {name} (Mã nhân viên: {short_id}) => CHƯA TÌM THẤY TRÊN CRM")

if __name__ == "__main__":
    show_staff()
