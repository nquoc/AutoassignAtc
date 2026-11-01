import sys
import re

def run():
    with open('crm_assigner.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The previous replace_file_content injected bad code at line 134.
    # Let's clean it up first.
    bad_code = """            # Extract data-id
            data_id_match = re.search(r'data-id=[\\'"](\\d+)[\\'"]', html) # Find the first data-id in the html (which belongs to the first row)
            if not data_id_match:
                return False, "Không thể trích xuất data-id từ kết quả."
                    """
    content = content.replace(bad_code, "")
    
    # Now replace the double quotes data-id regex globally
    content = content.replace(r'data-id="(\d+)"', r'data-id=[\'"](\d+)[\'"]')

    with open('crm_assigner.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Fixed data-id regex globally.")

if __name__ == "__main__":
    run()
