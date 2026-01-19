# SVapp - מערכת ניהול ובקרת אזורים

מערכת ניהול ובקרה מבוססת Flask לניהול מערכות הבקר הפיזי.

## תכונות

- ניהול ובקרת מערכות (מיזוג, תאורה, חימום)
- מסכי סטטוס בזמן אמת
- ניהול שעוני שבת
- ממשק משתמש HMI
- תמיכה במצב סימולציה לפיתוח

## דרישות מערכת

- Python 3.8+
- pip
- גישה לרשת המקומית (לחיבור לבקר)

## התקנה

### 1. שכפול הפרויקט

```bash
git clone <repository-url>
cd SVapp
```

### 2. יצירת סביבה וירטואלית

**Linux/Mac:**
```bash
python3 -m venv venv_linux
source venv_linux/bin/activate
```

**Windows:**
```bash
python -m venv venv_win
venv_win\Scripts\activate
```

### 3. התקנת תלויות

```bash
pip install -r tools/requirements.txt
```

### 4. הגדרת משתני סביבה

צור קובץ `secrets/.env` עם התוכן הבא:

```env
# אבטחת הבקר
CONTROLLER_WEB_USERNAME=your_username
CONTROLLER_WEB_PASSWORD=your_password
CONTROLLER_SYSTEM_PASSWORD=your_system_password

# אבטחת האפליקציה
SECRET_KEY=your_secret_key_here
# ליצירת SECRET_KEY: python -c 'import secrets; print(secrets.token_hex(32))'

# משתמשי האפליקציה
APP_USER_ADMIN=your_admin_password
APP_USER_ELI=your_eli_password
```

**חשוב:** אל תשמור את הקובץ `secrets/.env` ב-Git! הקובץ מוחרג אוטומטית.

## הרצה

### Linux/Mac

```bash
source venv_linux/bin/activate
python server_app.py
```

או באמצעות הסקריפט:

```bash
chmod +x run_linux.sh
./run_linux.sh
```

### Windows

```powershell
venv_win\Scripts\activate
python server_app.py
```

או באמצעות הסקריפט:

```powershell
.\run_win.ps1
```

השרת יעלה על: `http://localhost:5000`

## מצב סימולציה

המערכת מזהה אוטומטית אם היא רצה במחשב פיתוח לפי שם המחשב.

להפעלה ידנית של מצב סימולציה, ערוך את `config_app.py`:

```python
SIMULATION_MODE = True  # True לפיתוח, False לייצור
```

## מבנה הפרויקט

```
SVapp/
├── server_app.py          # אפליקציית Flask הראשית
├── plc_core.py            # ליבת תקשורת עם הבקר
├── config_app.py          # הגדרות אפליקציה
├── monitor_config.py      # הגדרות ניטור וקואורדינטות
├── auth_logic.py          # לוגיקת אימות
├── templates/             # תבניות HTML
├── static/                # קבצים סטטיים (CSS, JS)
├── secrets/               # משתני סביבה (לא ב-Git)
├── tools/                 # כלי פיתוח וסקריפטים
└── requirements.txt       # תלויות Python
```

## שימוש

1. פתח דפדפן וגש ל-`http://localhost:5000`
2. התחבר עם אחד מהמשתמשים המוגדרים ב-`secrets/.env`
3. בחר את אזור השליטה/סטטוס הרצוי

## פיתוח

### הרצת בדיקות

```bash
python tools/debug_pixels.py
```

### דיבאג

המערכת משתמשת ב-logging. לוגים מוצגים בקונסול.

במצב פיתוח (`SIMULATION_MODE=True`), המערכת תהיה ב-debug mode עם auto-reload.

## אבטחה

- כל הסיסמאות מוגדרות דרך משתני סביבה בקובץ `secrets/.env`
- הקובץ `secrets/.env` מוחרג מ-Git
- יש להגדיר `SECRET_KEY` חזק לאפליקציית Flask
- timeout אוטומטי לניתוק משתמשים לא פעילים

## בעיות נפוצות

### שגיאת חיבור לבקר

- ודא שהבקר מחובר לרשת והכתובת ב-`config_app.py` נכונה
- בדוק את פרטי ההתחברות ב-`secrets/.env`

### שגיאת ייבוא מודולים

```bash
# ודא שהסביבה הווירטואלית מופעלת
source venv_linux/bin/activate  # Linux/Mac
# או
venv_win\Scripts\activate       # Windows

# התקן מחדש את התלויות
pip install -r tools/requirements.txt
```

## רישיון

[ציין את הרישיון שלך כאן]

## תמיכה

[ציין פרטי קשר או קישור לנושא תמיכה]
