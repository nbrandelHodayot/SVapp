# server_app.py
import plc_core
import os
import logging
import threading
import time
import datetime

from datetime import timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler

import io
from PIL import Image

# ייבוא הגדרות ולוגיקה מקבצים חיצוניים
import config_app as config
from auth_logic import verify_app_user

from plc_core import (send_physical_click, fetch_plc_status, 
                      send_physical_click_by_action, N_TO_PAGE_NAME, 
                      parse_shabbat_clocks)

# =========================================================================
# 1. הגדרות שרת, סשן ולוגים
# =========================================================================
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
CORS(app)

# =========================================================================
# Context Processor - העברת משתנים גלובליים לכל ה-templates
# =========================================================================
@app.context_processor
def inject_simulation_mode():
    """מעביר את מצב הסימולציה לכל ה-templates"""
    return {
        'SIMULATION_MODE': getattr(config, 'SIMULATION_MODE', False)
    }

# הגדרת לוגים מפורטת
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# הגדרת SocketIO עם תמיכה ב-CORS ו-eventlet
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# משתנים גלובליים לניהול מצב לוגין
login_lock = threading.Lock()
is_login_running = False

def check_plc_status():
    """פונקציית סנכרון: בודקת איפה הבקר נמצא ומעדכנת את הדפדפן"""
    try:
        n_value = plc_core.get_screen_n_by_pixel_check() 
        if n_value:
            page_name = N_TO_PAGE_NAME.get(n_value)
            if page_name:
                logger.info(f"Sync: PLC is on page {n_value} ({page_name}). Sending force_navigate.")
                socketio.emit('force_navigate', {'target_page': page_name})
    except Exception as e:
        logger.error(f"Sync task error: {e}")

# =========================================================================
# 2. דקורטור אבטחה
# =========================================================================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# =========================================================================
# 3. נתיבי תצוגה (Templates) - הפירוט המלא כפי שהיה לך
# =========================================================================

@app.route('/')
def index():
    is_connected = plc_core.is_eli_physically_connected()
    return render_template('index.html', eli_connected=is_connected)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_app_user(username, password):
            session['user'] = username
            session.permanent = True
            
            if not getattr(config, 'SIMULATION_MODE', False):
                try:
                    logger.info(f"User {username} logged in. Triggering Smart Login...")
                    # הרצה ב-Thread כדי לא לחסום את תגובת ה-HTTP
                    threading.Thread(target=plc_core.smart_login_sequence, daemon=True).start()
                except Exception as e:
                    logger.error(f"Login trigger failed: {e}")
            return redirect(url_for('index'))
            
        return render_template('login.html', error="פרטי התחברות שגויים")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/status/<area>')
def status_page(area):
    # קריאה לפונקציה שעדכנו קודם (שמחזירה רנדומלי בבית)
    data = plc_core.fetch_plc_status(area)
    
    # שליחת הנתונים ל-HTML תחת השם status_data
    return render_template('status_base.html', area=area, status_data=data)

@app.route('/status_boys.html')
@login_required
def status_boys():
    return render_template('status/status_boys.html')

@app.route('/status_girls.html')
@login_required
def status_girls():
    return render_template('status/status_girls.html')

@app.route('/status_public.html')
@login_required
def status_public():
    return render_template('status/status_public.html')

@app.route('/status_shabbat.html')
@login_required
def status_shabbat():
    return render_template('status/status_shabbat.html')

@app.route('/api/status/shabbat')
@login_required
def get_shabbat_status():
    context = request.args.get('context', 'BOYS_SHABBAT_AC1')
    area = 'boys' if 'BOYS' in context.upper() else 'girls'
    
    # שימוש בפונקציה הייעודית החדשה
    data = plc_core.fetch_shabbat_data(area, context)
    
    if "error" in data:
        return jsonify({"error": data["error"]}), 500

    try:
        # החזרת הנתונים ישירות (הפונקציה כבר מחזירה clocks עם is_on, times, buildings, days)
        return jsonify({
            "clocks": data.get("clocks", []),
            "time": data.get("time", "--:--"),
            "area": data.get("area", area.upper()),
            "success": True  # הוספה לתאימות עם JavaScript
        })
    except Exception as e:
        logger.error(f"Failed to parse shabbat clocks: {e}")
        return jsonify({"error": str(e), "success": False}), 500
        
        
        
# =========================================================================
# 4. ליבת השליטה (Control Hub) - לוגיקה מלאה
# =========================================================================

@app.route('/control')
@login_required
def control():
    raw_action = request.args.get('action')
    context_param = request.args.get('context', 'INDEX')

    if not raw_action:
        return jsonify({"status": "error", "message": "No action provided"}), 400

    # 1. בדיקת חיבור פיזית (הפונקציה החדשה עם הפס הלבן/אפור)
    # אנחנו לא מבצעים לוגין אוטומטי אם הפעולה היא עצמה LOGIN
    if raw_action != 'LOGIN' and not plc_core.is_eli_physically_connected():
        logger.warning(f"Eli session lost (Gray pixels detected). Running auto-login...")
        threading.Thread(target=plc_core.smart_login_sequence, daemon=True).start()
        time.sleep(0.8) # המתנה קלה לסינכרון

    # 2. פקודת LOGIN ידנית
    if raw_action == 'LOGIN':
        threading.Thread(target=plc_core.smart_login_sequence, daemon=True).start()
        return jsonify({"status": "success", "message": "Login sequence initiated"})

    # 3. ביצוע הפקודה
    try:
        # שליחה ל-plc_core עם ה-context הנוכחי
        res, code = plc_core.send_physical_click_by_action(raw_action, context_param)
        return jsonify(res), code

    except Exception as e:
        logger.error(f"Control error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# =========================================================================
# 5. ממשקי API לנתונים (AJAX) - כולל D1 ו-Auto Back
# =========================================================================

#משיכת תאריך/שעה מהבקר
@app.route('/system_time')
def api_get_plc_time():
    """משיכת זמן מהבקר עבור השעון העליון"""
    try:
        t = plc_core.get_controller_time()
        now = datetime.datetime.now()
        return jsonify({
            "server_time": t if t else now.strftime("%H:%M:%S"),
            "server_date": now.strftime("%d/%m/%Y"),
            "time": t if t else now.strftime("%H:%M:%S")
        })
    except Exception as e:
        return jsonify({"time": "--:--:--", "server_time": "--:--:--"})

@app.route('/api/check_eli')
def check_eli():
    """בדיקת סטטוס חיבור וסנכרון זמן"""
    global is_login_running
    try:
        is_connected = plc_core.is_eli_physically_connected()
        t = plc_core.get_controller_time()
        status = "success" if is_connected else ("retrying" if is_login_running else "failed")
        
        return jsonify({
            "connected": is_connected,
            "status": status,
            "server_time": t if t else datetime.datetime.now().strftime("%H:%M:%S"),
            "server_date": datetime.datetime.now().strftime("%d/%m/%Y")
        })
    except Exception as e:
        logger.error(f"Error in check_eli: {e}")
        return jsonify({"connected": False, "status": "error"})

@app.route('/api/shabbat_status')
def api_shabbat_status():
    """משיכת נתוני שעוני שבת (זמנים, ימים ומבנים)"""
    context = request.args.get('context')
    try:
        if getattr(config, 'SIMULATION_MODE', False):
            # נתוני דמה למצב סימולציה
            return jsonify([
                {"on_time": "16:30", "off_time": "22:00", "days": ["ו", "ש"], "buildings": ["1", "2"]},
                {"on_time": "05:00", "off_time": "08:00", "days": ["א", "ג"], "buildings": ["3"]},
                {"on_time": "18:00", "off_time": "23:00", "days": ["ה"], "buildings": ["9א"]},
                {"on_time": "00:00", "off_time": "00:00", "days": [], "buildings": []}
            ])

        # 1. השגת צילום מסך
        image = plc_core.get_plc_screenshot(context_key=context)
        if not image:
            return jsonify({"error": "Could not capture PLC screen"}), 500
            
        # 2. פענוח השעונים מהתמונה (הפונקציה שקיימת ב-plc_core.py)
        clocks_data = plc_core.parse_shabbat_clocks(image)
        
        return jsonify(clocks_data)
    except Exception as e:
        logger.error(f"Error in api_shabbat_status: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/status/<area>')
@login_required
def get_area_status(area):
    data = fetch_plc_status(area)
    return jsonify(data)

@app.route('/api/status/boys/control_split')
@login_required
def get_boys_control_split_status():
    """מחזיר סטטוס נורות ביקורת לדף בקרת בנים - חלוקה למבנים"""
    import monitor_config
    from plc_core import get_multi_status
    
    # שימוש ב-MONITOR_POINTS_CONTROL_SPLIT עם המפתח "boys"
    points_dict = monitor_config.MONITOR_POINTS_CONTROL_SPLIT.get("boys", {})
    n_val = config.CONTEXT_N.get("BOYS_SPLIT")
    context_key = "BOYS_SPLIT"
    
    if not n_val or not points_dict:
        return jsonify({"error": "Configuration missing"}), 500
    
    try:
        results = get_multi_status(points_dict, n_val, context_key)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching boys control split status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/boys/general')
@login_required
def get_boys_control_general_status():
    """מחזיר סטטוס נורות ביקורת לדף בקרת בנים - הפעלה כללית"""
    import monitor_config
    from plc_core import get_multi_status
    
    # שימוש ב-MONITOR_POINTS_CONTROL_GEN עם המפתח "boys"
    points_dict = monitor_config.MONITOR_POINTS_CONTROL_GEN.get("boys", {})
    n_val = config.CONTEXT_N.get("BOYS_GENERAL")
    context_key = "BOYS_GENERAL"
    
    if not n_val or not points_dict:
        return jsonify({"error": "Configuration missing"}), 500
    
    try:
        results = get_multi_status(points_dict, n_val, context_key)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching boys control general status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/girls/control_split1')
@login_required
def get_girls_control_split1_status():
    """מחזיר סטטוס נורות ביקורת לדף בקרת בנות - חלוקה למבנים חלק 1 (בתים 7-10, C20-C26)"""
    import monitor_config
    from plc_core import get_multi_status
    
    # שימוש ב-MONITOR_POINTS_CONTROL_SPLIT עם המפתח "girls1"
    points_dict = monitor_config.MONITOR_POINTS_CONTROL_SPLIT.get("girls1", {})
    n_val = config.CONTEXT_N.get("GIRLS_SPLIT_1")
    context_key = "GIRLS_SPLIT_1"
    
    if not n_val or not points_dict:
        return jsonify({"error": "Configuration missing"}), 500
    
    try:
        results = get_multi_status(points_dict, n_val, context_key)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching girls control split1 status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/girls/control_split2')
@login_required
def get_girls_control_split2_status():
    """מחזיר סטטוס נורות ביקורת לדף בקרת בנות - חלוקה למבנים חלק 2 (בתים 12-13)"""
    import monitor_config
    from plc_core import get_multi_status
    
    # שימוש ב-MONITOR_POINTS_CONTROL_SPLIT עם המפתח "girls2"
    points_dict = monitor_config.MONITOR_POINTS_CONTROL_SPLIT.get("girls2", {})
    n_val = config.CONTEXT_N.get("GIRLS_SPLIT_2")
    context_key = "GIRLS_SPLIT_2"
    
    if not n_val or not points_dict:
        return jsonify({"error": "Configuration missing"}), 500
    
    try:
        results = get_multi_status(points_dict, n_val, context_key)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching girls control split2 status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/girls/general')
@login_required
def get_girls_control_general_status():
    """מחזיר סטטוס נורות ביקורת לדף בקרת בנות - הפעלה כללית"""
    import monitor_config
    from plc_core import get_multi_status
    
    # שימוש ב-MONITOR_POINTS_CONTROL_GEN עם המפתח "girls"
    points_dict = monitor_config.MONITOR_POINTS_CONTROL_GEN.get("girls", {})
    n_val = config.CONTEXT_N.get("GIRLS_GENERAL")
    context_key = "GIRLS_GENERAL"
    
    if not n_val or not points_dict:
        return jsonify({"error": "Configuration missing"}), 500
    
    try:
        results = get_multi_status(points_dict, n_val, context_key)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error fetching girls control general status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/public/control_d1')
@login_required
def api_get_d1_status():
    from plc_core import get_multi_status
    import monitor_config
    # משיכת נורות הסטטוס של מסך D1
    results = get_multi_status(monitor_config.MONITOR_POINTS_D1_STATUS, config.CONTEXT_N.get("D1_MAIN"))
    return jsonify(results)

@app.route('/api/trigger_auto_back')
@login_required
def trigger_auto_back():
    try:
        page_hint = request.args.get('page_hint')
        actual_n = plc_core.get_screen_n_by_pixel_check()
        
        if not actual_n:
            return jsonify({"status": "error", "message": "PLC not responding"}), 500

        page_key = N_TO_PAGE_NAME.get(actual_n) or page_hint
        if page_key == "MAIN":
            return jsonify({"status": "success", "page": "login"})

        back_cmd = config.BACK_CONFIG.get(page_key)
        if back_cmd:
            plc_core.send_physical_click(back_cmd['x'], back_cmd['y'], actual_n, f"BACK_FROM_{page_key}")
            return jsonify({"status": "success", "page": page_key})
        
        return jsonify({"status": "no_back_defined", "page": page_key}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# =========================================================================
# 6. הגנה, ניווט וחוסר פעילות
# =========================================================================

@app.before_request
def handle_session_and_protection():
    # 1. בדיקת חוסר פעילות (Inactivity Timeout)
    if request.endpoint not in ['login', 'static', 'logout_timeout']:
        if 'user' in session:
            last_activity = session.get('last_activity')
            if last_activity:
                last_time = datetime.datetime.fromisoformat(last_activity)
                elapsed = (datetime.datetime.now() - last_time).total_seconds()
                
                if elapsed > config.INACTIVITY_TIMEOUT:
                    logger.info(f"Session timeout for {session['user']}. Redirecting to login.")
                    session.clear()
                    return redirect(url_for('login_page'))
            
            # עדכון זמן פעילות אחרון
            session['last_activity'] = datetime.datetime.now().isoformat()

    # 2. הגנה על נתיבים (רק אם אלי לא מחובר)
    if getattr(config, 'SIMULATION_MODE', False): return None
    PROTECTED_ROUTES = ['nav_control', 'nav_settings']
    
    if request.endpoint == 'serve_html_pages':
        page_name = request.view_args.get('page_name', '')
        if any(protected in page_name for protected in PROTECTED_ROUTES):
            if not plc_core.is_eli_physically_connected():
                logger.warning(f"Unauthorized access to {page_name} (Eli not connected)")
                return redirect(url_for('index')) # או דף אחר לבחירתך
    return None

@app.route('/<path:page_name>')
@login_required
def serve_html_pages(page_name):
    if not page_name.endswith('.html'): page_name += '.html'
    search_locations = [page_name, f"status/{page_name}", f"control/{page_name}"]
    
    for location in search_locations:
        full_path = os.path.join(app.template_folder, location)
        if os.path.exists(full_path):
            return render_template(location)
    return f"הדף {page_name} לא נמצא", 404

@app.route('/api/set_plc_page')
@login_required
def set_plc_page():
    action_key = request.args.get('n') 
    tab_param = request.args.get('current_tab', 'AC1').upper()
    area = request.args.get('area', 'boys').lower()
    
    # מיפוי בין tab_id (מה-HTML) לשם המלא ב-TAB_COORDS
    tab_id_to_name = {
        'AC1': 'AC1',
        'AC2': 'AC2',
        'ROOMS': 'ROOM_LIGHTS',  # ROOMS -> ROOM_LIGHTS
        'WC': 'BATHROOM_LIGHTS',  # WC -> BATHROOM_LIGHTS
        'HEATER': 'HEATER'
    }
    
    # המרת tab_id לשם המלא
    full_tab_name = tab_id_to_name.get(action_key.upper(), action_key.upper())
    
    # בניית שם הטאב המלא (למשל BOYS_SHABBAT_AC1)
    if area == 'boys':
        tab_name = f"BOYS_SHABBAT_{full_tab_name}"
    elif area == 'girls':
        tab_name = f"GIRLS_SHABBAT_{full_tab_name}"
    else:
        tab_name = f"{area.upper()}_SHABBAT_{full_tab_name}"
    
    # קבלת הקואורדינטות של הטאב
    coords = config.TAB_COORDS.get(tab_name)
    
    if not coords:
        logger.error(f"Missing tab coordinates for {tab_name}")
        return jsonify({"success": False, "error": f"Tab {action_key} not found"}), 400
    
    # קבלת ה-N של הדף הנוכחי (למשל BOYS_SHABBAT_AC1)
    # המרת tab_param לשם המלא
    full_current_tab = tab_id_to_name.get(tab_param, tab_param)
    current_context_key = f"{area.upper()}_SHABBAT_{full_current_tab}"
    current_n = config.CONTEXT_N.get(current_context_key)
    
    if not current_n:
        # נסיון עם הקונטקסט הכללי
        current_n = config.CONTEXT_N.get(f"{area.upper()}_SHABBAT_AC1")
    
    if not current_n:
        logger.error(f"Missing context N for {current_context_key}")
        return jsonify({"success": False, "error": "Context mapping missing"}), 400

    # שליחת הלחיצה
    result, code = plc_core.send_physical_click(coords['x'], coords['y'], n=current_n, debug_name=f"TAB_{action_key}")
    
    if code == 200 and result.get("status") == "success":
        return jsonify({"success": True, "target_tab": action_key})
    else:
        return jsonify({"success": False, "error": result.get("message", "Unknown error")}), code
    
# =========================================================================
# 7. מתזמן (Scheduler) - ללא לוגין אוטומטי
# =========================================================================

@app.route('/logout_timeout')
def logout_timeout():
    session.clear()
    flash("נותקת עקב חוסר פעילות", "warning")
    return redirect(url_for('login'))

# יצרנו את ה-Scheduler רק עבור עדכון נוריות סטטוס כלליות
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_plc_status, trigger="interval", seconds=60)
scheduler.start()

# =========================================================================
# הרצת השרת
# =========================================================================
if __name__ == '__main__':
    # שימוש ב-socketio.run חיוני לעבודה תקינה של WebSockets
    # debug mode מופעל רק בסביבת פיתוח (SIMULATION_MODE)
    debug_mode = getattr(config, 'SIMULATION_MODE', False)
    socketio.run(app, host='0.0.0.0', port=5000, debug=debug_mode, use_reloader=False)