# test_click.py
import requests
from requests.auth import HTTPBasicAuth
import config
import login as auth_logic

# הגדרות (וודא שהן נכונות)
IP = config.REMOTE_IP
USER = auth_logic.CONTROLLER_USER
PASS = auth_logic.CONTROLLER_PASS

# הערכים שאתה רוצה לבדוק (תעתיק בדיוק מה-config)
X = 503
Y = 232
N = "00010000000000000000" # תוודא שזה ה-N של המסך הראשי!

s = requests.Session()
s.auth = HTTPBasicAuth(USER, PASS)

def test_single_click():
    print(f"--- Testing Click on {X}, {Y} with N={N} ---")
    
    # 1. קודם כל עושים לוגין נקי
    auth_logic.send_login_sequence(s, config.CGI_URL, config.REFERER)
    print("Login sequence sent. Waiting 2 seconds...")
    import time
    time.sleep(2)

    # 2. שליחת הלחיצה
    url = f"http://{IP}/cgi-bin/remote_mouse.cgi"
    params = {"pos_x": X, "pos_y": Y, "n": N}
    headers = {"Referer": f"http://{IP}/remote_control_full.html"}
    
    resp = s.get(url, params=params, headers=headers)
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response Preview: {resp.text[:200]}") # נראה מה הוא החזיר
    
    if "main_frame" in resp.text or "remote_control" in resp.text:
        print("SUCCESS: The PLC accepted the click logic.")
    else:
        print("FAILED: The PLC returned something else (maybe login page?)")

if __name__ == "__main__":
    test_single_click()