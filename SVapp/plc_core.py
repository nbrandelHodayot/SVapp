import sys, os, requests, time, re, logging, io
from PIL import Image
from requests.auth import HTTPBasicAuth

# הוספת נתיב העבודה כדי למנוע שגיאות Import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config_app as config
import monitor_config

logger = logging.getLogger(__name__)

# ==========================================
# 1. הגדרות ומיפויים (Reverse Mapping)
# ==========================================

# המילון ההפוך שמאפשר לשרת לדעת איזה דף מוצג לפי ה-N שמתקבל מהבקר
N_TO_PAGE_NAME = {v: k for k, v in config.CONTEXT_N.items()}

# הגדרת Session לחיבור רציף ומהיר מול הבקר
session = requests.Session()
session.auth = HTTPBasicAuth(config.CONTROLLER_USERNAME, config.CONTROLLER_PASSWORD)

# Headers שמחקים דפדפן כדי למנוע חסימות מהבקר
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": config.REFERER,
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Connection": "keep-alive"
}

# ==========================================
# 2. פונקציות עזר (צבעים ותמונות)
# ==========================================

def get_pixel_status(r, g, b):
    """זיהוי מצב נורה לפי צבע פיקסל (ירוק=ON, אדום=OFF)"""
    if g > 140 and r < 130 and b < 130: return "ON"
    if r > 130 and g < 135 and b < 135: return "OFF"
    return "UNKNOWN"

def fetch_plc_image():
    """משיכת צילום מסך מהבקר עם חתימת זמן למניעת Cache"""
    timestamp = int(time.time() * 1000)
    url = f"http://{config.REMOTE_IP}/CF/CAPTURE/CapVGA.BMP?d={timestamp}"
    try:
        response = session.get(url, headers=BROWSER_HEADERS, timeout=5)
        if response.status_code == 200 and len(response.content) > 5000:
            return response.content
        logger.warning(f"PLC Image fetch failed: {response.status_code}")
    except Exception as e:
        logger.error(f"Network error fetching PLC image: {e}")
    return None

def get_plc_system_time():
    """משיכת השעה המדויקת מהבקר (לשעון ב-Web)"""
    try:
        res = session.get(f"http://{config.REMOTE_IP}/detail.html", timeout=5)
        match = re.search(r'\d{2}:\d{2}:\d{2}', res.text)
        return match.group(0) if match else None
    except Exception as e:
        logger.debug(f"Could not fetch PLC time: {e}")
        return None

# ==========================================
# 3. ליבת השליטה (קואורדינטות ולחיצות)
# ==========================================

def send_physical_click(x, y, n_value, debug_name="Unknown"):
    """הפונקציה הבסיסית ששולחת את פקודת ה-CGI לבקר"""
    url = f"http://{config.REMOTE_IP}/cgi-bin/remote_mouse.cgi?pos_x={x},pos_y={y},n={n_value}"
    try:
        response = session.get(url, headers={"Referer": config.REFERER}, timeout=10)
        logger.info(f"Click Sent: {debug_name} ({x}, {y}) [N={n_value}]")
        return {"status": "success"}, 200
    except Exception as e:
        logger.error(f"Click failed {debug_name}: {e}")
        return {"status": "error", "message": str(e)}, 500

def get_coords_dynamic(action):
    """מפענח פעולה (Action) לסט של קואורדינטות וערך N"""
    
    # א. בדיקת פקודת חזרה (Back)
    if action.startswith("BACK_"):
        ctx = action.replace("BACK_", "")
        return config.BACK_CONFIG.get(ctx)

    # ב. בדיקת ניווט טאבים (למשל STATUS_BOYS/TAB_GIRLS)
    if "/" in action:
        context_name, sub_action = action.split("/", 1)
        target_n = config.CONTEXT_N.get(context_name)
        coords = config.TAB_COORDS.get(sub_action) or config.COMMANDS.get(sub_action)
        if coords and target_n:
            return {"x": coords["x"], "y": coords["y"], "n": target_n}

    # ג. מקלדת נומרית (סיסמא)
    if action.startswith("KEY_") and action != "KEY_ENT":
        digit = action.split("_")[1]
        if digit.isdigit():
            num = int(digit)
            pos = num if num != 0 else 10
            return {
                "x": config.KBD_START_X + ((pos - 1) * config.KBD_STEP),
                "y": config.KBD_Y,
                "n": config.CONTEXT_N.get("LOGIN", "00010001000000000000")
            }

    # ד. בדיקה במילון הפקודות הכללי
    if action in config.COMMANDS:
        res = config.COMMANDS[action].copy()
        if 'n' not in res:
            res['n'] = config.CONTEXT_N.get(action, config.CONTEXT_N.get("MAIN"))
        return res

    # ה. כפתורי מערכת קבועים
    special = {
        "WAKE_UP": {"x": 480, "y": 240, "n": config.CONTEXT_N.get("WAKE_UP")},
        "USER_BUTTON": {"x": 218, "y": 20, "n": config.CONTEXT_N.get("MAIN")},
        "DOWN_ARROW": {"x": 520, "y": 140, "n": config.CONTEXT_N.get("LOGIN")},
        "KEY_ENT": {"x": 480, "y": 398, "n": config.CONTEXT_N.get("LOGIN")}
    }
    return special.get(action)

def send_physical_click_by_action(full_action):
    """הפונקציה המרכזית לביצוע לחיצה לפי שם פעולה"""
    coords = get_coords_dynamic(full_action)
    if coords:
        return send_physical_click(coords['x'], coords['y'], coords['n'], full_action)
    logger.error(f"Action mapping NOT FOUND: {full_action}")
    return {"status": "error", "message": f"Action {full_action} not found"}, 404

# ==========================================
# 4. ניהול סטטוס וסריקת נורות
# ==========================================

def get_multi_status(points_dict, n_val):
    """מעדכן את הבקר לדף מסוים וסורק רשימת נקודות"""
    try:
        # פקודה שקטה כדי לוודא שהבקר בדף הנכון לפני הצילום
        session.get(f"http://{config.REMOTE_IP}/cgi-bin/remote_mouse.cgi?pos_x=1,pos_y=1&n={n_val}", timeout=2)
        time.sleep(0.8)
    except: pass
    
    img_data = fetch_plc_image()
    results = {name: "UNKNOWN" for name in points_dict.keys()}
    if not img_data: return results

    try:
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        for name, (x, y) in points_dict.items():
            try:
                r, g, b = img.getpixel((x, y))
                results[name] = get_pixel_status(r, g, b)
            except: continue
        return results
    except Exception as e:
        logger.error(f"Error analyzing status image: {e}")
        return results

def fetch_plc_status(area):
    """מביא סטטוס נורות בצורה חסינה לטעויות בשמות משתנים או במבנה המילון"""
    area = area.lower()
    
    # 1. מיפוי שמות אפשריים למשתנים ב-monitor_config
    possible_attr_names = [
        f"MONITOR_POINTS_STATUS_{area.upper()}",
        f"MONITOR_POINTS_{area.upper()}",
        f"STATUS_{area.upper()}"
    ]
    
    p_root = {}
    for attr in possible_attr_names:
        p_root = getattr(monitor_config, attr, {})
        if p_root: break # מצאנו משהו, עוצרים

    # 2. חילוץ הנקודות (טיפול במבנה מקונן או שטוח)
    # אם המילון מכיל את שם האזור כמפתח (כמו בבנים), ניקח אותו. אם לא - ניקח את כל המילון.
    if isinstance(p_root, dict):
        p = p_root.get(area, p_root)
    else:
        p = {}

    # 3. הבאת ערך ה-N מהקונפיג
    n = config.CONTEXT_N.get(f"STATUS_{area.upper()}")

    # לוג לצורך ניפוי שגיאות אם עדיין לא עובד
    if not n or not p:
        logger.warning(f"Status Scan: Missing data for {area}. Points found: {bool(p)}, N found: {bool(n)}")
        return {}

    return get_multi_status(p, n)

# ==========================================
# 5. לוגיקת לוגין וזיהוי מסך
# ==========================================

def get_screen_n_by_pixel_check():
    """מזהה איפה הבקר נמצא פיזית לפי צבע פיקסל ייחודי"""
    img_data = fetch_plc_image()
    if not img_data: return None
    try:
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        for page_name, sig in config.PAGE_SIGNATURES.items():
            r, g, b = img.getpixel((sig["x"], sig["y"]))
            color = sig["color"]
            if abs(r-color[0]) < 10 and abs(g-color[1]) < 10 and abs(b-color[2]) < 10:
                return config.CONTEXT_N.get(page_name)
        return None
    except: return None

def is_eli_physically_connected():
    """בודק אם המשתמש Eli מחובר (פיקסלים לבנים בכותרת)"""
    img_data = fetch_plc_image()
    if not img_data: return True
    try:
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        sig = config.PAGE_SIGNATURES.get("MAIN", {"x": 270, "y": 17})
        r, g, b = img.getpixel((sig["x"], sig["y"]))
        # אם הפיקסל לבן, המשתמש מחובר
        return (r > 220 and g > 220 and b > 220)
    except: return True

def perform_physical_login():
    """מבצע את כל רצף הלחיצות להתחברות"""
    logger.info("Starting automated login sequence...")
    # שימוש בשמות הפעולות כפי שהם מוגדרים ב-get_coords_dynamic
    sequence = ["WAKE_UP", "USER_BUTTON", "DOWN_ARROW", "KEY_6", "KEY_6", "KEY_9", "KEY_1", "KEY_1", "KEY_ENT"]
    
    for action in sequence:
        send_physical_click_by_action(action)
        time.sleep(1.2) # השהיה קריטית לתגובת הבקר

def smart_login_sequence():
    """מפעיל לוגין רק אם יש צורך"""
    if not is_eli_physically_connected():
        perform_physical_login()
    else:
        logger.info("Smart Login: Eli is already connected, skipping.")