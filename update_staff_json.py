import json
import os
import sys
from crm_api import get_staff_mapping

sys.stdout.reconfigure(encoding='utf-8')

def update_staff():
    staff_file = os.path.join(os.path.dirname(__file__), "staff.json")
    with open(staff_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for coacher, staff_list in data.items():
        print(f"Updating {coacher}...")
        for st in staff_list:
            internal = get_staff_mapping(st["short_id"])
            if internal:
                st["internal_id"] = internal
            print(f"- {st['short_id']} => {internal}")

    with open(staff_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print("Done updating staff.json")

if __name__ == "__main__":
    update_staff()
