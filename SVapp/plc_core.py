import sys, os, requests, time, re, logging, io
from PIL import Image
from requests.auth import HTTPBasicAuth
import random

# הוספת נתיב העבודה כדי למנוע שגיאות Import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config_app as config
import monitor_config
import monitor_config as cfg
import monitor_config as m_cfg
from monitor_config import SHABBAT_CLOCKS_BASE_Y, SHABBAT_CLOCK_LAYOUT, DIGIT_MAPS, DIGIT_MAPS, TIME_BOXES, DIGIT_W, DIGIT_H

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

def get_controller_time():
    """משיכת השעה המדויקת שמופיעה על מסך הבקר"""
    if getattr(config, 'SIMULATION_MODE', False):
        return time.strftime("%H:%M:%S")
    try:
        resp = session.get(f"http://{config.REMOTE_IP}/remote_control_full.html", timeout=2)
        if resp.status_code == 200:
            match = re.search(r'(\d{2}:\d{2}:\d{2})', resp.text)
            if match:
                return match.group(1)
    except:
        pass
    return None
    
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

def get_plc_screenshot():
    """משיכת תמונת המסך הנוכחית מהבקר לצורך פענוח"""
    try:
        url = f"http://{config.REMOTE_IP}/remote_control_full.html?pic_format=bmp"
        resp = session.get(url, timeout=5)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content))
    except Exception as e:
        logger.error(f"Failed to capture PLC screenshot: {e}")
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



def get_controller_time():
    """שליפת השעה הנוכחית מהבקר בצורה אמינה"""
    if getattr(config, 'SIMULATION_MODE', False):
        return time.strftime("%H:%M:%S")

    try:
        # פנייה לדף הסטטוס שבו השעה מופיעה בטקסט
        resp = session.get(f"http://{config.REMOTE_IP}/remote_control_full.html", timeout=2)
        if resp.status_code == 200:
            match = re.search(r'(\d{2}:\d{2}:\d{2})', resp.text)
            if match:
                return match.group(1)
    except Exception as e:
        logger.debug(f"Could not fetch time from PLC: {e}")
    
    return None


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
    """
    מביא סטטוס נורות. 
    במצב סימולציה (בבית): מחזיר נתונים אקראיים לעיצוב.
    במצב אמת (במשרד): ניגש לבקר.
    """
    area_upper = area.upper()
    area_lower = area.lower()

    # --- שלב א: בדיקה האם אנחנו בבית (Simulation Mode) ---
    if getattr(config, 'SIMULATION_MODE', False):
        # אנחנו בבית! נחפש את רשימת הנקודות רק כדי לדעת אילו שמות של נורות להמציא
        p_root = getattr(monitor_config, f"MONITOR_POINTS_STATUS_{area_upper}", 
                 getattr(monitor_config, f"MONITOR_POINTS_{area_upper}", {}))
        
        # חילוץ המילון (טיפול במבנה מקונן)
        points_dict = p_root.get(area_lower, p_root) if isinstance(p_root, dict) else {}

        if points_dict:
            # מייצרים סטטוס אקראי לכל נורה קיימת בקונפיג
            return {name: random.choice(["ON", "OFF"]) for name in points_dict.keys()}
        else:
            # אם אפילו בקונפיג אין נקודות, נחזיר כמה נורות גנריות כדי שלא תראה דף ריק בעיצוב
            return {"demo_light_1": "ON", "demo_light_2": "OFF", "demo_light_3": "ON"}

    # --- שלב ב: מצב אמת (רק אם SIMULATION_MODE = False) ---
    
    # חיפוש הגדרות
    possible_attr_names = [f"MONITOR_POINTS_STATUS_{area_upper}", f"MONITOR_POINTS_{area_upper}"]
    p_root = {}
    for attr in possible_attr_names:
        p_root = getattr(monitor_config, attr, {})
        if p_root: break

    p = p_root.get(area_lower, p_root) if isinstance(p_root, dict) else {}
    n = config.CONTEXT_N.get(f"STATUS_{area_upper}")

    if not n or not p:
        return {}

    try:
        # פונקציית הסריקה האמיתית שמדברת עם הבקר
        return get_multi_status(p, n)
    except Exception as e:
        logger.error(f"Real-time scan failed: {e}")
        return {}

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
    """
    בדיקת חיבור דיפרנציאלית (הצלבת נתונים):
    מחובר: X=270 (16-27) לבן  ו- X=284 (20-27) אפור.
    מנותק: X=270 (16-19) אפור ו- X=284 (20-27) לבן.
    """
    if getattr(config, 'SIMULATION_MODE', False):
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
    """מפענח פעולה לקואורדינטות - סדר עדיפויות מתוקן"""
    if not action: return None

    # א. כפתורי מערכת קבועים (צריך להיות ראשון כדי שלא יידרס ע"י BACK)
    special = {
        "WAKE_UP": {"x": 509, "y": 391, "n": config.CONTEXT_N.get("WAKE_UP")},
        "USER_BUTTON": {"x": 218, "y": 20, "n": config.CONTEXT_N.get("MAIN")},
        "DOWN_ARROW": {"x": 520, "y": 140, "n": config.CONTEXT_N.get("LOGIN")},
        "KEY_ENT": {"x": 480, "y": 398, "n": config.CONTEXT_N.get("LOGIN")}
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
                "x": config.KBD_START_X + ((pos - 1) * config.KBD_STEP),
                "y": config.KBD_Y,
                "n": config.CONTEXT_N.get("LOGIN")
            }

    # ג. ניווט טאבים (CONTEXT/TAB)
    if "/" in action:
        try:
            context_name, sub_action = action.split("/", 1)
            target_n = config.CONTEXT_N.get(context_name)
            tab_coords = getattr(config, 'TAB_COORDS', {})
            commands = getattr(config, 'COMMANDS', {})
            coords = tab_coords.get(sub_action) or commands.get(sub_action)
            if coords and target_n:
                return {"x": coords["x"], "y": coords["y"], "n": target_n}
        except: pass

    # ד. בדיקה במילונים סטטיים (BUTTONS / COMMANDS)
    buttons = getattr(config, 'BUTTONS', {})
    commands = getattr(config, 'COMMANDS', {})
    static_btn = buttons.get(action) or commands.get(action)
    if static_btn:
        res = static_btn.copy()
        if 'n' not in res:
            res['n'] = config.CONTEXT_N.get(action, config.CONTEXT_N.get("MAIN"))
        return res

    # ה. פקודת חזרה (רק אם שום דבר אחר לא התאים)
    if action.startswith("BACK_"):
        clean_action = action.replace("BACK_", "")
        back_config = getattr(config, 'BACK_CONFIG', {})
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
        n_val = config.CONTEXT_N.get(context_name)
    if not n_val:
        n_val = get_screen_n_by_pixel_check() or config.CONTEXT_N.get("MAIN")

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
    if config.SIMULATION_MODE:
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
    target_n = config.CONTEXT_N.get(context_name)
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

def parse_shabbat_clocks(image):
    """
    מנתחת תמונה ומחזירה רשימת אובייקטים של שעוני שבת כולל סטטוס פעיל/כבוי.
    """
    if not image: return []

    # המרה לשחור-לבן עבור פענוח ספרות וסימוני V
    bw_img = image.convert('L').point(lambda x: 0 if x < 128 else 255, '1')
    
    results = []
    for clock_cfg in monitor_config.SHABBAT_CLOCK_LAYOUT:
        y = clock_cfg['y']
        
        # --- זיהוי סטטוס ON/OFF (לפי צבע בנקודה ספציפית) ---
        # נדגום את הנקודה שבה אמורה להיות נורית הסטטוס (נניח X=290)
        r, g, b = image.getpixel((290, y + 5))
        is_on = (g > 150 and r < 120)  # אם הירוק דומיננטי -> פעיל
        
        results.append({
            "is_on": is_on,
            "on_time":    parse_time_at(bw_img, clock_cfg['on_x'], y),
            "off_time":   parse_time_at(bw_img, clock_cfg['off_x'], y),
            "days":        parse_days_at(bw_img, clock_cfg['days_x'], y),
            "buildings":  parse_buildings_at(bw_img, y)
        })
    return results

def get_digit_at(image, x, y):
    """מזהה ספרה בודדת במיקום ספציפי"""
    best_digit = "?"
    max_score = -1
    
    # חותכים את הריבוע של הספרה (10x15)
    digit_img = image.crop((x, y, x + DIGIT_W, y + DIGIT_H)).convert('L')
    
    for char, bitmap in DIGIT_MAPS.items():
        score = 0
        # הפיכת הביטמאפ לסט לבדיקה מהירה
        black_pixels = set()
        for row, cols in bitmap:
            for col in cols:
                black_pixels.add((col, row))
        
        # השוואה מול התמונה (פיקסל שחור < 128)
        for py in range(DIGIT_H):
            for px in range(DIGIT_W):
                is_black_in_img = digit_img.getpixel((px, py)) < 128
                is_black_in_map = (px, py) in black_pixels
                
                if is_black_in_img == is_black_in_map:
                    score += 1
        
        if score > max_score:
            max_score = score
            best_digit = char
            
    return best_digit

def parse_time_box(image, config_key):
    """סורק תיבת זמן שלמה (4 ספרות)"""
    cfg = TIME_BOXES[config_key]
    res = ""
    for i in range(4):
        curr_x = cfg['x_start'] + (i * cfg['spacing'])
        res += get_digit_at(image, curr_x, cfg['y'])
        if i == 1: res += ":" # הוספת נקודתיים בפורמט HH:MM
    return res
    
def update_shabbat_status():
    image = fetch_plc_image()
    
    shabbat_data = {
        "clock_1": {
            "on_time": parse_time_box(image, "START_TIME"),
            "off_time": parse_time_box(image, "STOP_TIME"),
            "status": "ON" if check_is_green(image, 58, 254) else "OFF"
        }
    }
    return shabbat_data
    

def get_digit_from_image(image, x, y):
    """מזהה ספרה בודדת במיקום X,Y לפי מפת הפיקסלים מה-PDF"""
    best_match = "?"
    max_score = -1
    
    # חיתוך ועיבוד ראשוני של הריבוע (10x15)
    # נהפוך לאפור (L) כדי להקל על הבדיקה
    digit_segment = image.crop((x, y, x + 10, y + 15)).convert('L')
    
    for digit, bitmap in m_cfg.DIGIT_MAPS.items():
        score = 0
        # הפיכת הביטמאפ לסט קואורדינטות של 'שחור'
        target_pixels = set()
        for row, cols in bitmap:
            for col in cols:
                target_pixels.add((col, row))
        
        # השוואה פיקסל-פיקסל
        for py in range(15):
            for px in range(10):
                is_dark = digit_segment.getpixel((px, py)) < 128
                is_should_be_dark = (px, py) in target_pixels
                
                if is_dark == is_should_be_dark:
                    score += 1
        
        if score > max_score:
            max_score = score
            best_match = digit
            
    return best_match

def parse_shabbat_clocks(image):
    """
    הפונקציה המרכזית שנסרקת על ידי השרת.
    מחזירה רשימה של 4 שעונים בפורמט JSON.
    """
    if not image:
        return []

    clocks_results = []

    for i in range(4):
        current_y = m_cfg.SHABBAT_BASE_Y + (i * m_cfg.SHABBAT_STEP_Y)
        
        # 1. קריאת שעת הפעלה
        on_time = ""
        for x in m_cfg.START_TIME_X_OFFSETS:
            on_time += get_digit_from_image(image, x, current_y)
        on_time = f"{on_time[:2]}:{on_time[2:]}" # הוספת נקודתיים

        # 2. קריאת שעת הפסקה
        off_time = ""
        for x in m_cfg.STOP_TIME_X_OFFSETS:
            off_time += get_digit_from_image(image, x, current_y)
        off_time = f"{off_time[:2]}:{off_time[2:]}"

        # 3. בדיקת סטטוס כפתור (ON/OFF)
        # נדגום את הנקודה (58, Y) ונבדוק אם היא ירוקה
        pixel_color = image.getpixel((m_cfg.STATUS_POINT_X, current_y))
        is_active = (pixel_color[1] > 200 and pixel_color[0] < 50) # בדיקה שהירוק דומיננטי

        # 4. בניית האובייקט (תואם ל-Javascript ב-HTML שלך)
        clocks_results.append({
            "index": i + 1,
            "on_time": on_time,
            "off_time": off_time,
            "is_active": is_active,
            "buildings": [], # ניתן להוסיף כאן את parse_buildings_at אם תרצה
            "days": []       # ניתן להוסיף כאן את parse_days_at
        })

    return clocks_results
    
def is_green(pixel):
    """בודק אם פיקסל בטווח הירוק המוגדר"""
    r, g, b = pixel
    return r == 0 and 250 <= g <= 255 and b == 0

def parse_shabbat_clocks(image):
    if not image: return []
    
    results = []
    # סריקת 4 רצועות שעון
    for i in range(4):
        offset = i * cfg.SHABBAT_STEP_Y
        
        # --- 1. זיהוי שעות (OCR) ---
        # שעת הפעלה (Y קבוע 276 + אופסט)
        on_time = "".join([get_digit_from_image(image, x, 276 + offset) for x in cfg.START_TIME_X])
        # שעת הפסקה (Y קבוע 276 + אופסט)
        off_time = "".join([get_digit_from_image(image, x, 276 + offset) for x in cfg.STOP_TIME_X])

        # --- 2. זיהוי מבנים (Y התחלתי 229) ---
        active_buildings = []
        y_buildings = 229 + offset
        for b_name, x in cfg.SHABBAT_BUILDINGS_X.items():
            if is_green(image.getpixel((x, y_buildings))):
                active_buildings.append(b_name)

        # --- 3. זיהוי ימים (Y התחלתי 278) ---
        active_days = []
        y_days = 278 + offset
        for day_name, x in cfg.SHABBAT_DAYS_X.items():
            if is_green(image.getpixel((x, y_days))):
                active_days.append(day_name)

        # --- 4. מצב כפתור הפעלה כללי ---
        # לפי הקוד הקודם שלך, נדגום את הנקודה (58, 276 + offset)
        is_active = is_green(image.getpixel((58, 276 + offset)))

        results.append({
            "index": i + 1,
            "on_time": f"{on_time[:2]}:{on_time[2:]}",
            "off_time": f"{off_time[:2]}:{off_time[2:]}",
            "is_active": is_active,
            "buildings": active_buildings,
            "days": active_days
        })
        
    return results
    
# plc_core.py
import monitor_config as cfg
from monitor_config import DIGIT_MAPS # מפת הספרות מה-PDF

def is_pixel_active_green(pixel):
    """בודק האם הפיקסל בטווח הירוק המדויק (0, 250-255, 0)"""
    r, g, b = pixel
    return r == 0 and 250 <= g <= 255 and b == 0

def get_digit_at(image, x, y):
    """מזהה ספרה בודדת בשיטת Template Matching"""
    best_digit = "?"
    max_score = -1
    
    # חיתוך ריבוע הספרה
    digit_img = image.crop((x, y, x + 10, y + 15)).convert('L')
    
    for digit, bitmap in DIGIT_MAPS.items():
        score = 0
        expected_pixels = set()
        for row, cols in bitmap:
            for col in cols: expected_pixels.add((col, row))
            
        for py in range(15):
            for px in range(10):
                is_dark = digit_img.getpixel((px, py)) < 128
                if is_dark == ((px, py) in expected_pixels):
                    score += 1
        
        if score > max_score:
            max_score = score
            best_digit = digit
    return best_digit

def parse_shabbat_clocks(image):
    """סורק את כל 4 שעוני השבת בדף"""
    if not image: return []
    
    results = []
    for i in range(4):
        offset = i * cfg.SHABBAT_STEP_Y
        
        # 1. פענוח שעת הפעלה
        on_time_raw = "".join([get_digit_at(image, x, cfg.SHABBAT_TIME_Y_BASE + offset) for x in cfg.START_TIME_X])
        on_time = f"{on_time_raw[:2]}:{on_time_raw[2:]}"
        
        # 2. פענוח שעת הפסקה
        off_time_raw = "".join([get_digit_at(image, x, cfg.SHABBAT_TIME_Y_BASE + offset) for x in cfg.STOP_TIME_X])
        off_time = f"{off_time_raw[:2]}:{off_time_raw[2:]}"

        # 3. בדיקת מבנים (Y=229 + offset)
        active_buildings = []
        y_b = 229 + offset
        for name, x in cfg.SHABBAT_BUILDINGS_X.items():
            if is_pixel_active_green(image.getpixel((x, y_b))):
                active_buildings.append(name)

        # 4. בדיקת ימים (Y=278 + offset)
        active_days = []
        y_d = 278 + offset
        for day, x in cfg.SHABBAT_DAYS_X.items():
            if is_pixel_active_green(image.getpixel((x, y_d))):
                active_days.append(day)

        # 5. סטטוס כפתור הפעלה (נקודה 58, 276)
        is_active = is_pixel_active_green(image.getpixel((58, cfg.SHABBAT_TIME_Y_BASE + offset)))

        results.append({
            "index": i + 1,
            "on_time": on_time,
            "off_time": off_time,
            "is_active": is_active,
            "buildings": active_buildings,
            "days": active_days
        })
    return results