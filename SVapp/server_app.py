#server_app.py
import plc_core
import os
import logging
import threading
import time
import datetime
from datetime import timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS

# ייבוא הגדרות ולוגיקה מקבצים חיצוניים
import config_app as config
from auth_logic import verify_app_user
from plc_core import send_physical_click, fetch_plc_status

# =========================================================================
# 1. הגדרות שרת וסשן
# =========================================================================
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
CORS(app)

# הגדרת לוגים
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================================================================
# 2. דקורטור לאבטחה
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
# 3. נתיבי ניווט ותצוגה (Templates)
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
        
        # אימות המשתמש מול האפליקציה (auth_logic)
        if verify_app_user(username, password):
            session['user'] = username
            session.permanent = True
            
            # --- הפעלת לוגין פיזי אוטומטי לבקר ---
            # נבצע לוגין פיזי רק אם אנחנו לא במצב סימולציה
            if not getattr(config, 'SIMULATION_MODE', False):
                try:
                    from plc_core import perform_physical_login
                    logger.info(f"User {username} logged in. Triggering PLC physical login sequence...")
                    perform_physical_login()
                except Exception as e:
                    logger.error(f"Physical login failed: {e}")
                    # במצב אמת אולי תרצה לעצור כאן, אבל כרגע אנחנו רק מתעדים שגיאה
            else:
                logger.info(f"SIMULATION MODE: User {username} logged in. Skipping physical PLC login sequence.")
            # ------------------------------------

            return redirect(url_for('index'))
            
        return render_template('login.html', error="פרטי התחברות שגויים")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# דפי סטטוס
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

@app.route('/<page_name>.html')
@login_required
def serve_html_pages(page_name):
    # רשימת התיקיות שבהן יש לחפש קבצי HTML לפי ה-tree.txt שלך
    folders = ['', 'status', 'control']
    
    for folder in folders:
        # בניה של הנתיב היחסי (למשל: status/status_boys.html)
        template_path = os.path.join(folder, f"{page_name}.html").replace('\\', '/')
        if os.path.exists(os.path.join(app.template_folder, template_path)):
            return render_template(template_path)
    
    return f"Page {page_name}.html not found", 404

# =========================================================================
# 4. ליבת השליטה (Control Hub)
# =========================================================================

@app.route('/control')
@login_required
def control():
    raw_action = request.args.get('action')
    if not raw_action:
        return jsonify({"status": "error", "message": "No action provided"}), 400

    # 1. מנגנון Auto-Login (אם אלי לא מחובר, נסה להתחבר לפני הפקודה)
    if not plc_core.is_eli_physically_connected():
        # חריג: אם הפקודה היא LOGIN בעצמה, אל תריץ לוגין כפול
        if raw_action != 'LOGIN':
            logger.warning("PLC Eli Session lost. Running auto-login...")
            plc_core.perform_physical_login()
            time.sleep(1.2)

    # 2. טיפול בפקודת LOGIN ישירה (מהכפתור ב-Header)
    if raw_action == 'LOGIN':
        plc_core.perform_physical_login()
        return jsonify({"status": "success", "message": "Login sequence executed"})

    # 3. שליפת נתוני לחיצה (קואורדינטות ו-N)
    res = {"status": "error"}
    code = 400
    cmd = None

    try:
        # לוגיקת BACK_
        if raw_action.startswith("BACK_"):
            ctx = raw_action.replace("BACK_", "")
            cmd = config.BACK_CONFIG.get(ctx)
        
        # לוגיקת הקשר (Context /)
        elif '/' in raw_action:
            ctx_name, act_name = raw_action.split('/')
            n_val = config.CONTEXT_N.get(ctx_name)
            coords = config.TAB_COORDS.get(act_name) or config.COMMON_COORDS.get(act_name)
            if n_val and coords:
                cmd = {**coords, "n": n_val}
        
        # פקודה רגילה מ-COMMANDS
        elif raw_action in config.COMMANDS:
            cmd = config.COMMANDS[raw_action]

        # 4. ביצוע הלחיצה אם נמצאו קואורדינטות
        if cmd and 'x' in cmd and 'y' in cmd:
            res, code = plc_core.send_physical_click(cmd["x"], cmd["y"], cmd.get("n", "00010000000000000000"), raw_action)
        else:
            logger.error(f"Action '{raw_action}' found but missing x/y coordinates in config")
            res = {"status": "error", "message": f"Invalid config for {raw_action}"}

    except Exception as e:
        logger.error(f"Error in control route for action {raw_action}: {e}")
        res = {"status": "error", "message": str(e)}
        code = 500

    return jsonify(res), code

# =========================================================================
# 5. ממשקי API לנתונים (AJAX)
# =========================================================================

@app.route('/api/plc_time')
def get_plc_time():
    status = plc_core.fetch_plc_status("STATUS") # או דף אחר שבו מופיע הזמן
    return jsonify({"time": status.get("PLC_TIME", "00:00:00")})
    
@app.route('/api/status/<area>')
@app.route('/api/status/<area>/<page_type>')
@login_required
def get_area_status(area, page_type="status"):
    """
    API שמחזיר JSON עם מצב הנורות.
    תומך בפורמט: /api/status/boys (סטטוס רגיל)
    או: /api/status/boys/control_split (דף פיצול)
    """
    # קריאה לפונקציה שעדכנו ב-plc_core
    data = fetch_plc_status(area, page_type)
    return jsonify(data)

# =       משיכת תאריך ושעה מהבקר ללא תלות במכשיר ממנו מתחברים לאפליקציה
@app.route('/api/plc_time')
def api_get_plc_time():
    # קריאה לפונקציית הגירוד החדשה
    t = plc_core.get_plc_system_time()
    if t:
        return jsonify({"time": t})
    return jsonify({"time": "00:00:00"}), 404

# =       בדיקה: האם המשתמש מחובר כרגע? אם לא השרת יבצע חיבור אוטומטי      
# משתנה גלובלי למניעת כפילות לוגין
login_lock = threading.Lock()
is_login_running = False

@app.route('/api/check_eli')
def check_eli():
    global is_login_running
    
    # 1. אם אנחנו בסימולציה - החזר אישור מיידי בלי לבצע פעולות ברקע
    if getattr(config, 'SIMULATION_MODE', False):
        return jsonify({
            "connected": True,
            "status": "success",
            "server_time": datetime.datetime.now().strftime("%H:%M:%S"),
            "server_date": datetime.datetime.now().strftime("%d/%m/%Y"),
            "mode": "simulation"
        })

    # 2. בדיקה אמיתית מול הבקר (במצב אמת)
    is_connected = plc_core.is_eli_physically_connected()
    
    # אם אלי לא מחובר ואין כרגע תהליך לוגין שרץ - נתניע לוגין אוטומטי
    if not is_connected and not is_login_running:
        def run_login():
            global is_login_running
            # וודא ש-login_lock מוגדר גלובלית ב-server_app.py
            with login_lock:
                is_login_running = True
                try:
                    logger.info("Automatic login sequence started...")
                    plc_core.smart_login_sequence()
                except Exception as e:
                    logger.error(f"Background login error: {e}")
                finally:
                    is_login_running = False

        threading.Thread(target=run_login, daemon=True).start()
    
    status = "success" if is_connected else ("retrying" if is_login_running else "failed")
    
    return jsonify({
        "connected": is_connected,
        "status": status,
        "server_time": datetime.datetime.now().strftime("%H:%M:%S"),
        "server_date": datetime.datetime.now().strftime("%d/%m/%Y")
    })

@app.route('/api/status/public')
@login_required
def get_public_status_api():
    try:
        from monitor_config import MONITOR_POINTS_STATUS_PUBLIC
        points = MONITOR_POINTS_STATUS_PUBLIC.get("public", {})
        n_val = config.CONTEXT_N.get("STATUS_PUBLIC")
        
        # קריאה לפונקציה ב-plc_core
        data = plc_core.get_multi_status(points, n_val)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    
@app.route('/api/status/public/control_d1')
@login_required # אם הגדרת דקורטור כזה, אם לא - הסר
def api_get_d1_status():
    from plc_core import get_multi_status, check_d1_button_status
    import monitor_config
    
    # 1. קריאת סטטוס נורות הביקורת מהבקר
    results = get_multi_status(monitor_config.MONITOR_POINTS_D1_STATUS)
    
    # 2. בדיקת מצב כפתורי הטוגל (שבת ומועדונים)
    results['SHABBAT_STATUS'] = check_d1_button_status("SHABBAT_STATUS")
    results['CLUBS_STATUS'] = check_d1_button_status("CLUBS_STATUS")
    
    return jsonify(results)
# ======================================================================================================
# חזרה אוטומטית במקרה של חוסר פעילות וסנכרון עם מסך בקר
# ======================================================================================================

@app.route('/api/trigger_auto_back')
@login_required
def trigger_auto_back():
    try:
        # 1. נסיון לקבל רמז מהדפדפן (מהיר)
        page_hint = request.args.get('page_hint')
        
        # 2. בדיקה פיזית בבקר (אמין)
        actual_n = plc_core.get_screen_n_by_pixel_check()
        
        if not actual_n:
            return jsonify({"status": "error", "message": "PLC not responding"}), 500

        from plc_core import N_TO_PAGE_NAME
        # סדר עדיפויות: מה שהבקר אומר, ואם לא מזוהה - מה שהדפדפן אמר
        page_key = N_TO_PAGE_NAME.get(actual_n) or page_hint

        if page_key == "MAIN":
            return jsonify({"status": "success", "page": "MAIN"})

        if not page_key:
            return jsonify({"status": "unknown_n", "n": actual_n}), 200

        # שליחת הלחיצה
        back_cmd = config.BACK_CONFIG.get(page_key)
        if back_cmd:
            # שימוש ב-actual_n כדי שהלחיצה תשלח עם ה-N הנכון שהבקר נמצא בו כרגע
            plc_core.send_physical_click(back_cmd['x'], back_cmd['y'], actual_n, f"BACK_FROM_{page_key}")
            return jsonify({"status": "success", "page": page_key})
        
        return jsonify({"status": "no_back_defined", "page": page_key}), 404
    except Exception as e:
        logger.error(f"Auto-back error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
        
# =========================================================================
# נעילת ניווט במקרה שהמשתמש לא מחבור לבקר
# =========================================================================

# רשימת דפים שדורשים חיבור של Eli (נתיבים מוגנים)
PROTECTED_ROUTES = [
    'nav_control', 
    'settings'
]

@app.before_request
def block_navigation_if_not_connected():
    # רשימת דפים שדורשים חיבור פיזי
    PROTECTED_ROUTES = ['nav_control', 'settings', 'boys_status', 'girls_status', 'public_status']
    
    # אם אנחנו במצב סימולציה, אנחנו לא חוסמים כלום
    if getattr(config, 'SIMULATION_MODE', False):
        return None

    # בודק אם הבקשה היא לאחד הדפים המוגנים
    if request.endpoint in PROTECTED_ROUTES:
        if not plc_core.is_eli_physically_connected():
            flash("הגישה נחסמה: הבקר אינו מזהה חיבור פיזי. (עבור למצב סימולציה ב-Config כדי לעקוף)", "danger")
            return redirect(url_for('index'))



# =========================================================================
# הרצה
# =========================================================================

if __name__ == '__main__':
    # הרצה על כל הממשקים בפורט 5000
    app.run(host='0.0.0.0', port=5000, debug=True)