import requests
from requests.auth import HTTPBasicAuth
import time

# הפרטים המדויקים מ-login.py
IP = "192.168.1.234"
USER = "Eli" 
PASS = "66911"

s = requests.Session()
# הגדרת ה-Auth ברמת הסשן
s.auth = HTTPBasicAuth(USER, PASS)

def test_navigation():
    print(f"--- Attempting NAV_STATUS using login.py logic ---")
    
    # הכתובת המדויקת עם הפסיקים - כפי שמופיע ב-login.py
    # השתמשתי בערכים שהוצאת מהדפדפן
    x, y, n = 497, 230, "00010000000000000000"
    
    manual_url = f"http://{IP}/cgi-bin/remote_mouse.cgi?pos_x={x},pos_y={y},n={n}"
    headers = {"Referer": f"http://{IP}/remote_control_full.html"}
    
    try:
        # שליחה בדיוק כמו ב-login.py
        resp = s.get(manual_url, headers=headers, timeout=5)
        
        print(f"URL Sent: {manual_url}")
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            print("SUCCESS! The controller should have moved to the Status page.")
        else:
            print(f"Failed with status: {resp.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_navigation()