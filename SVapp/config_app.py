# config_app.py
import socket
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# הגדרת logger
logger = logging.getLogger(__name__)

# טעינת משתני סביבה מקובץ .env בתיקיית secrets
secrets_dir = Path(__file__).parent / "secrets"
env_file = secrets_dir / ".env"
load_dotenv(env_file)

COMPUTER_NAME = socket.gethostname().upper() # הופך הכל לאותיות גדולות למניעת טעויות
# בדיקה גמישה יותר - אם השם מכיל את המחרוזת או שווה לה
SIMULATION_MODE = ("HOD2301-07" in COMPUTER_NAME) 

# שנה ל-True כשאתה בבית, ול-False כשאתה בעבודה
MOCK_MODE = False

logger.info(f"Computer Name: {COMPUTER_NAME}")
logger.info(f"Simulation Mode: {SIMULATION_MODE}")

# --- הגדרות חיבור לבקר ---
REMOTE_IP = "192.168.1.234"

# ============================================
# שכבת אבטחה 1: ממשק הווב של הבקר (HTTP Basic Auth)
# זה נדרש לכל קריאת HTTP לבקר (צילומי מסך, שליחת פקודות)
# ============================================
CONTROLLER_USERNAME = os.getenv("CONTROLLER_WEB_USERNAME")
CONTROLLER_PASSWORD = os.getenv("CONTROLLER_WEB_PASSWORD")

if not CONTROLLER_USERNAME or not CONTROLLER_PASSWORD:
    raise ValueError(
        "CONTROLLER_WEB_USERNAME and CONTROLLER_WEB_PASSWORD must be set in secrets/.env file"
    )

# ============================================
# שכבת אבטחה 2: סיסמת מערכת הבקר עצמו
# זה נדרש לכניסה למערכת הבקר (לוגין פיזי בממשק הבקר)
# ============================================
ACTUAL_SYSTEM_PASSWORD = os.getenv("CONTROLLER_SYSTEM_PASSWORD")

if not ACTUAL_SYSTEM_PASSWORD:
    raise ValueError(
        "CONTROLLER_SYSTEM_PASSWORD must be set in secrets/.env file"
    )

CGI_URL = f"http://{REMOTE_IP}/cgi-bin/remote_mouse.cgi"
REFERER = f"http://{REMOTE_IP}/remote_control_full.html?pic_format=bmp"

# --- אבטחת האפליקציה (Flask) ---
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY must be set in secrets/.env file. "
        "Generate a strong secret key using: python -c 'import secrets; print(secrets.token_hex(32))'"
    )

INACTIVITY_TIMEOUT = 270  # שניות עד לניתוק אוטומטי

# מילון משתמשים לכניסה לממשק הווב
admin_password = os.getenv("APP_USER_ADMIN")
eli_password = os.getenv("APP_USER_ELI")

if not admin_password or not eli_password:
    raise ValueError(
        "APP_USER_ADMIN and APP_USER_ELI must be set in secrets/.env file"
    )

USERS = {
    "admin": admin_password,
    "eli": eli_password
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
    "C_B_S": "00030000000000000000",  # קיצור עבור Control Boys Split (משמש ב-HTML)
    "GIRLS_SPLIT": "00100000000000000000",  # קונטקסט כללי לחלוקה למבנים בנות (משמש לניווט)
    "C_G_S": "00100000000000000000",  # קיצור עבור Control Girls Split
    "GIRLS_SPLIT_1": "00100000000000000000",
    "GIRLS_SPLIT_2": "00110000000000000000",
    "PUBLIC_SPLIT": "00190000000000000000",
    "C_P_S": "00190000000000000000",  # קיצור עבור Control Public Split
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
    
    # =========================================================================
    # פקודות הפעלה בדף "בקרת אזורים - אזור בנים - חלוקה למבנים" (C_B_S / BOYS_SPLIT)
    # הקואורדינטות מחושבות לפי MONITOR_POINTS_CONTROL_SPLIT["boys"]
    # הכפתורים נמצאים משמאל לנורה: ON ב-X-80, OFF ב-X-40 (צריך לבדוק במציאות)
    # =========================================================================
    # בית 1
    "AC_B1_ON": {"x": 759, "y": 186, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(839, 186)
    "AC_B1_OFF": {"x": 799, "y": 186, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B1_ON": {"x": 759, "y": 227, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B1_OFF": {"x": 799, "y": 227, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B1_ON": {"x": 759, "y": 268, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B1_OFF": {"x": 799, "y": 268, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 2
    "AC_B2_ON": {"x": 419, "y": 186, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(499, 186)
    "AC_B2_OFF": {"x": 459, "y": 186, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B2_ON": {"x": 419, "y": 227, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B2_OFF": {"x": 459, "y": 227, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B2_ON": {"x": 419, "y": 268, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B2_OFF": {"x": 459, "y": 268, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 3
    "AC_B3_ON": {"x": 79, "y": 190, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(159, 190)
    "AC_B3_OFF": {"x": 119, "y": 190, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B3_ON": {"x": 79, "y": 228, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B3_OFF": {"x": 119, "y": 228, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B3_ON": {"x": 79, "y": 268, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B3_OFF": {"x": 119, "y": 268, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 4
    "AC_B4_ON": {"x": 759, "y": 354, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(839, 354)
    "AC_B4_OFF": {"x": 799, "y": 354, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B4_ON": {"x": 759, "y": 395, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B4_OFF": {"x": 799, "y": 395, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B4_ON": {"x": 759, "y": 436, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B4_OFF": {"x": 799, "y": 436, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 5
    "AC_B5_ON": {"x": 419, "y": 354, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(499, 354)
    "AC_B5_OFF": {"x": 459, "y": 354, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B5_ON": {"x": 419, "y": 395, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B5_OFF": {"x": 459, "y": 395, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B5_ON": {"x": 419, "y": 436, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B5_OFF": {"x": 459, "y": 436, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 9
    "AC_B9A_ON": {"x": 79, "y": 358, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(159, 358)
    "AC_B9A_OFF": {"x": 119, "y": 358, "n": CONTEXT_N["BOYS_SPLIT"]},
    "AC_B9B_ON": {"x": 79, "y": 399, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(159, 399)
    "AC_B9B_OFF": {"x": 119, "y": 399, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B9_ON": {"x": 79, "y": 440, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B9_OFF": {"x": 119, "y": 440, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B9_ON": {"x": 79, "y": 478, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B9_OFF": {"x": 119, "y": 478, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 11 קומה א'
    "AC_B11AA_ON": {"x": 759, "y": 534, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(839, 534)
    "AC_B11AA_OFF": {"x": 799, "y": 534, "n": CONTEXT_N["BOYS_SPLIT"]},
    "AC_B11AB_ON": {"x": 759, "y": 575, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(839, 575)
    "AC_B11AB_OFF": {"x": 799, "y": 575, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B11A_ON": {"x": 759, "y": 616, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B11A_OFF": {"x": 799, "y": 616, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B11A_ON": {"x": 759, "y": 654, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B11A_OFF": {"x": 799, "y": 654, "n": CONTEXT_N["BOYS_SPLIT"]},
    # בית 11 קומה ב'
    "AC_B11BA_ON": {"x": 419, "y": 534, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(499, 534)
    "AC_B11BA_OFF": {"x": 459, "y": 534, "n": CONTEXT_N["BOYS_SPLIT"]},
    "AC_B11BB_ON": {"x": 419, "y": 575, "n": CONTEXT_N["BOYS_SPLIT"]},  # נורה ב-(499, 575)
    "AC_B11BB_OFF": {"x": 459, "y": 575, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B11B_ON": {"x": 419, "y": 616, "n": CONTEXT_N["BOYS_SPLIT"]},
    "R_B11B_OFF": {"x": 459, "y": 616, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B11B_ON": {"x": 419, "y": 654, "n": CONTEXT_N["BOYS_SPLIT"]},
    "T_B11B_OFF": {"x": 459, "y": 654, "n": CONTEXT_N["BOYS_SPLIT"]},
    
    # =========================================================================
    # פקודות הפעלה בדף "בקרת אזורים - אזור בנות - חלוקה למבנים" (C_G_S)
    # GIRLS_SPLIT_1 (n=00100000000000000000): בתים 7, 8, 10, C23-C26
    # =========================================================================
    # בית 7
    "B7_ACa_ON": {"x": 721, "y": 206, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_ACa_OFF": {"x": 790, "y": 202, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_ACb_ON": {"x": 732, "y": 241, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_ACb_OFF": {"x": 784, "y": 237, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_R_ON": {"x": 729, "y": 279, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_R_OFF": {"x": 781, "y": 279, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_WC_ON": {"x": 728, "y": 321, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B7_WC_OFF": {"x": 775, "y": 326, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # בית 8
    "B8_AC_ON": {"x": 403, "y": 199, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_AC_OFF": {"x": 454, "y": 198, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_R_ON": {"x": 397, "y": 241, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_R_OFF": {"x": 450, "y": 238, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_WC_ON": {"x": 395, "y": 285, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_WC_OFF": {"x": 452, "y": 282, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_H_ON": {"x": 394, "y": 318, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B8_H_OFF": {"x": 450, "y": 319, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # בית 10
    "B10_ACa_ON": {"x": 62, "y": 164, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_ACa_OFF": {"x": 125, "y": 167, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_ACb_ON": {"x": 73, "y": 202, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_ACb_OFF": {"x": 125, "y": 199, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_R_ON": {"x": 75, "y": 243, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_R_OFF": {"x": 127, "y": 162, "n": CONTEXT_N["GIRLS_SPLIT_1"]},  # ייתכן שצריך לבדוק
    "B10_WC_ON": {"x": 399, "y": 276, "n": CONTEXT_N["GIRLS_SPLIT_1"]},  # ייתכן שצריך לבדוק
    "B10_WC_OFF": {"x": 129, "y": 284, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_H_ON": {"x": 70, "y": 324, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "B10_H_OFF": {"x": 118, "y": 321, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C20
    "C20_AC_ON": {"x": 721, "y": 418, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C20_AC_OFF": {"x": 781, "y": 418, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C20_ROOMS_ON": {"x": 725, "y": 453, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C20_ROOMS_OFF": {"x": 787, "y": 453, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C21
    "C21_AC_ON": {"x": 398, "y": 418, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C21_AC_OFF": {"x": 454, "y": 418, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C21_ROOMS_ON": {"x": 401, "y": 453, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C21_ROOMS_OFF": {"x": 454, "y": 453, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C22
    "C22_AC_ON": {"x": 67, "y": 418, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C22_AC_OFF": {"x": 130, "y": 418, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C22_ROOMS_ON": {"x": 64, "y": 453, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C22_ROOMS_OFF": {"x": 117, "y": 453, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C23 - עמודה שמאלית (כמו C20), שורה שנייה
    "C23_AC_ON": {"x": 721, "y": 546, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C23_AC_OFF": {"x": 781, "y": 546, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C23_ROOMS_ON": {"x": 725, "y": 596, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C23_ROOMS_OFF": {"x": 787, "y": 596, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C24 - עמודה אמצעית (כמו C21), שורה שנייה (Y כמו C23)
    "C24_AC_ON": {"x": 398, "y": 546, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C24_AC_OFF": {"x": 454, "y": 546, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C24_ROOMS_ON": {"x": 401, "y": 596, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C24_ROOMS_OFF": {"x": 454, "y": 596, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C25 - עמודה ימנית (כמו C22), שורה שנייה (Y כמו C23)
    "C25_AC_ON": {"x": 67, "y": 546, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C25_AC_OFF": {"x": 130, "y": 546, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C25_ROOMS_ON": {"x": 64, "y": 596, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C25_ROOMS_OFF": {"x": 117, "y": 596, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    # C26
    "C26_AC_ON": {"x": 723, "y": 690, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C26_AC_OFF": {"x": 780, "y": 696, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C26_ROOMS_ON": {"x": 735, "y": 732, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    "C26_ROOMS_OFF": {"x": 781, "y": 735, "n": CONTEXT_N["GIRLS_SPLIT_1"]},
    
    # =========================================================================
    # GIRLS_SPLIT_2 (n=00110000000000000000): בתים 12a, 12b, 12c, 13a, 13b, 13c
    # =========================================================================
    # בית 12a
    "B12a_AC_ON": {"x": 733, "y": 220, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12a_AC_OFF": {"x": 124, "y": 247, "n": CONTEXT_N["GIRLS_SPLIT_2"]},  # ייתכן שצריך לבדוק
    "B12a_R_ON": {"x": 724, "y": 259, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12a_R_OFF": {"x": 783, "y": 257, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12a_WC_ON": {"x": 731, "y": 297, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12a_WC_OFF": {"x": 777, "y": 301, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12a_H_ON": {"x": 727, "y": 335, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12a_H_OFF": {"x": 786, "y": 336, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    # בית 12b
    "B12b_AC_ON": {"x": 390, "y": 216, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12b_AC_OFF": {"x": 397, "y": 299, "n": CONTEXT_N["GIRLS_SPLIT_2"]},  # ייתכן שצריך לבדוק
    "B12b_WC_ON": {"x": 397, "y": 299, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12b_WC_OFF": {"x": 453, "y": 295, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12b_R_ON": {"x": 401, "y": 259, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12b_R_OFF": {"x": 458, "y": 260, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    # בית 12c
    "B12c_AC_ON": {"x": 70, "y": 324, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12c_AC_OFF": {"x": 128, "y": 327, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12c_R_ON": {"x": 75, "y": 262, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12c_R_OFF": {"x": 453, "y": 262, "n": CONTEXT_N["GIRLS_SPLIT_2"]},  # ייתכן שצריך לבדוק
    "B12c_WC_ON": {"x": 67, "y": 297, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B12c_WC_OFF": {"x": 129, "y": 301, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    # בית 13a
    "B13a_AC_ON": {"x": 723, "y": 487, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_AC_OFF": {"x": 777, "y": 490, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_R_ON": {"x": 729, "y": 528, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_R_OFF": {"x": 782, "y": 525, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_WC_ON": {"x": 726, "y": 569, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_WC_OFF": {"x": 789, "y": 570, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_H_ON": {"x": 728, "y": 610, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13a_H_OFF": {"x": 780, "y": 604, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    # בית 13b
    "B13b_AC_ON": {"x": 394, "y": 494, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13b_AC_OFF": {"x": 449, "y": 487, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13b_R_ON": {"x": 396, "y": 531, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13b_R_OFF": {"x": 451, "y": 528, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13b_WC_ON": {"x": 395, "y": 572, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13b_WC_OFF": {"x": 450, "y": 567, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    # בית 13c
    "B13c_AC_ON": {"x": 64, "y": 495, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13c_AC_OFF": {"x": 122, "y": 488, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13c_R_ON": {"x": 398, "y": 527, "n": CONTEXT_N["GIRLS_SPLIT_2"]},  # ייתכן שצריך לבדוק
    "B13c_R_OFF": {"x": 117, "y": 528, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13c_WC_ON": {"x": 73, "y": 573, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
    "B13c_WC_OFF": {"x": 120, "y": 574, "n": CONTEXT_N["GIRLS_SPLIT_2"]},
}

# --- קואורדינטות טאבים ---
TAB_COORDS = {
    # --- קואורדינטות טאבים (בתוך מסכי הסטטוס) ---
    "TAB_BOYS":    {"x": 233, "y": 73},
    "TAB_GIRLS":   {"x": 168, "y": 73},
    "TAB_PUBLIC":  {"x": 102, "y": 73},
    "TAB_SHABBAT": {"x": 36, "y": 73},
    
    # --- קואורדינטות טאבים -שעוני שבת בנים ---
    "BOYS_SHABBAT_AC1": {"x": 265, "y": 117},
    "BOYS_SHABBAT_AC2": {"x": 207, "y": 118},
    "BOYS_SHABBAT_ROOM_LIGHTS": {"x": 150, "y": 117},
    "BOYS_SHABBAT_BATHROOM_LIGHTS": {"x": 92, "y": 118},
    "BOYS_SHABBAT_HEATER": {"x": 33, "y": 118},

    # --- קואורדינטות טאבים -שעוני שבת בנות ---
    "GIRLS_SHABBAT_AC1": {"x": 265, "y": 117},
    "GIRLS_SHABBAT_AC2": {"x": 207, "y": 118},
    "GIRLS_SHABBAT_ROOM_LIGHTS": {"x": 150, "y": 117},
    "GIRLS_SHABBAT_BATHROOM_LIGHTS": {"x": 92, "y": 118},
    "GIRLS_SHABBAT_HEATER": {"x": 33, "y": 118},

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