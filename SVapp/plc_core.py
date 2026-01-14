import sys, os, requests, time, re, logging, io
from PIL import Image
from requests.auth import HTTPBasicAuth
import random
import datetime

# הוספת נתיב העבודה כדי למנוע שגיאות Import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config_app
import monitor_config
from monitor_config import (
    SHABBAT_TIME_Y_BASE, SHABBAT_STEP_Y, START_TIME_X, STOP_TIME_X,
    DIGIT_W, DIGIT_H, DIGIT_MAPS, PLC_GREEN, STATUS_POINT_X,
    SHABBAT_BUILDINGS_X, SHABBAT_DAYS_X, SHABBAT_CLOCK_LAYOUT
)

logger = logging.getLogger(__name__)

# ==========================================
# 1. הגדרות ומיפויים (Reverse Mapping)
# ==========================================

# המילון ההפוך שמאפשר לשרת לדעת איזה דף מוצג לפי ה-N שמתקבל מהבקר
N_TO_PAGE_NAME = {v: k for k, v in config_app.CONTEXT_N.items()}

# הגדרת Session לחיבור רציף ומהיר מול הבקר
session = requests.Session()
session.auth = HTTPBasicAuth(config_app.CONTROLLER_USERNAME, config_app.CONTROLLER_PASSWORD)

# Headers שמחקים דפדפן כדי למנוע חסימות מהבקר
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": config_app.REFERER,
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
    url = f"http://{config_app.REMOTE_IP}/CF/CAPTURE/CapVGA.BMP?d={timestamp}"
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
        res = session.get(f"http://{config_app.REMOTE_IP}/detail.html", timeout=5)
        match = re.search(r'\d{2}:\d{2}:\d{2}', res.text)
        return match.group(0) if match else None
    except Exception as e:
        logger.debug(f"Could not fetch PLC time: {e}")
        return None

def get_plc_screenshot():
    """משיכת תמונת המסך הנוכחית מהבקר לצורך פענוח"""
    try:
        url = f"http://{config_app.REMOTE_IP}/remote_control_full.html?pic_format=bmp"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content))
    except Exception as e:
        logger.error(f"Failed to capture PLC screenshot: {e}")
    return None
    



# ==========================================
# 3. ליבת השליטה (קואורדינטות ולחיצות)
# ==========================================

def send_physical_click(x, y, n, debug_name="Unknown"):
    """
    שולחת פקודת לחיצה פיזית לבקר.
    x, y: קואורדינטות הלחיצה.
    n: הקונטקסט (הדף) שבו הלחיצה צריכה להתבצע.
    """
    if getattr(config_app, 'SIMULATION_MODE', False):
        logger.info(f"[SIMULATION] Click at ({x}, {y}) with N={n} [{debug_name}]")
        return {"status": "success"}, 200

    # בניית ה-URL עם הפרמטרים הנכונים עבור הבקר
    url = f"http://{config_app.REMOTE_IP}/cgi-bin/remote_mouse.cgi?pos_x={x},pos_y={y},n={n}"
    
    try:
        # שליחת הבקשה עם ה-Referer שהבקר דורש
        response = session.get(url, headers={"Referer": config_app.REFERER}, timeout=10)
        
        if response.ok:
            logger.info(f"Click Sent: {debug_name} ({x}, {y}) [N={n}]")
            return {"status": "success"}, 200
        else:
            logger.error(f"PLC returned error: {response.status_code} for {debug_name}")
            return {"status": "error", "message": f"PLC Error {response.status_code}"}, 500
            
    except Exception as e:
        logger.error(f"Click failed {debug_name}: {e}")
        return {"status": "error", "message": str(e)}, 500

# ==========================================
# 4. ניהול סטטוס וסריקת נורות
# ==========================================

def get_multi_status(points_dict, n_val):
    """מעדכן את הבקר לדף מסוים וסורק רשימת נקודות"""
    try:
        # פקודה שקטה כדי לוודא שהבקר בדף הנכון לפני הצילום
        session.get(f"http://{config_app.REMOTE_IP}/cgi-bin/remote_mouse.cgi?pos_x=1,pos_y=1&n={n_val}", timeout=2)
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
    """
    פונקציה מקורית ויציבה לדפי סטטוס (נורות).
    מחזירה מילון שטוח של ON/OFF בלבד.
    """
    area_upper = area.upper()
    area_lower = area.lower()

    if getattr(config_app, 'SIMULATION_MODE', False):
        p_root = getattr(monitor_config, f"MONITOR_POINTS_STATUS_{area_upper}", {})
        points_dict = p_root.get(area_lower, p_root) if isinstance(p_root, dict) else {}
        return {name: random.choice(["ON", "OFF"]) for name in points_dict.keys()}

    # מצב אמת - קריאה לסטטוס נורות
    possible_attr_names = [f"MONITOR_POINTS_STATUS_{area_upper}", f"MONITOR_POINTS_{area_upper}"]
    p_root = {}
    for attr in possible_attr_names:
        p_root = getattr(monitor_config, attr, {})
        if p_root: break

    p = p_root.get(area_lower, p_root) if isinstance(p_root, dict) else {}
    n = config_app.CONTEXT_N.get(f"STATUS_{area_upper}")

    if not n or not p:
        return {}

    try:
        return get_multi_status(p, n)
    except Exception as e:
        logger.error(f"Real-time scan failed: {e}")
        return {}

def fetch_shabbat_data(area, context_key):
    """
    מושכת תמונה מהבקר ומפענחת את כל נתוני שעוני השבת עבור הטאב הנבחר.
    """
    import datetime as dt
    area_upper = area.upper()
    img = None
    
    try:
        # 1. משיכת התמונה העדכנית מהבקר
        response = session.get(config_app.CGI_URL, timeout=5)
        if response.status_code == 200 and len(response.content) > 0:
            img = Image.open(io.BytesIO(response.content)).convert('RGB')
        else:
            logger.error(f"Failed to fetch image from PLC: Status {response.status_code}")
            return {"clocks": [], "time": "--:--", "error": "Connection error"}

        # 2. פענוח נתוני השעונים (זמנים, ימים ומבנים)
        clocks_list = parse_shabbat_clocks(img)

        # 3. החזרת הנתונים ל-Frontend
        return {
            "clocks": clocks_list, # הרשימה שסרקנו
            "time": dt.datetime.now().strftime("%H:%M:%S"),
            "area": area_upper
        }

    except Exception as e:
        logger.error(f"Error fetching shabbat data: {e}")
        return {"clocks": [], "time": "--:--", "error": str(e)}
        
# ==========================================
# 5. לוגיקת לוגין וזיהוי מסך
# ==========================================

def get_screen_n_by_pixel_check():
    """מזהה איפה הבקר נמצא פיזית לפי צבע פיקסל ייחודי"""
    img_data = fetch_plc_image()
    if not img_data: return None
    try:
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        for page_name, sig in config_app.PAGE_SIGNATURES.items():
            r, g, b = img.getpixel((sig["x"], sig["y"]))
            color = sig["color"]
            if abs(r-color[0]) < 10 and abs(g-color[1]) < 10 and abs(b-color[2]) < 10:
                return config_app.CONTEXT_N.get(page_name)
        return None
    except: return None

def is_eli_physically_connected():
    """
    בדיקת חיבור דיפרנציאלית (הצלבת נתונים):
    מחובר: X=270 (16-27) לבן  ו- X=284 (20-27) אפור.
    מנותק: X=270 (16-19) אפור ו- X=284 (20-27) לבן.
    """
    if getattr(config_app, 'SIMULATION_MODE', False):
        return True

    try:
        # משיכת תמונה טרייה
        img_data = fetch_plc_image()
        if not img_data:
            return False
            
        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        
        # פונקציות עזר לזיהוי צבעים
        def is_white(p): return p[0] > 230 and p[1] > 230 and p[2] > 230
        def is_gray(p):  return p[0] < 80  and p[1] < 80  and p[2] < 80

        # דגימת נקודות מפתח
        p270_16 = img.getpixel((270, 16))
        p284_20 = img.getpixel((284, 20))

        # 1. בדיקת מצב "מחובר" (הצלבה חיובית)
        if is_white(p270_16) and is_gray(p284_20):
            return True
            
        # 2. בדיקת מצב "מנותק" (הצלבה שלילית)
        if is_gray(p270_16) and is_white(p284_20):
            logger.warning("Eli State: Physically Disconnected (Login Page pattern detected).")
            return False

        # מקרה קצה (דף לא מזוהה)
        logger.warning(f"Eli State: Ambiguous. Pixels: 270,16={p270_16}, 284,20={p284_20}")
        return False

    except Exception as e:
        logger.error(f"Error in physical connection check: {e}")
        return False

def get_coords_dynamic(action):
    """מפענח פעולה לקואורדינטות - כולל תמיכה בטאבים של שעוני שבת"""
    if not action: return None

    # א. כפתורי מערכת קבועים
    special = {
        "WAKE_UP": {"x": 509, "y": 391, "n": config_app.CONTEXT_N.get("WAKE_UP")},
        "USER_BUTTON": {"x": 218, "y": 20, "n": config_app.CONTEXT_N.get("MAIN")},
        "DOWN_ARROW": {"x": 520, "y": 140, "n": config_app.CONTEXT_N.get("LOGIN")},
        "KEY_ENT": {"x": 480, "y": 398, "n": config_app.CONTEXT_N.get("LOGIN")}
    }
    if action in special:
        return special[action]

    # ב. מקלדת נומרית
    if action.startswith("KEY_") and action != "KEY_ENT":
        digit = action.split("_")[1]
        if digit.isdigit():
            num = int(digit)
            pos = num if num != 0 else 10
            return {
                "x": config_app.KBD_START_X + ((pos - 1) * config_app.KBD_STEP),
                "y": config_app.KBD_Y,
                "n": config_app.CONTEXT_N.get("LOGIN")
            }

    # ג. ניווט טאבים או פקודות מורכבות (CONTEXT/SUB_ACTION)
    if "/" in action:
        try:
            context_name, sub_action = action.split("/", 1)
            target_n = config_app.CONTEXT_N.get(context_name)
            
            # חיפוש הקואורדינטות בטאבים או בפקודות
            tab_coords = getattr(config_app, 'TAB_COORDS', {})
            commands = getattr(config_app, 'COMMANDS', {})
            coords = tab_coords.get(sub_action) or commands.get(sub_action)
            
            if coords:
                res = coords.copy()
                # אם ה-N לא מוגדר בטאב עצמו, ניקח את ה-N של הקונטקסט
                if 'n' not in res:
                    res['n'] = target_n
                return res
        except Exception as e:
            logger.error(f"Error parsing complex action {action}: {e}")

    # ד. בדיקה במילונים סטטיים (TAB_COORDS, BUTTONS, COMMANDS)
    # הוספנו כאן את TAB_COORDS כדי לאפשר לחיצה ישירה אם נשלח רק 'TAB_AC1'
    tab_coords = getattr(config_app, 'TAB_COORDS', {})
    buttons = getattr(config_app, 'BUTTONS', {})
    commands = getattr(config_app, 'COMMANDS', {})
    
    static_btn = tab_coords.get(action) or buttons.get(action) or commands.get(action)
    
    if static_btn:
        res = static_btn.copy()
        if 'n' not in res:
            # ברירת מחדל ל-N אם לא צוין
            res['n'] = config_app.CONTEXT_N.get(action, config_app.CONTEXT_N.get("MAIN"))
        return res

    # ה. פקודת חזרה
    if action.startswith("BACK_"):
        clean_action = action.replace("BACK_", "")
        back_config = getattr(config_app, 'BACK_CONFIG', {})
        target = back_config.get(clean_action)
        if target: return target

    return None
    

def send_physical_click_by_action(action_name, context_name=None):
    """ביצוע לחיצה עם ניהול N חכם - גרסה חסינה"""
    coords = get_coords_dynamic(action_name)

    if not coords or 'x' not in coords:
        logger.error(f"Action '{action_name}' unknown or coordinate missing.")
        return {"status": "error", "message": f"Unknown action: {action_name}"}, 400

    x = coords.get('x')
    y = coords.get('y')
    
    # חישוב ה-N הנכון
    n_val = coords.get('n')
    if not n_val and context_name:
        n_val = config_app.CONTEXT_N.get(context_name)
    if not n_val:
        n_val = get_screen_n_by_pixel_check() or config_app.CONTEXT_N.get("MAIN")

    logger.info(f"CLICK: {action_name} at ({x}, {y}) | N: {n_val}")
    
    return send_physical_click(x, y, n_val, debug_name=action_name)

def get_current_page_name():
    """מזהה את שם הדף הנוכחי לפי ה-N הפיזי"""
    try:
        current_n = get_screen_n_by_pixel_check()
        if not current_n: return "INDEX"
        return N_TO_PAGE_NAME.get(current_n, "INDEX")
    except Exception as e:
        logger.error(f"Error auto-detecting page: {e}")
        return "INDEX"


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

def read_shabbat_clock_time(img, clock_index, type="ON"):
    """
    img: אובייקט התמונה מהבקר
    clock_index: 0-3 (עבור שעונים א-ד)
    """
    if config_app.SIMULATION_MODE:
        return "08:00" if type == "ON" else "16:30"

    base_y = SHABBAT_CLOCKS_BASE_Y[clock_index]
    layout = SHABBAT_CLOCK_LAYOUT
    
    time_digits = []
    
    for x_pos in layout["DIGITS_X"]:
        # גזירת ריבוע הספרה
        y_pos = base_y + layout["DIGIT_Y_OFFSET"]
        digit_crop = img.crop((x_pos, y_pos, x_pos + layout["DIGIT_W"], y_pos + layout["DIGIT_H"]))
        
        # זיהוי הספרה לפי השוואת פיקסלים (נשתמש בנתונים שתביא)
        digit = identify_digit_from_crop(digit_crop)
        time_digits.append(str(digit))
    
    return f"{time_digits[0]}{time_digits[1]}:{time_digits[2]}{time_digits[3]}"

def identify_digit_from_crop(crop_img):
    """מקבלת תמונה של 10x15 ומחזירה את הספרה המזוהה"""
    # הופך את התמונה לשחור-לבן כדי שיהיה קל לזהות
    bw_img = crop_img.convert('L').point(lambda x: 0 if x < 128 else 255, '1')
    
    for digit, pattern in monitor_config.DIGIT_MAPS.items():
        is_match = True
        for row, black_pixels in pattern:
            for x in range(10):
                pixel = bw_img.getpixel((x, row))
                # אם הפיקסל אמור להיות שחור (0) אבל הוא לבן (255)
                if x in black_pixels and pixel == 255:
                    is_match = False; break
                # אם הפיקסל אמור להיות לבן אבל הוא שחור
                if x not in black_pixels and pixel == 0:
                    is_match = False; break
            if not is_match: break
        
        if is_match:
            return digit
    return "?" # אם לא זיהה
    
# ==========================================
# 6. לוגיקת שעוני שבת
# ==========================================
def get_shabbat_status_data(context_name):
    """
    פונקציית מעטפת: ניווט לדף הנכון בבקר, צילום ופענוח.
    """
    target_n = config_app.CONTEXT_N.get(context_name)
    if not target_n:
        return {"success": False, "error": f"Context {context_name} unknown"}

    try:
        # 1. וידוא שהבקר נמצא בדף הנכון לפני הצילום
        current_n = get_screen_n_by_pixel_check()
        if current_n != target_n:
            logger.info(f"Navigating PLC to {context_name} (N: {target_n})")
            send_physical_click(1, 1, target_n) # לחיצת ניווט שקטה
            time.sleep(0.7) # המתנה לטעינת מסך

        # 2. צילום תמונה
        img_data = fetch_plc_image()
        if not img_data:
            return {"success": False, "error": "PLC image fetch failed"}

        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        
        # 3. פענוח
        clocks = parse_shabbat_clocks(img)
        return {"success": True, "clocks": clocks}

    except Exception as e:
        logger.error(f"Error in get_shabbat_status_data: {e}")
        return {"success": False, "error": str(e)}

def is_pixel_marked(bw_img, x, y):
    """
    בודק אם פיקסל מסוים 'מסומן' (שחור).
    בתמונת ה-BW שלנו: 0 = שחור (טקסט/סימון), 255 = לבן (רקע).
    """
    try:
        return bw_img.getpixel((x, y)) == 0
    except:
        return False

def parse_digit(bw_img, x_start, y_start):
    """מזהה ספרה אחת לפי השוואה למפות הפיקסלים ב-monitor_config"""
    for digit, pattern in DIGIT_MAPS.items():
        is_match = True
        for row, black_pixels in pattern:
            for x_offset in range(10): # רוחב ספרה ממוצע
                pixel = bw_img.getpixel((x_start + x_offset, y_start + row))
                # אם הפיקסל אמור להיות שחור (0) אך הוא לבן (255)
                if x_offset in black_pixels and pixel == 255:
                    is_match = False; break
                # אם הפיקסל אמור להיות לבן (255) אך הוא שחור (0)
                if x_offset not in black_pixels and pixel == 0:
                    is_match = False; break
            if not is_match: break
        
        if is_match:
            return digit
    return "?"

def parse_time_at(bw_img, x_start, y_row):
    """מפענח מחרוזת זמן HH:MM מנקודת התחלה בשורה"""
    offsets = [0, 12, 30, 42] # רווחים לספרות (כולל דילוג על הנקודתיים)
    time_str = ""
    for i, offset in enumerate(offsets):
        digit = parse_digit(bw_img, x_start + offset, y_row)
        time_str += str(digit)
        if i == 1: time_str += ":"
    return time_str

def parse_days_at(bw_img, x_start, y_row):
    """מזהה אילו ימים (א-ש) מסומנים ב-V"""
    days_labels = ["א", "ב", "ג", "ד", "ה", "ו", "ש"]
    day_spacing = 15 # המרחק בין ריבועי הימים
    active = []
    for i, label in enumerate(days_labels):
        if is_pixel_marked(bw_img, x_start + (i * day_spacing), y_row + 5):
            active.append(label)
    return active

def parse_buildings_at(bw_img, y_row):
    """מזהה אילו מבנים מסומנים בשורה לפי BUILDINGS_MAP"""
    active = []
    for name, x in monitor_config.BUILDINGS_MAP.items():
        if is_pixel_marked(bw_img, x, y_row + 5):
            active.append(name)
    return active

def is_pixel_active_green(pixel):
    """בודק האם הפיקסל בטווח הירוק המדויק (0, 250-255, 0)"""
    r, g, b = pixel
    return r == 0 and 250 <= g <= 255 and b == 0

def get_digit_at(img, x_start, y_start):
    best_digit = "?"
    max_score = -1
    
    # דגימה מהירה של האזור (10x15)
    actual = []
    for r in range(15):
        for c in range(10):
            p = img.getpixel((x_start + c, y_start + r))
            actual.append(1 if sum(p) < 400 else 0) # סף רגישות גבוה יותר

    for digit, pattern in monitor_config.DIGIT_MAPS.items():
        score = 0
        pattern_flat = [0] * 150
        # הפיכת ה-pattern לרשימה שטוחה להשוואה מהירה
        for row_idx, cols in pattern:
            for c in cols:
                if 0 <= c < 10: pattern_flat[row_idx * 10 + c] = 1
        
        # חישוב דמיון
        for i in range(150):
            if actual[i] == pattern_flat[i]:
                score += 1
            elif pattern_flat[i] == 1 and actual[i] == 0:
                score -= 0.5 # קנס על פיקסל חסר

        if score > max_score:
            max_score = score
            best_digit = digit

    return best_digit if max_score > 110 else "?" # דורש לפחות 75% התאמה

def parse_time_box(image, config_key):
    """סורק תיבת זמן שלמה (4 ספרות)"""
    cfg = TIME_BOXES[config_key]
    res = ""
    for i in range(4):
        curr_x = cfg['x_start'] + (i * cfg['spacing'])
        res += get_digit_at(image, curr_x, cfg['y'])
        if i == 1: res += ":" # הוספת נקודתיים בפורמט HH:MM
    return res
    
def parse_shabbat_clocks(image):
    """
    סורקת את כל 4 שעוני השבת בדף ומחזירה רשימה מסודרת של הנתונים.
    """
    if not image:
        return []
    
    results = []
    
    for i in range(4):
        # חישוב ה-Y המדויק לכל שעון לפי ה-Step של 145 פיקסלים
        current_offset = i * monitor_config.SHABBAT_STEP_Y
        
        # שימוש בפונקציה שכבר הוספת לסריקת נתוני שעון בודד
        clock_data = scan_shabbat_clock(image, current_offset)
        
        # הוספת אינדקס (1-4) וסטטוס פעולה (נורה ירוקה)
        # נדגום את הסטטוס לפי הקואורדינטות שסיכמנו (STATUS_POINT_X, SHABBAT_TIME_Y_BASE)
        try:
            status_pixel = image.getpixel((monitor_config.STATUS_POINT_X, monitor_config.SHABBAT_TIME_Y_BASE + current_offset))
            is_on = is_pixel_active_green(status_pixel)
        except:
            is_on = False
            
        # בניית האובייקט בפורמט שה-HTML שלך מכיר
        results.append({
            "index": i + 1,
            "on_time": clock_data["start"],     # 'start' מהפונקציה scan_shabbat_clock
            "off_time": clock_data["stop"],      # 'stop' מהפונקציה scan_shabbat_clock
            "is_on": is_on,
            "buildings": clock_data["buildings"],
            "days": clock_data["days"]
        })
        
    return results

def update_shabbat_status():
    """מעדכן סטטוס שעוני שבת - משתמש ב-parse_shabbat_clocks"""
    image_data = fetch_plc_image()
    if not image_data:
        return {}
    
    image = Image.open(io.BytesIO(image_data)).convert('RGB')
    clocks = parse_shabbat_clocks(image)
    
    if clocks:
        return {"clock_1": clocks[0]}
    return {}
    
def check_heater_buildings(img, offset_y):
    active = []
    # נבדוק נקודת אמצע בתוך הטווח שנתת (למשל Y=230 + ה-offset של השעון)
    for name, coords in monitor_config.HEATER_BUILDINGS.items():
        target_y = 230 + offset_y 
        pixel = img.getpixel((coords["x_range"][0], target_y))
        if is_pixel_active_green(pixel):
            active.append(name)
    return active
    
def get_current_n():
    """
    בודק מהו ה-N (מזהה הדף) הנוכחי שמוצג בבקר
    """
    try:
        # שליחת בקשה קלה לבקר לקבלת המצב הנוכחי
        response = session.get(f"http://{config_app.REMOTE_IP}/remote_control_full.html", timeout=3)
        # חיפוש ה-N בתוך ה-HTML של הבקר (בד"כ מופיע ב-Value של ה-Input)
        match = re.search(r'name="n"\s+value="([0-9A-F]+)"', response.text)
        if match:
            return match.group(1)
    except Exception as e:
        logger.error(f"Failed to get current N: {e}")
    return "UNKNOWN"
    
def get_controller_time():
    import datetime as dt
    try:
        # שימוש בפונקציה שבאמת מושכת זמן מהבקר
        plc_time = get_plc_system_time()
        if plc_time:
            return plc_time
        return dt.datetime.now().strftime("%H:%M:%S")
    except Exception as e:
        logger.error(f"Error in get_controller_time: {e}")
        return dt.datetime.now().strftime("%H:%M:%S")
        
        
def scan_shabbat_clock(img, offset_y):
    """סורקת שעון בודד לפי היסט ה-Y שלו"""
    
    # 1. פענוח זמנים (OCR)
    def get_time_string(x_list):
        digits = []
        for x in x_list:
            # גזירת אזור הספרה מהתמונה
            digit_box = img.crop((x, SHABBAT_TIME_Y_BASE + offset_y, 
                                  x + DIGIT_W, SHABBAT_TIME_Y_BASE + offset_y + DIGIT_H))
            digit = recognize_digit(digit_box)
            digits.append(digit if digit else "?")
        
        # בניית פורמט HH:MM (למשל 0800 -> 08:00)
        res = "".join(digits)
        return f"{res[:2]}:{res[2:]}" if len(res) == 4 else "--:--"

    start_time = get_time_string(START_TIME_X)
    stop_time = get_time_string(STOP_TIME_X)

    # 2. בדיקת ימים פעילים
    active_days = []
    for day, x in SHABBAT_DAYS_X.items():
        # בודק פיקסל בודד במיקום היום
        pixel = img.getpixel((x, SHABBAT_TIME_Y_BASE + offset_y + 2)) # +2 לתיקון אנכי קל
        if is_pixel_active_green(pixel):
            active_days.append(day)

    # 3. בדיקת מבנים פעילים
    active_buildings = []
    for bld, x in SHABBAT_BUILDINGS_X.items():
        # נקודת הבדיקה של המבנים היא מעט מעל השעון (Y התחלתי 229 בערך)
        target_y = 229 + offset_y
        pixel = img.getpixel((x, target_y))
        if is_pixel_active_green(pixel):
            active_buildings.append(bld)
            
    # 4. בדיקת חימום מים (אם מדובר בטאב HEATER)
    active_heaters = check_heater_buildings(img, offset_y)
    active_buildings.extend(active_heaters)

    return {
        "start": start_time,
        "stop": stop_time,
        "days": active_days,
        "buildings": list(set(active_buildings)) # הסרת כפילויות
    }
    
    