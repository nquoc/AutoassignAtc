import sys
from crm_api import get_staff_mapping

sys.stdout.reconfigure(encoding='utf-8')

def trigger():
    print("Triggering cache fetch...")
    val = get_staff_mapping("8178")
    print("Mapping for 8178:", val)

if __name__ == "__main__":
    trigger()
