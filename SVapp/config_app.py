# config_app.py
import socket

COMPUTER_NAME = socket.gethostname().upper() # הופך הכל לאותיות גדולות למניעת טעויות
# בדיקה גמישה יותר - אם השם מכיל את המחרוזת או שווה לה
SIMULATION_MODE = ("HOD2301-07" in COMPUTER_NAME) 

# שנה ל-True כשאתה בבית, ול-False כשאתה בעבודה
MOCK_MODE = False

print(f"DEBUG: Computer Name is {COMPUTER_NAME}")
print(f"DEBUG: Simulation Mode is {SIMULATION_MODE}")

# --- הגדרות חיבור לבקר ---
REMOTE_IP = "192.168.1.234"
CONTROLLER_USERNAME = "Eli"
CONTROLLER_PASSWORD = "66911"

CGI_URL = f"http://{REMOTE_IP}/cgi-bin/remote_mouse.cgi"
REFERER = f"http://{REMOTE_IP}/remote_control_full.html?pic_format=bmp"

# --- אבטחת האפליקציה (Flask) ---
SECRET_KEY = "super-secret-key-change-me"
INACTIVITY_TIMEOUT = 270  # שניות עד לניתוק אוטומטי

# מילון משתמשים לכניסה לממשק הווב
USERS = {
    "admin": "6546",
    "eli": "66911"
}
 
# =================================================================
#           *** הגדרת Context N (הקשרים) ***
# =================================================================
# ערך ה-N קובע לאיזה מסך בבקר הפקודה מתייחסת
CONTEXT_N = {
    # --- כללי וניווט ראשי ---
    "MAIN":     "00010000000000000000",
    "STATUS":   "00500000000000000000",
    "CONTROL":  "00020000000000000000",
    "SETTINGS": "01000000000000000000",
    
    "CONTROL_MENU": "00020000000000000000",
    "NAV_CONTROL": "00020000000000000000",
    "LOGIN": "00010001000000000000",
    "WAKE_UP": "00010002000000000000",

    # --- סטטוס מערכות ---
    "STATUS_BOYS": "00500000000000000000",
    "STATUS_GIRLS": "00510000000000000000",
    "STATUS_PUBLIC": "00520000000000000000",
    "STATUS_SHABBAT": "00540000000000000000",

    # --- הפעלה כללית ---
    "BOYS_GENERAL": "00040000000000000000",
    "GIRLS_GENERAL": "00120000000000000000",

    # --- חלוקה למבנים ---
    "BOYS_SPLIT": "00030000000000000000",
    "GIRLS_SPLIT": "00100000000000000000",  # קונטקסט כללי לחלוקה למבנים בנות (משמש לניווט)
    "GIRLS_SPLIT_1": "00100000000000000000",
    "GIRLS_SPLIT_2": "00110000000000000000",
    "PUBLIC_SPLIT": "00190000000000000000",
    "PUBLIC_MAIN": "00190000000000000000",  # קונטקסט כללי לאזור ציבורי (משמש לניווט)
    "PUBLIC_SHABBAT": "00200000000000000000",  # שעוני שבת אזור ציבורי (משמש לניווט)

    # --- שעוני שבת בנים ---
    "BOYS_SHABBAT_AC1": "00050000000000000000",
    "BOYS_SHABBAT_AC2": "00060000000000000000",
    "BOYS_SHABBAT_ROOM_LIGHTS": "00070000000000000000",
    "BOYS_SHABBAT_BATHROOM_LIGHTS": "00080000000000000000",
    "BOYS_SHABBAT_HEATER": "00090000000000000000",

    # --- שעוני שבת בנות ---
    "GIRLS_SHABBAT_AC1": "00130000000000000000",
    "GIRLS_SHABBAT_AC2": "00140000000000000000",
    "GIRLS_SHABBAT_ROOM_LIGHTS": "00150000000000000000",
    "GIRLS_SHABBAT_BATHROOM_LIGHTS": "00160000000000000000",
    "GIRLS_SHABBAT_HEATER": "00170000000000000000",

    # --- מועדונים (בנים/בנות) ---
    "CLUBS_BOYS": "00340000000000000000",
    "CLUBS_GIRLS": "00350000000000000000",

    # --- מועדונים (אזור ציבורי) ---
    "CLUBS_PUBLIC_LIB": "00360000000000000000",
    "CLUBS_PUBLIC_HOLLAND": "00370000000000000000",
    "CLUBS_PUBLIC_NATIV": "00380000000000000000",
    "CLUBS_PUBLIC_DAVID": "00390000000000000000",
    "CLUBS_PUBLIC_POLICE": "00400000000000000000",
    "CLUBS_PUBLIC_ECONOMICS": "00410000000000000000",
    
    # --- שונות ---
    "PUBLIC_D1": "00330000000000000000",
    "D1_MAIN": "00330000000000000000",      # שעות מגעני D1 (ראשי)
    "D1_CLUBS_BOYS": "00340000000000000000", # מועדונים בנים
    "D1_CLUBS_GIRLS": "00350000000000000000",# מועדונים בנות
    "D1_CLUBS_PUB": "00360000000000000000",  # מועדונים ציבורי
}

COMMANDS = {
    # --- פקודות ניווט מהתפריט הראשי ---
    "NAV_STATUS": {"x": 503,"y": 232, "n": "00010000000000000000"},
    "NAV_CONTROL": {"x": 503,"y": 367, "n": "00010000000000000000"},
    "NAV_SETTINGS": {"x": 504,"y": 502, "n": "00010000000000000000"},
    
    # --- פקודות ניווט בדף "סטטוס מערכות" י ---
    "STATUS_BOYS":   {"x": 230, "y": 71, "n": CONTEXT_N["STATUS_BOYS"]},
    "STATUS_GIRLS":  {"x": 169, "y": 65, "n": CONTEXT_N["STATUS_GIRLS"]},
    "STATUS_PUBLIC": {"x": 101, "y": 68, "n": CONTEXT_N["STATUS_PUBLIC"]},
    "STATUS_SHABBAT": {"x": 35, "y": 65, "n": CONTEXT_N["STATUS_SHABBAT"]},
    
    # --- פקודות ניווט בדף "בקרת אזורים" י ---
    "BOYS_SPLIT":    {"x": 900, "y": 333, "n": CONTEXT_N["CONTROL_MENU"]},
    "BOYS_GENERAL":  {"x": 900, "y": 444, "n": CONTEXT_N["CONTROL_MENU"]},
    "BOYS_SHABBAT":  {"x": 900, "y": 555, "n": CONTEXT_N["CONTROL_MENU"]},

    "GIRLS_SPLIT":   {"x": 640, "y": 333, "n": CONTEXT_N["CONTROL_MENU"]},
    "GIRLS_GENERAL": {"x": 640, "y": 444, "n": CONTEXT_N["CONTROL_MENU"]},
    "GIRLS_SHABBAT": {"x": 640, "y": 555, "n": CONTEXT_N["CONTROL_MENU"]},

    "PUBLIC_SPLIT":   {"x": 400, "y": 333, "n": CONTEXT_N["CONTROL_MENU"]},
    "PUBLIC_SHABBAT": {"x": 400, "y": 444, "n": CONTEXT_N["CONTROL_MENU"]},
    "PUBLIC_D1_CANCEL": {"x": 400, "y": 555, "n": CONTEXT_N["CONTROL_MENU"]},

    "CLUBS_BOYS":     {"x": 140, "y": 333, "n": CONTEXT_N["CONTROL_MENU"]},
    "CLUBS_GIRLS":    {"x": 140, "y": 444, "n": CONTEXT_N["CONTROL_MENU"]},
    "CLUBS_PUBLIC_LIB": {"x": 140, "y": 555, "n": CONTEXT_N["CONTROL_MENU"]},
    
    "CLUBS_PUBLIC_HOLLAND": {"x": 35, "y": 220, "n": CONTEXT_N["CLUBS_PUBLIC_LIB"]},
    "CLUBS_PUBLIC_NATIV":   {"x": 35, "y": 270, "n": CONTEXT_N["CLUBS_PUBLIC_LIB"]},
    "CLUBS_PUBLIC_DAVID":   {"x": 35, "y": 320, "n": CONTEXT_N["CLUBS_PUBLIC_LIB"]},
    "CLUBS_PUBLIC_POLICE":  {"x": 35, "y": 370, "n": CONTEXT_N["CLUBS_PUBLIC_LIB"]},
    "CLUBS_PUBLIC_ECONOMICS":{"x": 35, "y": 420, "n": CONTEXT_N["CLUBS_PUBLIC_LIB"]},
   
       
    # פקודות הפעלה בדף בקרת אזורים -אזור ציבורי -ביטול חיישן תנועה D1
    # ==כפתורי טוגל (רצועה 1 ו-2)==
    "D1_SHABBAT_TOGGLE": {"x": 93, "y": 248, "n": "00330000000000000000"}, #שעון ביטול חיישן בשבתות/חגים
    "D1_CLUBS_TOGGLE":   {"x": 96, "y": 451, "n": "00330000000000000000"}, # "אין כניסה למועדונים"
    # == ביטול/הפעלה D1==
    # בנים
    "D1_BOYS_ON":  {"x": 782, "y": 647, "n": "00330000000000000000"},
    "D1_BOYS_OFF": {"x": 837, "y": 647, "n": "00330000000000000000"},
    # בנות
    "D1_GIRLS_ON": {"x": 782, "y": 687, "n": "00330000000000000000"},
    "D1_GIRLS_OFF":{"x": 837, "y": 687, "n": "00330000000000000000"},
    # ציבורי
    "D1_PUB_ON":   {"x": 782, "y": 717, "n": "00330000000000000000"},
    "D1_PUB_OFF":  {"x": 837, "y": 717, "n": "00330000000000000000"},    
}

# --- קואורדינטות טאבים ---
TAB_COORDS = {
    # --- קואורדינטות טאבים (בתוך מסכי הסטטוס) ---
    "TAB_BOYS":    {"x": 233, "y": 73},
    "TAB_GIRLS":   {"x": 168, "y": 73},
    "TAB_PUBLIC":  {"x": 102, "y": 73},
    "TAB_SHABBAT": {"x": 36, "y": 73},
    
    # --- קואורדינטות טאבים (בתוך מסכי בקרת בנים ובקרת בנות) ---
        "TAB_AC1": {"x": 265, "y": 117},
    "TAB_AC2": {"x": 207, "y": 118},
    "TAB_ROOMS": {"x": 150, "y": 117},
    "TAB_WC": {"x": 92, "y": 118},
    "TAB_HEATER": {"x": 33, "y": 118},
}


# =================================================================
#            *** הגדרות פקודות חזרה (BACK_CONFIG) ***
# =================================================================

# הקואורדינטות הפיזיות של כפתור ה-BACK במסך של הבקר
BACK_X = 931
BACK_Y = 73

# מפה זו קובעת לאן "יורה" כפתור החזרה.
# אנחנו יוצרים אותה אוטומטית מתוך CONTEXT_N כדי שכל דף במערכת יוכל להיות "יעד" לחזרה.
BACK_CONFIG = {}

for key, n_value in CONTEXT_N.items():
    BACK_CONFIG[key] = {
        "x": BACK_X, 
        "y": BACK_Y, 
        "n": n_value
    }

# קואורדינטות כלליות (למשל כפתור בית)
COMMON_COORDS = {
    "HOME_ICON": {"x": 20, "y": 20}
    }
    
# הגדרות מקלדת עבור לוגין פיזי
KBD_START_X = 120
KBD_Y = 230
KBD_STEP = 40
KBD_DEFAULT_N = "00010001000000000000"

# נקודות חתימה לזיהוי דפים (פיקסל ייחודי לכל מסך כדי לוודא שהניווט הצליח)
PAGE_SIGNATURES = {
    "MAIN": {"x": 270, "y": 17, "color": (255, 255, 255)}, # פיקסל לבן ב-User מעיד על לוגין
}