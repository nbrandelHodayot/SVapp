import sys, os, requests, time, re, logging, io
from PIL import Image
from requests.auth import HTTPBasicAuth
import random
import datetime
import glob
from pathlib import Path

# הוספת נתיב העבודה כדי למנוע שגיאות Import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config_app
import monitor_config
from monitor_config import (
    SHABBAT_TIME_Y_BASE, SHABBAT_STEP_Y, START_TIME_X, STOP_TIME_X,
    DIGIT_W, DIGIT_H, DIGIT_MAPS, PLC_GREEN, STATUS_POINT_X,
    SHABBAT_BUILDINGS_X, SHABBAT_DAYS_X, SHABBAT_CLOCK_LAYOUT,
    SHABBAT_STATUS_POINTS_BOYS, SHABBAT_DIGIT_Y_BASE, TIME_BOXES
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

def context_to_filename(context_key):
    """ממיר context key לשם קובץ אפשרי בתמונות סימולציה"""
    if not context_key:
        return ["default"]
    
    # מיפוי context keys לשמות קבצים
    context_map = {
        "STATUS_BOYS": ["status_boys", "boys_status"],
        "STATUS_GIRLS": ["status_girls", "girls_status"],
        "STATUS_PUBLIC": ["status_public", "public_status"],
        "STATUS_SHABBAT": ["status_shabbat", "shabbat_status"],
        "BOYS_SHABBAT_AC1": ["02.1.3.1 control_boys_shabbat_ac1", "control_boys_shabbat_ac1", "boys_shabbat_ac1", "shabbat_ac1"],
        "BOYS_SHABBAT_AC2": ["control_boys_shabbat_ac2", "boys_shabbat_ac2", "shabbat_ac2"],
        "BOYS_SHABBAT_ROOM_LIGHTS": ["control_boys_shabbat_room", "boys_shabbat_room", "shabbat_room"],
        "BOYS_SHABBAT_BATHROOM_LIGHTS": ["control_boys_shabbat_bathroom", "boys_shabbat_bathroom", "shabbat_bathroom"],
        "BOYS_SHABBAT_HEATER": ["control_boys_shabbat_heater", "boys_shabbat_heater", "shabbat_heater"],
        "GIRLS_SHABBAT_AC1": ["girls_shabbat_ac1"],
        "GIRLS_SHABBAT_AC2": ["girls_shabbat_ac2"],
        "GIRLS_SHABBAT_ROOM_LIGHTS": ["girls_shabbat_room"],
        "GIRLS_SHABBAT_BATHROOM_LIGHTS": ["girls_shabbat_bathroom"],
        "GIRLS_SHABBAT_HEATER": ["girls_shabbat_heater"],
        # בקרת חלוקה למבנים
        "BOYS_SPLIT": ["control_boys_split", "boys_split", "C_B_S"],
        "GIRLS_SPLIT_1": ["control_girls_split1", "girls_split1", "C_G_S_1"],
        "GIRLS_SPLIT_2": ["control_girls_split2", "girls_split2", "C_G_S_2"],
        "C_B_S": ["control_boys_split", "boys_split"],
        "C_G_S": ["control_girls_split1", "girls_split1"],  # ברירת מחדל ל-split1
        "PUBLIC_SPLIT": ["control_public_split", "public_split", "C_P_S"],
        "C_P_S": ["control_public_split", "public_split"],
        # הפעלה כללית
        "BOYS_GENERAL": ["control_boys_general", "boys_general", "02.2.1 control_boys_general"],
        "GIRLS_GENERAL": ["control_girls_general", "girls_general", "02.2.2 control_girls_general"],
    }
    
    # חיפוש ישיר
    if context_key in context_map:
        return context_map[context_key]
    
    # חיפוש חלקי (למשל "BOYS_SHABBAT" ימצא "BOYS_SHABBAT_AC1")
    for key, names in context_map.items():
        if context_key in key or key in context_key:
            return names
    
    # ברירת מחדל
    return [context_key.lower().replace("_", "-"), "default"]

def find_simulation_images(base_names, sim_dir):
    """מוצא את כל התמונות התואמות לשמות הבסיס"""
    found = []
    extensions = ["*.jfif", "*.jpg", "*.jpeg", "*.bmp", "*.png"]
    
    for base in base_names:
        for ext in extensions:
            # חיפוש עם מספרים (variant_1, variant_2, etc.)
            pattern1 = os.path.join(sim_dir, f"{base}_*.{ext[2:]}")
            pattern2 = os.path.join(sim_dir, f"{base}*.{ext[2:]}")
            pattern3 = os.path.join(sim_dir, f"{base}.{ext[2:]}")
            # חיפוש עם מספרים לפני השם (02.2.1.1 control_girls_split1.jfif)
            pattern4 = os.path.join(sim_dir, f"*{base}_*.{ext[2:]}")
            pattern5 = os.path.join(sim_dir, f"*{base}*.{ext[2:]}")
            pattern6 = os.path.join(sim_dir, f"*{base}.{ext[2:]}")
            # חיפוש עם רווחים (02.2.1.1 control_girls_split1.jfif)
            pattern7 = os.path.join(sim_dir, f"* {base}_*.{ext[2:]}")
            pattern8 = os.path.join(sim_dir, f"* {base}*.{ext[2:]}")
            pattern9 = os.path.join(sim_dir, f"* {base}.{ext[2:]}")
            
            found.extend(glob.glob(pattern1))
            found.extend(glob.glob(pattern2))
            found.extend(glob.glob(pattern3))
            found.extend(glob.glob(pattern4))
            found.extend(glob.glob(pattern5))
            found.extend(glob.glob(pattern6))
            found.extend(glob.glob(pattern7))
            found.extend(glob.glob(pattern8))
            found.extend(glob.glob(pattern9))
    
    return list(set(found))  # הסרת כפילויות

def load_simulation_image(context_key=None, default_name="default", random_variant=True):
    """טוען תמונת סימולציה מהתיקייה המקומית"""
    sim_dir = Path(__file__).parent / "simulation_images"
    
    if not sim_dir.exists():
        logger.warning(f"Simulation directory not found: {sim_dir}")
        return None
    
    # קבלת רשימת שמות אפשריים
    if context_key:
        base_names = context_to_filename(context_key)
        logger.info(f"SIMULATION_MODE: Looking for images with base names: {base_names} (context_key='{context_key}')")
    else:
        base_names = [default_name]
        logger.info(f"SIMULATION_MODE: Looking for images with default name: {default_name}")
    
    # חיפוש תמונות
    images = find_simulation_images(base_names, str(sim_dir))
    
    if not images:
        # נסיון עם default
        if context_key:
            logger.info(f"SIMULATION_MODE: No images found for {base_names}, trying default: {default_name}")
            images = find_simulation_images([default_name], str(sim_dir))
    
    if not images:
        logger.warning(f"SIMULATION_MODE: No simulation images found for context: {context_key} (searched: {base_names})")
        return None
    
    logger.info(f"SIMULATION_MODE: Found {len(images)} image(s): {[os.path.basename(img) for img in images]}")
    
    # סינון תמונות לפי context_key - העדפה לתמונות שמתאימות ל-context
    filtered_images = images
    if context_key:
        # נסה למצוא תמונות שמתאימות ל-context (למשל BOYS_SHABBAT_AC1 צריך תמונות של boys)
        context_lower = context_key.lower()
        matching_images = [img for img in images if context_lower in os.path.basename(img).lower()]
        if matching_images:
            filtered_images = matching_images
            logger.info(f"SIMULATION_MODE: Filtered to {len(filtered_images)} matching images for context {context_key}")
    
    # בחירת תמונה (אקראית או הראשונה)
    selected = random.choice(filtered_images) if random_variant and len(filtered_images) > 1 else filtered_images[0]
    
    try:
        img = Image.open(selected)
        logger.info(f"SIMULATION_MODE: Loaded image '{selected}' for context_key='{context_key}' (found {len(images)} images)")
        return img
    except Exception as e:
        logger.error(f"Failed to load simulation image {selected}: {e}")
        return None

def fetch_plc_image(context_key=None):
    """
    משיכת צילום מסך מהבקר עם חתימת זמן למניעת Cache.
    ב-SIMULATION_MODE: טוען תמונה מהתיקייה המקומית (תמיכה בכמה תמונות אקראיות).
    """
    if getattr(config_app, 'SIMULATION_MODE', False):
        img = load_simulation_image(context_key, default_name="default", random_variant=True)
        if img:
            # המרה ל-bytes כמו שהבקר מחזיר
            buf = io.BytesIO()
            img.save(buf, format='BMP')
            return buf.getvalue()
        else:
            logger.warning("SIMULATION_MODE: No local image found, returning None")
            return None
    
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

def get_plc_screenshot(context_key=None):
    """משיכת תמונת המסך הנוכחית מהבקר לצורך פענוח"""
    if getattr(config_app, 'SIMULATION_MODE', False):
        return load_simulation_image(context_key, default_name="default", random_variant=True)
    
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

def send_physical_click(x, y, n, debug_name="Unknown", silent=False):
    """
    שולחת פקודת לחיצה פיזית לבקר.
    x, y: קואורדינטות הלחיצה.
    n: הקונטקסט (הדף) שבו הלחיצה צריכה להתבצע.
    silent: אם True, לא יוצג בלוגים (מתאים לרצף LOGIN)
    """
    if getattr(config_app, 'SIMULATION_MODE', False):
        if not silent:
            logger.info(f"[SIMULATION] Click at ({x}, {y}) with N={n} [{debug_name}]")
        else:
            logger.debug(f"[SIMULATION] Click at ({x}, {y}) with N={n} [{debug_name}]")
        return {"status": "success"}, 200

    # בניית ה-URL עם הפרמטרים הנכונים עבור הבקר
    url = f"http://{config_app.REMOTE_IP}/cgi-bin/remote_mouse.cgi?pos_x={x},pos_y={y},n={n}"
    
    try:
        # שליחת הבקשה עם ה-Referer שהבקר דורש
        response = session.get(url, headers={"Referer": config_app.REFERER}, timeout=10)
        
        if response.ok:
            if not silent:
                logger.info(f"Click Sent: {debug_name} ({x}, {y}) [N={n}]")
            else:
                logger.debug(f"Click Sent: {debug_name} ({x}, {y}) [N={n}]")
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

def get_multi_status(points_dict, n_val, context_key=None):
    """מעדכן את הבקר לדף מסוים וסורק רשימת נקודות"""
    results = {name: "UNKNOWN" for name in points_dict.keys()}
    
    # מציאת context_key אם לא הועבר
    if not context_key:
        context_key = N_TO_PAGE_NAME.get(n_val)
    
    # מצב סימולציה
    if getattr(config_app, 'SIMULATION_MODE', False):
        logger.info(f"SIMULATION_MODE: Loading image for context_key={context_key}, n_val={n_val}")
        img_data = fetch_plc_image(context_key)
        if not img_data:
            # אם אין תמונה, נחזיר ערכים אקראיים
            logger.warning(f"SIMULATION_MODE: No image found for {context_key}, returning random values")
            return {name: random.choice(["ON", "OFF"]) for name in points_dict.keys()}
        
        # סריקת התמונה
        try:
            img = Image.open(io.BytesIO(img_data)).convert('RGB')
            logger.info(f"SIMULATION_MODE: Image loaded successfully, scanning {len(points_dict)} points")
            for name, (x, y) in points_dict.items():
                try:
                    r, g, b = img.getpixel((x, y))
                    results[name] = get_pixel_status(r, g, b)
                    logger.info(f"  {name} at ({x}, {y}): RGB=({r}, {g}, {b}) -> {results[name]}")
                except Exception as e:
                    logger.warning(f"  Error reading pixel for {name} at ({x}, {y}): {e}")
                    continue
            logger.info(f"SIMULATION_MODE: Status scan complete. Results: {sum(1 for v in results.values() if v == 'ON')} ON, {sum(1 for v in results.values() if v == 'OFF')} OFF, {sum(1 for v in results.values() if v == 'UNKNOWN')} UNKNOWN")
            return results
        except Exception as e:
            logger.error(f"SIMULATION_MODE: Error analyzing image: {e}")
            return {name: random.choice(["ON", "OFF"]) for name in points_dict.keys()}
    
    # מצב אמת - עדכון הבקר לדף הנכון
    try:
        # פקודה שקטה כדי לוודא שהבקר בדף הנכון לפני הצילום
        session.get(f"http://{config_app.REMOTE_IP}/cgi-bin/remote_mouse.cgi?pos_x=1,pos_y=1&n={n_val}", timeout=2)
        time.sleep(0.8)
    except: pass
    
    img_data = fetch_plc_image(context_key)
    if not img_data: 
        return results

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
    וודא שהבקר נמצא בדף הנכון לפני משיכת התמונה.
    """
    import datetime as dt
    area_upper = area.upper()
    img = None
    
    try:
        # 1. וידוא שהבקר נמצא בדף הנכון לפני הצילום
        target_n = config_app.CONTEXT_N.get(context_key)
        if target_n:
            current_n = get_screen_n_by_pixel_check()
            if current_n != target_n:
                logger.info(f"Navigating PLC to {context_key} (N: {target_n})")
                send_physical_click(1, 1, target_n)  # לחיצת ניווט שקטה
                time.sleep(0.7)  # המתנה לטעינת מסך
        
        # 2. משיכת התמונה העדכנית מהבקר
        if getattr(config_app, 'SIMULATION_MODE', False):
            img = load_simulation_image(context_key, default_name="default", random_variant=True)
            if not img:
                logger.warning(f"SIMULATION_MODE: No image found for context {context_key}")
                return {"clocks": [], "time": "--:--", "error": "No simulation image"}
        else:
            # שימוש ב-fetch_plc_image עם context_key כדי לוודא שהתמונה מהדף הנכון
            img_data = fetch_plc_image(context_key=context_key)
            if not img_data:
                logger.error("Failed to fetch image from PLC")
                return {"clocks": [], "time": "--:--", "error": "Connection error"}
            img = Image.open(io.BytesIO(img_data)).convert('RGB')

        if not img:
            return {"clocks": [], "time": "--:--", "error": "No image available"}

        # 3. פענוח נתוני השעונים (זמנים, ימים ומבנים)
        # העברת area ל-parse_shabbat_clocks (לעתיד - אם יהיו קואורדינטות שונות)
        clocks_list = parse_shabbat_clocks(img, area=area_upper)
        
        logger.info(f"Parsed {len(clocks_list)} shabbat clocks for context {context_key}")

        # 4. החזרת הנתונים ל-Frontend
        return {
            "clocks": clocks_list, # הרשימה שסרקנו
            "time": dt.datetime.now().strftime("%H:%M:%S"),
            "area": area_upper
        }

    except Exception as e:
        import traceback
        logger.error(f"Error fetching shabbat data: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
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
            
            if not target_n:
                logger.warning(f"Context '{context_name}' not found in CONTEXT_N")
                return None
            
            # מיפוי שמות להפעלה כללית (BOYS_GENERAL / GIRLS_GENERAL)
            # השמות ב-HTML הם: BATHROOM_ON/OFF, ROOMS_ON/OFF, AC_ON/OFF, HEATER_ON/OFF
            # אבל הפקודות ב-COMMANDS הן: HK_B_* / HK_G_*
            action_mapping = {}
            if context_name == "BOYS_GENERAL":
                action_mapping = {
                    "BATHROOM_ON": "HK_B_WC_ON",
                    "BATHROOM_OFF": "HK_B_WC_OFF",
                    "ROOMS_ON": "HK_B_R_ON",
                    "ROOMS_OFF": "HK_B_R_OFF",
                    "AC_ON": "HK_B_AC_ON",
                    "AC_OFF": "HK_B_AC_OFF",
                    "HEATER_ON": "HK_B_H_ON",
                    "HEATER_OFF": "HK_B_H_OFF"
                }
            elif context_name == "GIRLS_GENERAL":
                action_mapping = {
                    "BATHROOM_ON": "HK_G_WC_ON",
                    "BATHROOM_OFF": "HK_G_WC_OFF",
                    "ROOMS_ON": "HK_G_R_ON",
                    "ROOMS_OFF": "HK_G_R_OFF",
                    "AC_ON": "HK_G_AC_ON",
                    "AC_OFF": "HK_G_AC_OFF",
                    "HEATER_ON": "HK_G_H_ON",
                    "HEATER_OFF": "HK_G_H_OFF"
                }
            
            # אם יש מיפוי, נשתמש בשם הממופה
            mapped_action = action_mapping.get(sub_action, sub_action)
            
            # קודם כל - חיפוש ישיר בפקודות (COMMANDS) - זה הכי מהיר ואמין
            tab_coords = getattr(config_app, 'TAB_COORDS', {})
            commands = getattr(config_app, 'COMMANDS', {})
            coords = tab_coords.get(mapped_action) or commands.get(mapped_action)
            
            if coords:
                res = coords.copy()
                # אם ה-N לא מוגדר בפקודה עצמה, ניקח את ה-N של הקונטקסט
                if 'n' not in res:
                    res['n'] = target_n
                logger.info(f"Found command '{sub_action}' -> '{mapped_action}' in COMMANDS: {res}")
                return res
            
            # אם לא נמצא ב-COMMANDS, ננסה לחשב מהנורות (רק לדפי חלוקה למבנים)
            if context_name in ["C_B_S", "C_G_S", "C_P_S"]:
                # מזהים פעולות כמו AC_B1_ON, AC_B1_OFF או B7_AC_A_ON (בנות)
                if sub_action.endswith("_ON") or sub_action.endswith("_OFF"):
                    device_name = sub_action.replace("_ON", "").replace("_OFF", "")
                    is_on = sub_action.endswith("_ON")
                    
                    # חיפוש הקואורדינטות של הנורה ב-MONITOR_POINTS_CONTROL_SPLIT
                    monitor_dict = None
                    if context_name == "C_B_S":
                        monitor_dict = getattr(monitor_config, 'MONITOR_POINTS_CONTROL_SPLIT', {}).get("boys", {})
                    elif context_name == "C_G_S":
                        # בנות - צריך לבדוק גם girls1 וגם girls2
                        split_dict = getattr(monitor_config, 'MONITOR_POINTS_CONTROL_SPLIT', {})
                        monitor_dict = {**split_dict.get("girls1", {}), **split_dict.get("girls2", {})}
                    elif context_name == "C_P_S":
                        monitor_dict = getattr(monitor_config, 'MONITOR_POINTS_CONTROL_SPLIT', {}).get("public", {})
                    
                    # חיפוש גם בשמות שונים (למשל AC_B1 vs AC_B1)
                    # בנות משתמשות בפורמט B7_AC_A במקום AC_B7
                    if monitor_dict:
                        # נסיון חיפוש ישיר
                        led_coords = monitor_dict.get(device_name)
                        
                        # אם לא נמצא, ננסה להתאים (למשל B7_AC_A -> ACA_B7)
                        if not led_coords and "_" in device_name:
                            parts = device_name.split("_")
                            # אם הפורמט הוא B7_AC_A, נהפוך ל-ACA_B7
                            if len(parts) >= 3 and parts[1].startswith("AC"):
                                if parts[1] == "AC" and len(parts) == 3:
                                    # B7_AC_A -> ACA_B7
                                    alternate_name = f"AC{parts[2]}_{parts[0]}"
                                    led_coords = monitor_dict.get(alternate_name)
                        
                        if led_coords:
                            # קואורדינטות הנורה
                            led_x, led_y = led_coords
                            
                            # בדף חלוקה למבנים, הכפתורים ON/OFF נמצאים משמאל לנורה
                            # ON משמאל, OFF מימין (או להפך - צריך לבדוק)
                            # לפי התבנית: נורה ב-X=839, כפתורים כנראה ב-X ~740-790
                            # נשתמש בהפרש קבוע של ~50 פיקסלים
                            button_x = led_x - (80 if is_on else 40)  # ON יותר שמאלה, OFF פחות שמאלה
                            button_y = led_y  # אותו Y כמו הנורה
                            
                            logger.info(f"Calculated button coordinates for {sub_action}: ({button_x}, {button_y}) from LED at ({led_x}, {led_y})")
                            
                            return {
                                "x": button_x,
                                "y": button_y,
                                "n": target_n
                            }
                        else:
                            logger.warning(f"Device '{device_name}' not found in MONITOR_POINTS_CONTROL_SPLIT for context '{context_name}'")
                    else:
                        logger.warning(f"No monitor dict found for context '{context_name}'")
            
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

    # ו. כפתורי toggle של שעוני שבת - משתמשים באותן קואורדינטות כמו נורות הביקורת
    if action.startswith("TIMER_") and action.endswith("_TOGGLE"):
        timer_num = action.replace("TIMER_", "").replace("_TOGGLE", "")
        timer_key = f"timer_{timer_num}"
        
        # קבלת הקואורדינטות מ-SHABBAT_STATUS_POINTS_BOYS
        if hasattr(monitor_config, 'SHABBAT_STATUS_POINTS_BOYS'):
            status_points = monitor_config.SHABBAT_STATUS_POINTS_BOYS
            if timer_key in status_points:
                x, y = status_points[timer_key]
                # הקונטקסט יהיה לפי ה-context_name שמועבר, או נלקח מהקונטקסט הנוכחי
                # בדרך כלל זה יהיה BOYS_SHABBAT_AC1, BOYS_SHABBAT_AC2, וכו'
                return {
                    "x": x,
                    "y": y,
                    # ה-N יקבע לפי ה-context_name שמועבר לפונקציה
                    "n": None  # יקבע לפי context_name
                }

    return None
    

def send_physical_click_by_action(action_name, context_name=None, silent=False):
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

    if not silent:
        logger.info(f"CLICK: {action_name} at ({x}, {y}) | N: {n_val}")
    else:
        logger.debug(f"CLICK: {action_name} at ({x}, {y}) | N: {n_val}")
    
    return send_physical_click(x, y, n_val, debug_name=action_name, silent=silent)

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
    """מבצע את כל רצף הלחיצות להתחברות (בצורה שקטה - ללא הצגה בלוגים)"""
    logger.debug("Starting automated login sequence (silent mode)...")
    # שימוש בשמות הפעולות כפי שהם מוגדרים ב-get_coords_dynamic
    sequence = ["WAKE_UP", "USER_BUTTON", "DOWN_ARROW", "KEY_6", "KEY_6", "KEY_9", "KEY_1", "KEY_1", "KEY_ENT"]
    
    for action in sequence:
        send_physical_click_by_action(action, silent=True)
        time.sleep(1.2) # השהיה קריטית לתגובת הבקר
    logger.debug("Login sequence completed (silent mode)")

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

    # חישוב base_y לפי ה-index של השעון
    base_y = SHABBAT_TIME_Y_BASE + (clock_index * SHABBAT_STEP_Y)
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
        img_data = fetch_plc_image(context_key=context_name)
        if not img_data:
            return {"success": False, "error": "PLC image fetch failed"}

        img = Image.open(io.BytesIO(img_data)).convert('RGB')
        
        # 3. פענוח
        clocks = parse_shabbat_clocks(img, area='boys')  # ברירת מחדל לבנים
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
    for digit, pattern in monitor_config.DIGIT_MAPS.items():
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
    for name, x in monitor_config.BUILDINGS_MAP_BOYS.items():
        if is_pixel_marked(bw_img, x, y_row + 5):
            active.append(name)
    return active

def is_pixel_active_green(pixel):
    """בודק האם הפיקסל בטווח הירוק - גמיש יותר לזיהוי נורות"""
    r, g, b = pixel
    # ירוק = G גבוה, R ו-B נמוכים
    # טווח גמיש יותר: R < 50, G > 200, B < 50
    return r < 50 and g > 200 and b < 50

def check_shabbat_button_status(img, offset_y):
    """
    בודק מצב כפתור הפעלה/כיבוי של שעון שבת לפי פיקסלים אסטרטגיים.
    
    בדיקה נעשית בפיקסלים: x=90, y מ-264 עד 271 (עם offset לפי השעון)
    
    Args:
        img: PIL Image object
        offset_y: היסט Y לפי השעון (0 לשעון 1, 146 לשעון 2, וכו')
    
    Returns:
        "ON" אם הכפתור במצב פעיל (ירוק), "OFF" אם כבוי (אדום), או "UNKNOWN" אם לא ניתן לזהות
    """
    try:
        check_x = monitor_config.SHABBAT_BUTTON_X_CHECK  # 90
        check_y_start = monitor_config.SHABBAT_BUTTON_Y_CHECK_START + offset_y  # 264 + offset
        check_y_end = monitor_config.SHABBAT_BUTTON_Y_CHECK_END + offset_y  # 271 + offset
        
        # בדיקת גבולות
        if not (0 <= check_x < img.width):
            logger.warning(f"Button check X out of bounds: {check_x} (image width: {img.width})")
            return "UNKNOWN"
        if not (0 <= check_y_start < img.height and 0 <= check_y_end < img.height):
            logger.warning(f"Button check Y out of bounds: {check_y_start}-{check_y_end} (image height: {img.height})")
            return "UNKNOWN"
        
        # וידוא ש-check_y_start <= check_y_end
        if check_y_start > check_y_end:
            logger.warning(f"Invalid Y range: start={check_y_start} > end={check_y_end}")
            return "UNKNOWN"
        
        green_count = 0
        red_count = 0
        total_checked = 0
        
        # סריקה של הפיקסלים מ-y=264 עד y=271
        logger.debug(f"Scanning pixels: x={check_x}, y from {check_y_start} to {check_y_end} (image size: {img.width}x{img.height})")
        y_range = list(range(check_y_start, check_y_end + 1))
        logger.debug(f"Y range list: {y_range} (length: {len(y_range)})")
        
        for y in y_range:
            try:
                # בדיקת גבולות נוספת לפני קריאת הפיקסל
                if not (0 <= check_x < img.width and 0 <= y < img.height):
                    logger.debug(f"Pixel ({check_x}, {y}) out of bounds, skipping")
                    continue
                    
                pixel = img.getpixel((check_x, y))
                r, g, b = pixel
                
                # בדיקת ירוק: RGB(0,250,0) עד RGB(0,255,0)
                if r < 10 and 250 <= g <= 255 and b < 10:
                    green_count += 1
                
                # בדיקת אדום: RGB(250,0,0) עד RGB(255,0,0)
                if 250 <= r <= 255 and g < 10 and b < 10:
                    red_count += 1
                
                total_checked += 1
            except Exception as e:
                logger.warning(f"Error reading pixel at ({check_x}, {y}): {e}")
                continue
        
        logger.info(f"Button status check: x={check_x}, y={check_y_start}-{check_y_end}, green={green_count}, red={red_count}, total={total_checked}")
        
        # קביעת מצב לפי רוב הפיקסלים
        if total_checked == 0:
            logger.warning("No pixels checked for button status")
            return "UNKNOWN"
        
        # אם רוב הפיקסלים ירוקים - ON
        if green_count > red_count and green_count >= total_checked * 0.5:
            return "ON"
        
        # אם רוב הפיקסלים אדומים - OFF
        if red_count > green_count and red_count >= total_checked * 0.5:
            return "OFF"
        
        # אם אין רוב ברור - UNKNOWN
        logger.debug(f"Button status unclear: green={green_count}, red={red_count}, total={total_checked}")
        return "UNKNOWN"
        
    except Exception as e:
        logger.error(f"Error checking shabbat button status: {e}")
        return "UNKNOWN"

def get_shabbat_clock_time(clock_id, time_type="ON", context_name=None, img=None):
    """
    מפענח שעת שעון שבת לפי clock_id.
    
    Args:
        clock_id: מזהה השעון - יכול להיות 1-4, "timer_1" עד "timer_4", או "1" עד "4"
        time_type: "ON" (שעת הפעלה) או "OFF" (שעת הפסקה) - ברירת מחדל: "ON"
        context_name: שם הקונטקסט (למשל "BOYS_SHABBAT_AC1") - נדרש אם img=None
        img: אובייקט תמונה (PIL Image) - אם None, ימשוך מהבקר לפי context_name
    
    Returns:
        מחרוזת של השעה בפורמט "HH:MM" או "--:--" אם לא הצליח
    
    Uses:
        - קואורדינטות מ-monitor_config.py (START_TIME_X, STOP_TIME_X, SHABBAT_DIGIT_Y_BASE, SHABBAT_STEP_Y)
        - פונקציית get_digit_at() לזיהוי ספרות לפי pixel-based recognition
        - DIGIT_MAPS מ-monitor_config.py לזיהוי תבניות הספרות
    """
    # נרמול clock_id לפורמט אחיד
    if isinstance(clock_id, str):
        if clock_id.startswith("timer_"):
            clock_id = int(clock_id.replace("timer_", ""))
        else:
            try:
                clock_id = int(clock_id)
            except ValueError:
                logger.error(f"Invalid clock_id format: {clock_id}")
                return "--:--"
    
    if not (1 <= clock_id <= 4):
        logger.error(f"clock_id must be between 1 and 4, got: {clock_id}")
        return "--:--"
    
    # חישוב offset Y לפי clock_id
    timer_key = f"timer_{clock_id}"
    status_coords = monitor_config.SHABBAT_STATUS_POINTS_BOYS.get(timer_key)
    if not status_coords:
        logger.error(f"Timer {clock_id} coordinates not found in SHABBAT_STATUS_POINTS_BOYS")
        return "--:--"
    
    # בדיקת בטיחות - וודא ש-status_coords הוא tuple/list
    if not isinstance(status_coords, (tuple, list)) or len(status_coords) != 2:
        logger.error(f"Timer {clock_id} invalid coordinates format: {status_coords} (type: {type(status_coords)})")
        return "--:--"
    
    status_x, status_y_base = status_coords
    offset_y = status_y_base - monitor_config.SHABBAT_TIME_Y_BASE
    
    # Y של שורת הספרות לשעון זה
    digit_y = monitor_config.SHABBAT_DIGIT_Y_BASE + offset_y
    
    # בחירת רשימת X לפי סוג הזמן
    if time_type.upper() == "OFF":
        x_list = monitor_config.STOP_TIME_X
    else:
        x_list = monitor_config.START_TIME_X
    
    # משיכת תמונה אם לא סופקה
    if img is None:
        if not context_name:
            logger.error("Either img or context_name must be provided")
            return "--:--"
        
        try:
            # וידוא שהבקר נמצא בדף הנכון
            target_n = config_app.CONTEXT_N.get(context_name)
            if target_n:
                current_n = get_screen_n_by_pixel_check()
                if current_n != target_n:
                    logger.info(f"Navigating PLC to {context_name} (N: {target_n})")
                    send_physical_click(1, 1, target_n)
                    time.sleep(0.7)
            
            # משיכת תמונה מהבקר
            img_data = fetch_plc_image(context_key=context_name)
            if not img_data:
                logger.error("Failed to fetch image from PLC")
                return "--:--"
            
            img = Image.open(io.BytesIO(img_data)).convert('RGB')
        except Exception as e:
            logger.error(f"Error fetching image for shabbat clock: {e}")
            return "--:--"
    
    # דגימת פיקסלים אסטרטגיים לכל ספרה (4 ספרות: HH:MM)
    digits = []
    for x in x_list:
        try:
            # בדיקת גבולות
            if 0 <= x < img.width and 0 <= digit_y < img.height:
                # שימוש ב-get_digit_at() לזיהוי הספרה לפי pixel-based recognition
                digit = get_digit_at(img, x, digit_y)
                digits.append(digit if digit and digit != "?" else "?")
            else:
                logger.warning(f"Digit coordinates out of bounds: ({x}, {digit_y})")
                digits.append("?")
        except Exception as e:
            logger.debug(f"Error reading digit at ({x}, {digit_y}): {e}")
            digits.append("?")
    
    # בניית מחרוזת השעה בפורמט HH:MM
    if len(digits) == 4 and "?" not in digits:
        time_str = f"{digits[0]}{digits[1]}:{digits[2]}{digits[3]}"
        logger.debug(f"Shabbat clock {clock_id} ({time_type}): {time_str}")
        return time_str
    else:
        logger.warning(f"Failed to read all digits for clock {clock_id}: {digits}")
        return "--:--"

def get_digit_at(img, x_start, y_start):
    """
    מזהה ספרה אחת לפי מיקום - דגימת פיקסלים אסטרטגיים בלבד (3-5 פיקסלים לכל ספרה)
    
    Logic for Shabbat Clocks (Digit Recognition):
    - Each digit position (0-9) is treated as a grid
    - Instead of reading the whole image, we sample 3-5 "Strategic Pixels" for each digit box
    - If any sampled pixel fails the threshold (sum < 200), return "?"
    - Uses threshold sum(pixel) > 600 for bright pixels (to account for RGB variations)
    
    Args:
        img: PIL Image object
        x_start: X coordinate of digit top-left corner
        y_start: Y coordinate of digit top-left corner
    
    Returns:
        Digit string ("0"-"9") or "?" if recognition fails
    """
    best_digit = "?"
    max_score = -1
    
    # מימדים: 14x9 (רוחב x גובה)
    digit_w = monitor_config.DIGIT_W  # 14
    digit_h = monitor_config.DIGIT_H   # 9
    
    # דגימת פיקסלים אסטרטגיים בלבד מהתבניות
    # במקום לקרוא את כל התמונה, נדגום רק את הפיקסלים הרלוונטיים מהתבנית
    for digit, pattern in monitor_config.DIGIT_MAPS.items():
        score = 0
        total_checks = 0
        failed_checks = 0
        
        try:
            # דגימת פיקסלים אסטרטגיים מהתבנית
            # התבנית ב-10x15, נמיר ל-14x9
            for row_idx, cols in pattern:
                # התאמת שורה: נדגום את השורות 3-11 מתוך 15 (החלק המרכזי)
                if 3 <= row_idx < 12:  # 9 שורות מרכזיות
                    mapped_row = row_idx - 3  # 0-8
                    for c in cols:
                        # התאמת עמודה: scale factor 1.4
                        scaled_c = int(c * 1.4)
                        if 0 <= scaled_c < digit_w and 0 <= mapped_row < digit_h:
                            x = x_start + scaled_c
                            y = y_start + mapped_row
                            
                            # בדיקת גבולות
                            if 0 <= x < img.width and 0 <= y < img.height:
                                p = img.getpixel((x, y))
                                pixel_sum = sum(p)
                                
                                # Threshold: פיקסל בהיר = sum > 600 (להתחשב בשונות RGB)
                                # פיקסל כהה = sum < 200
                                if pixel_sum < 200:
                                    failed_checks += 1
                                    # אם פיקסל אסטרטגי נכשל, זה סימן רע
                                    score -= 0.5
                                elif pixel_sum > 600:
                                    # פיקסל בהיר במקום הנכון - התאמה טובה
                                    score += 1
                                
                                total_checks += 1
                            else:
                                # מחוץ לגבולות - נחשב ככשל
                                failed_checks += 1
                                score -= 0.3
            
            # חישוב ציון סופי (נרמול לפי מספר הבדיקות)
            if total_checks > 0:
                normalized_score = score / total_checks
                
                # אם יותר מדי פיקסלים אסטרטגיים נכשלו, הספרה לא תקינה
                failure_rate = failed_checks / total_checks if total_checks > 0 else 1.0
                if failure_rate > 0.4:  # יותר מ-40% כשלים
                    normalized_score -= 0.5
                
                if normalized_score > max_score:
                    max_score = normalized_score
                    best_digit = digit
        except Exception as e:
            logger.debug(f"Error sampling strategic pixels for digit {digit} at ({x_start}, {y_start}): {e}")
            continue
    
    # דורש ציון מינימלי של 0.3 (30% התאמה)
    if max_score > 0.3:
        return best_digit
    else:
        # אם כל הפיקסלים האסטרטגיים נכשלו, החזר "?"
        logger.debug(f"Digit recognition failed at ({x_start}, {y_start}): max_score={max_score:.2f}")
        return "?"

def parse_time_box(image, config_key):
    """סורק תיבת זמן שלמה (4 ספרות)"""
    cfg = TIME_BOXES[config_key]
    res = ""
    for i in range(4):
        curr_x = cfg['x_start'] + (i * cfg['spacing'])
        res += get_digit_at(image, curr_x, cfg['y'])
        if i == 1: res += ":" # הוספת נקודתיים בפורמט HH:MM
    return res
    
def parse_shabbat_clocks(image, area='boys'):
    """
    סורקת את כל 4 שעוני השבת בדף ומחזירה רשימה מסודרת של הנתונים.
    משתמשת בקואורדינטות המדויקות מ-SHABBAT_STATUS_POINTS_BOYS (או GIRLS/PUBLIC אם קיימים).
    
    Args:
        image: PIL Image object
        area: 'boys', 'girls', או 'public' - לקביעת הקואורדינטות הנכונות
    """
    if not image:
        return []
    
    results = []
    
    # בחירת קואורדינטות לפי אזור (כרגע כולם משתמשים ב-BOYS)
    status_points = monitor_config.SHABBAT_STATUS_POINTS_BOYS
    if area.lower() == 'girls':
        # אם יש קואורדינטות ספציפיות לבנות, נשתמש בהן
        status_points = getattr(monitor_config, 'SHABBAT_STATUS_POINTS_GIRLS', status_points)
    elif area.lower() == 'public':
        # אם יש קואורדינטות ספציפיות לציבורי, נשתמש בהן
        status_points = getattr(monitor_config, 'SHABBAT_STATUS_POINTS_PUBLIC', status_points)
    
    for i in range(4):
        timer_key = f"timer_{i+1}"
        
        # חישוב ה-Y offset לפי הקואורדינטות המדויקות
        # שעון 1: Y=266, שעון 2: Y=412, שעון 3: Y=556, שעון 4: Y=701
        status_coords = status_points.get(timer_key)
        if not status_coords:
            logger.warning(f"Timer {i+1} coordinates not found in SHABBAT_STATUS_POINTS_BOYS")
            continue
        
        # בדיקת בטיחות - וודא ש-status_coords הוא tuple/list
        if not isinstance(status_coords, (tuple, list)) or len(status_coords) != 2:
            logger.error(f"Timer {i+1} invalid coordinates format: {status_coords} (type: {type(status_coords)})")
            continue
            
        status_x, status_y_base = status_coords
        
        # חישוב offset Y ביחס לשעון הראשון (266)
        try:
            current_offset = status_y_base - monitor_config.SHABBAT_TIME_Y_BASE
            # וידוא ש-current_offset הוא int
            if not isinstance(current_offset, (int, float)):
                logger.error(f"Timer {i+1} invalid offset: {current_offset} (type: {type(current_offset)})")
                continue
        except Exception as e:
            logger.error(f"Timer {i+1} error calculating offset: {e}, status_y_base={status_y_base}, SHABBAT_TIME_Y_BASE={monitor_config.SHABBAT_TIME_Y_BASE}")
            continue
        
        # שימוש בפונקציה לסריקת נתוני שעון בודד
        try:
            clock_data = scan_shabbat_clock(image, current_offset, area=area)
        except Exception as e:
            import traceback
            logger.error(f"Timer {i+1} error in scan_shabbat_clock: {e}")
            logger.error(f"Timer {i+1} traceback: {traceback.format_exc()}")
            continue
        
        # בדיקת סטטוס כפתור - שימוש בפונקציה החדשה לבדיקת פיקסלים אסטרטגיים
        # הפונקציה scan_shabbat_clock כבר בודקת את מצב הכפתור ומחזירה is_on
        is_on = clock_data.get("is_on", False)
        button_status = clock_data.get("button_status", "UNKNOWN")
        
        logger.info(f"Timer {i+1} button status: {button_status}, is_on: {is_on}, offset_y: {current_offset}")
            
        # בניית האובייקט בפורמט שה-HTML מכיר
        results.append({
            "index": i + 1,
            "on_time": clock_data["start"],     # 'start' מהפונקציה scan_shabbat_clock
            "off_time": clock_data["stop"],     # 'stop' מהפונקציה scan_shabbat_clock
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
    clocks = parse_shabbat_clocks(image, area='boys')  # ברירת מחדל לבנים
    
    if clocks:
        return {"clock_1": clocks[0]}
    return {}
    
def check_heater_buildings(img, offset_y):
    active = []
    # נבדוק נקודת אמצע בתוך הטווח שנתת (למשל Y=230 + ה-offset של השעון)
    # וידוא ש-HEATER_BUILDINGS הוא dict
    if not isinstance(monitor_config.HEATER_BUILDINGS, dict):
        logger.error(f"HEATER_BUILDINGS is not a dict: {type(monitor_config.HEATER_BUILDINGS)}")
        return active
    
    for name, coords in monitor_config.HEATER_BUILDINGS.items():
        try:
            # וידוא ש-coords הוא dict עם x_range
            if not isinstance(coords, dict) or "x_range" not in coords:
                logger.error(f"Invalid coords format for {name}: {coords}")
                continue
            target_y = 230 + offset_y 
            pixel = img.getpixel((coords["x_range"][0], target_y))
            if is_pixel_active_green(pixel):
                active.append(name)
        except Exception as e:
            logger.debug(f"Error checking heater building {name}: {e}")
            continue
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
        
        
def scan_shabbat_clock(img, offset_y, area='boys'):
    """
    סורקת שעון בודד לפי היסט ה-Y שלו - משתמשת בקואורדינטות המדויקות.
    
    Args:
        img: PIL Image object
        offset_y: היסט Y לפי השעון (0 לשעון 1, 146 לשעון 2, וכו')
        area: 'boys', 'girls', או 'public' - לקביעת קואורדינטות המבנים הנכונות
    """
    
    # בדיקת טיפוס offset_y
    if not isinstance(offset_y, (int, float)):
        logger.error(f"scan_shabbat_clock: invalid offset_y type: {type(offset_y)}, value: {offset_y}")
        raise TypeError(f"offset_y must be int/float, got {type(offset_y)}")
    
    # Y של שורת הספרות לשעון זה
    digit_y = monitor_config.SHABBAT_DIGIT_Y_BASE + offset_y
    
    # 1. פענוח זמנים (OCR) - 4 ספרות מימין לשמאל
    def get_time_string(x_list):
        digits = []
        for x in x_list:
            # גזירת אזור הספרה מהתמונה - מימדים: 14x9 (רוחב x גובה)
            try:
                # בדיקת גבולות
                if 0 <= x < img.width and 0 <= digit_y < img.height:
                    digit = get_digit_at(img, x, digit_y)
                    digits.append(digit if digit else "?")
                else:
                    digits.append("?")
            except Exception as e:
                logger.debug(f"Error reading digit at ({x}, {digit_y}): {e}")
                digits.append("?")
        
        # בניית פורמט HH:MM (למשל 0800 -> 08:00)
        res = "".join(digits)
        return f"{res[:2]}:{res[2:]}" if len(res) == 4 and "?" not in res else "--:--"

    start_time = get_time_string(monitor_config.START_TIME_X)
    stop_time = get_time_string(monitor_config.STOP_TIME_X)

    # 2. בדיקת ימים פעילים - בדיקה לפי טווחי פיקסלים
    active_days = []
    days_y = monitor_config.SHABBAT_DAYS_Y + offset_y  # Y קבוע: 285 + offset
    
    # שימוש בטווחי X החדשים לבדיקה מדויקת יותר
    days_x_ranges = getattr(monitor_config, 'SHABBAT_DAYS_X_RANGES', {})
    if not days_x_ranges:
        # fallback ל-SHABBAT_DAYS_X הישן (נקודה בודדת)
        logger.warning("SHABBAT_DAYS_X_RANGES not found, using SHABBAT_DAYS_X")
        days_x_ranges = {day: (x, x) for day, x in monitor_config.SHABBAT_DAYS_X.items()}
    
    for day, (x_start, x_end) in days_x_ranges.items():
        try:
            # בדיקת גבולות
            if not (0 <= days_y < img.height):
                logger.debug(f"Day {day} Y out of bounds: {days_y}")
                continue
            
            green_count = 0
            total_checked = 0
            
            # סריקה של כל הפיקסלים בטווח X
            for x in range(x_start, x_end + 1):
                if 0 <= x < img.width:
                    try:
                        pixel = img.getpixel((x, days_y))
                        r, g, b = pixel
                        
                        # בדיקת ירוק: RGB(0,250,0) עד RGB(0,255,0)
                        if r < 10 and 250 <= g <= 255 and b < 10:
                            green_count += 1
                        
                        total_checked += 1
                    except Exception as e:
                        logger.debug(f"Error reading pixel at ({x}, {days_y}) for day {day}: {e}")
                        continue
            
            # אם רוב הפיקסלים ירוקים - היום נבחר
            if total_checked > 0 and green_count >= total_checked * 0.5:
                active_days.append(day)
                logger.debug(f"Day {day} is active: {green_count}/{total_checked} green pixels")
            else:
                logger.debug(f"Day {day} is not active: {green_count}/{total_checked} green pixels")
                
        except Exception as e:
            logger.warning(f"Error checking day {day} at range ({x_start}-{x_end}, {days_y}): {e}")
            continue

    # 3. בדיקת מבנים פעילים - שתי שורות (Y=222 ו-Y=279)
    active_buildings = []
    # בחירת קואורדינטות לפי אזור (בנים/בנות/ציבורי)
    area_lower = area.lower()
    if area_lower == 'girls':
        # קואורדינטות לבנות (אם קיימות)
        buildings_row1 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW1_GIRLS', 
                                getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW1', {}))
        buildings_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW2_GIRLS', 
                                getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW2', {}))
        buildings_y_row1 = getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW1_GIRLS', 
                                   getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW1', 222)) + offset_y
        buildings_y_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW2_GIRLS', 
                                   getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW2', 279)) + offset_y
    elif area_lower == 'public':
        # קואורדינטות לציבורי (אם קיימות)
        buildings_row1 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW1_PUBLIC', 
                                getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW1', {}))
        buildings_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW2_PUBLIC', 
                                getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW2', {}))
        buildings_y_row1 = getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW1_PUBLIC', 
                                   getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW1', 222)) + offset_y
        buildings_y_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW2_PUBLIC', 
                                   getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW2', 279)) + offset_y
    else:
        # ברירת מחדל - בנים
        buildings_row1 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW1', {})
        buildings_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW2', {})
        buildings_y_row1 = getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW1', 222) + offset_y
        buildings_y_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_Y_ROW2', 279) + offset_y
    
    # בדיקת שורה ראשונה
    # וידוא ש-buildings_row1 הוא dict
    if not isinstance(buildings_row1, dict):
        logger.error(f"SHABBAT_BUILDINGS_X_ROW1 is not a dict: {type(buildings_row1)}, value: {buildings_row1}")
    else:
        for bld, x in buildings_row1.items():
            try:
                if 0 <= x < img.width and 0 <= buildings_y_row1 < img.height:
                    pixel = img.getpixel((x, buildings_y_row1))
                    if is_pixel_active_green(pixel):
                        active_buildings.append(bld)
            except Exception as e:
                logger.debug(f"Error checking building {bld} (row1) at ({x}, {buildings_y_row1}): {e}")
    
    # בדיקת שורה שנייה
    buildings_row2 = getattr(monitor_config, 'SHABBAT_BUILDINGS_X_ROW2', {})
    # וידוא ש-buildings_row2 הוא dict
    if not isinstance(buildings_row2, dict):
        logger.error(f"SHABBAT_BUILDINGS_X_ROW2 is not a dict: {type(buildings_row2)}, value: {buildings_row2}")
    else:
        for bld, x in buildings_row2.items():
            try:
                if 0 <= x < img.width and 0 <= buildings_y_row2 < img.height:
                    pixel = img.getpixel((x, buildings_y_row2))
                    if is_pixel_active_green(pixel) and bld not in active_buildings:
                        active_buildings.append(bld)
            except Exception as e:
                logger.debug(f"Error checking building {bld} (row2) at ({x}, {buildings_y_row2}): {e}")
            
    # 4. בדיקת חימום מים (אם מדובר בטאב HEATER)
    active_heaters = check_heater_buildings(img, offset_y)
    active_buildings.extend(active_heaters)
    
    # 5. בדיקת מצב כפתור הפעלה/כיבוי לפי פיקסלים אסטרטגיים
    button_status = check_shabbat_button_status(img, offset_y)
    is_on = (button_status == "ON")

    return {
        "start": start_time,
        "stop": stop_time,
        "days": active_days,
        "buildings": list(set(active_buildings)), # הסרת כפילויות
        "is_on": is_on,
        "button_status": button_status
    }
    
    