import sys
import subprocess

def test():
    try:
        import browser_cookie3
    except ImportError:
        print("Installing browser-cookie3...")
        subprocess.run([sys.executable, "-m", "pip", "install", "browser-cookie3"], stdout=subprocess.DEVNULL)
        import browser_cookie3
    
    print("Testing chrome cookie extraction...")
    try:
        cj = browser_cookie3.chrome(domain_name='kvcrm.kiotviet.vn')
        cookies = [f"{c.name}={c.value}" for c in cj]
        print("Cookies found:", len(cookies))
    except Exception as e:
        print("Error:", e)
        
    print("Testing edge cookie extraction...")
    try:
        cj = browser_cookie3.edge(domain_name='kvcrm.kiotviet.vn')
        cookies = [f"{c.name}={c.value}" for c in cj]
        print("Cookies found:", len(cookies))
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test()
