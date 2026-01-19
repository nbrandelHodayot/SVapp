import requests
import time
from config import (
    REMOTE_IP,
    CONTROLLER_PORT,
    ACTUAL_SYSTEM_PASSWORD,
    CONTEXT_N,
    COMMON_COORDS,
    COMMANDS,
    BACK_CONFIG
)

# כתובת ה-CGI הבסיסית לשליחת פקודות עכבר מרחוק
BASE_URL = f"http://{REMOTE_IP}:{CONTROLLER_PORT}/cgi-bin/remote_mouse.cgi"

def _send_command(x: int, y: int, n: str, description: str = "פקודת שליטה") -> bool:
    """
    פונקציה פנימית לשליחת פקודת HTTP GET לשרת הבקרה.
    
    :param x: קואורדינטת X.
    :param y: קואורדינטת Y.
    :param n: ערך ה-N (Context).
    :param description: תיאור הפעולה ללוגים.
    :return: True אם הפקודה נשלחה בהצלחה, False אחרת.
    """
    try:
        url = f"{BASE_URL}?pos_x={x},pos_y={y},n={n}"
        print(f"שולח פקודה: '{description}' ל-URL: {url}")
        
        # הערה: עדיף להשתמש ב-requests.get() במקום לשלוח בקשה באופן ישיר
        # requests.get(url, timeout=5)
        
        # הדמיה של שליחת הפקודה
        response_status = 200 # הנחת הצלחה לצורך הדגמה
        
        if response_status == 200:
            print("הפקודה נשלחה בהצלחה.")
            return True
        else:
            print(f"שליחת הפקודה נכשלה. קוד סטטוס: {response_status}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"שגיאה במהלך שליחת הפקודה: {e}")
        return False

# =================================================================
#               *** פונקציות מרכזיות ***
# =================================================================

def perform_control_action(context_key: str, action_key: str) -> bool:
    """
    שולח פקודת הפעלה/כיבוי או Toggle עבור אזור ספציפי (N) ופעולה גנרית (X,Y).
    
    :param context_key: מפתח הקונטקסט (Context N) מתוך config.CONTEXT_N
                        (למשל: "BOYS_GENERAL_CONTROL", "GIRLS_SHABBAT_AC1").
    :param action_key: מפתח הפעולה (X,Y) מתוך config.COMMON_COORDS
                       (למשל: "AC_ON", "TIMER_1_TOGGLE").
    :return: True אם הפקודה נשלחה, False אחרת.
    """
    try:
        n = CONTEXT_N[context_key]
        coords = COMMON_COORDS[action_key]
        x = coords["x"]
        y = coords["y"]
        description = f"הפעלת '{action_key}' בתוך קונטקסט '{context_key}' (N={n})"
        
        return _send_command(x, y, n, description)
    except KeyError as e:
        print(f"שגיאה: המפתח {e} אינו קיים במילון הרלוונטי (CONTEXT_N או COMMON_COORDS).")
        return False

def navigate(command_key: str) -> bool:
    """
    שולח פקודת ניווט ישירה או קליק חד-פעמי הדורשת N, X, Y ספציפיים.
    
    :param command_key: מפתח הפקודה מתוך config.COMMANDS (למשל: "NAV_CONTROL", "BOYS_GENERAL").
    :return: True אם הפקודה נשלחה, False אחרת.
    """
    try:
        command = COMMANDS[command_key]
        x = command["x"]
        y = command["y"]
        n = command["n"]
        description = f"ניווט/קליק ישיר: '{command_key}' (N={n})"
        
        return _send_command(x, y, n, description)
    except KeyError as e:
        print(f"שגיאה: מפתח הפקודה '{e}' אינו קיים במילון COMMANDS.")
        return False

def go_back(context_key: str) -> bool:
    """
    שולח פקודת 'חזור' המוגדרת עבור קונטקסט ספציפי (כדי לחזור למסך הקודם).
    
    :param context_key: מפתח המסך הנוכחי מתוך config.BACK_CONFIG (למשל: "BOYS_GENERAL").
    :return: True אם הפקודה נשלחה, False אחרת.
    """
    try:
        back_command = BACK_CONFIG[context_key]
        x = back_command["x"]
        y = back_command["y"]
        n = back_command["n"]
        description = f"פקודת חזרה מהמסך '{context_key}' (N={n})"
        
        return _send_command(x, y, n, description)
    except KeyError as e:
        print(f"שגיאה: מפתח המסך '{e}' אינו קיים במילון BACK_CONFIG.")
        return False

def login() -> bool:
    """
    מבצע את רצף הפעולות הנדרש לכניסה למערכת: פתיחת מקלדת, הקלדת סיסמה ולחיצה על Enter.
    הסיסמה נמשכת מ-config.ACTUAL_SYSTEM_PASSWORD.
    """
    print("\n--- מתחיל תהליך כניסה (Login) ---")
    
    # 1. פתיחת תפריט משתמש / מקלדת (מתוך המסך הראשי N=0001)
    if not navigate("USER_BUTTON"):
        return False
    time.sleep(0.5) # השהייה קצרה לטעינת המסך
    
    # 2. (אופציונלי) לחיצה על החץ למטה (אם צריך לבחור משתמש/להעלות מקלדת)
    # בהנחה שהמקלדת עולה אוטומטית או שהכפתור מובנה במסך המקלדת
    # אם נדרש: navigate("DOWN_ARROW")
    
    # 3. הקלדת הסיסמה (66911)
    password = ACTUAL_SYSTEM_PASSWORD
    key_map = {
        '6': "KEY_6",
        '9': "KEY_9",
        '1': "KEY_1"
    }
    
    for digit in password:
        key_command = key_map.get(digit)
        if key_command:
            if not navigate(key_command):
                return False
            time.sleep(0.1)
        else:
            print(f"אזהרה: לא נמצא מפתח ב-COMMANDS עבור הספרה {digit}.")
            return False
            
    # 4. לחיצה על Enter
    if not navigate("KEY_ENT"):
        return False

    print("--- תהליך כניסה הושלם בהצלחה (משוער) ---\n")
    return True

# =================================================================
#               *** דוגמאות שימוש (להסרה בקובץ סופי) ***
# =================================================================
if __name__ == "__main__":
    print("--- דוגמאות לשימוש ב-actions.py ---")
    
    # 1. דוגמה לכניסה למערכת
    # success = login()
    
    # 2. דוגמה לניווט למסך בקרת אזורים
    # navigate("NAV_CONTROL") 
    
    # 3. דוגמה לכניסה למסך הפעלה כללית בנים
    # navigate("BOYS_GENERAL") 
    
    # 4. דוגמה להפעלת AC כללי בבנים
    # נכנסים לקונטקסט BOYS_GENERAL_CONTROL (N=0004...)
    # ומפעילים את הפעולה AC_ON (X,Y משותפים)
    # perform_control_action(
    #     context_key="BOYS_GENERAL_CONTROL",
    #     action_key="AC_ON"
    # )
    
    # 5. דוגמה לכיבוי תאורת חדרי בנות
    # perform_control_action(
    #     context_key="GIRLS_GENERAL_CONTROL",
    #     action_key="ROOMS_OFF"
    # )
    
    # 6. דוגמה להפעלת טיימר 1 בשעוני שבת - AC1 בנים
    # perform_control_action(
    #     context_key="BOYS_SHABBAT_AC1",
    #     action_key="TIMER_1_TOGGLE"
    # )

    # 7. דוגמה לפקודת חזור ממסך שעוני שבת בנים (למסך הראשי של שעוני השבת)
    # go_back("BOYS_SHABBAT_AC1") 
    
    print("\n--- סוף הדוגמאות ---")