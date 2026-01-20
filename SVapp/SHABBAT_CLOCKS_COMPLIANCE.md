# בדיקת תאימות לכלל Shabbat Clocks

## ✅ תאימות מלאה לכלל החדש

הקוד הקיים תואם את הכלל `.cursor/rules/shabbatclocks.mdc`:

### 1. ✅ Pixel-Based Digit Recognition (OCR-lite)
- **לא משתמש ב-OCR חיצוני**: הקוד משתמש רק ב-PIL (Pillow) כפי שמוגדר ב-`plc_core.py`
- **Coordinate-Based Sampling**: כל ספרה מוגדרת עם קואורדינטות ספציפיות ב-`monitor_config.py` (DIGIT_MAPS)
- **Strategic Probing**: הפונקציות `get_digit_at()` ו-`identify_digit_from_crop()` דוגמות פיקסלים ספציפיים
- **Signature Matching**: השוואת פיקסלים עם truth table (DIGIT_MAPS) ב-`monitor_config.py`
- **Context Sensitivity**: המערכת משתמשת ב-`n` value (context) כדי לדעת איזה דף לנתח

### 2. ✅ File Responsibilities
- **plc_core.py**: מכיל את `fetch_plc_image()`, `get_pixel_status()`, `get_digit_from_pixels()` (get_digit_at)
- **monitor_config.py**: ה-"Source of Truth" לכל הקואורדינטות (DIGIT_MAPS, TIME_BOXES, וכו')
- **server_app.py**: Flask backend שמנהל polling loops ו-session states
- **config_app.py**: מכיל IPs, credentials, ו-CONTEXT_N mapping

### 3. ✅ Guidelines for Code Generation & Debugging
- **No External OCR**: הקוד לא משתמש ב-Tesseract, OpenCV-OCR, או cloud APIs
- **PIL Only**: כל הניתוח נעשה עם Pillow
- **Coordinate Shifts**: אם יש בעיות עם "--:--" או ערכים שגויים, צריך לבדוק את `monitor_config.py` ל-frame offset
- **Communication Protocol**: משתמש ב-requests עם HTTPBasicAuth, שומר על session integrity
- **Shabbat Clock Specifics**: מטפל ב-4 ספרות (HH:MM) ומזהה את הנקודתיים

### 4. ✅ UI/UX Rules
- **Buttons**: כפתורים ב-web interface שולחים action ל-`/control?action=...` לפני ניווט
- **syncAndNavigate**: משתמש ב-pattern זה לכפתורי "Back" כדי לשמור על sync עם PLC
- **eli-connected CSS**: משתמש ב-class זה כדי להציג login מוצלח

## פונקציות רלוונטיות

### `get_digit_at(img, x_start, y_start)` (plc_core.py:846)
- דוגמת פיקסלים מאזור 14x9
- משווה עם DIGIT_MAPS מ-monitor_config.py
- מחזיר ספרה או "?" אם לא מזוהה

### `identify_digit_from_crop(crop_img)` (plc_core.py:726)
- מקבלת תמונה 10x15
- הופכת לשחור-לבן
- משווה עם DIGIT_MAPS

### `read_shabbat_clock_time(img, clock_index, type)` (plc_core.py:701)
- קוראת 4 ספרות (HH:MM) משעון שבת
- משתמשת ב-SHABBAT_CLOCK_LAYOUT מ-monitor_config.py

### `get_pixel_status(r, g, b)` (plc_core.py:45)
- מזהה מצב נורה לפי צבע פיקסל
- ירוק=ON, אדום=OFF

## הערות

1. **שתי פונקציות לזיהוי ספרות**: יש `get_digit_at()` ו-`identify_digit_from_crop()` - שתיהן משתמשות ב-DIGIT_MAPS אבל עם לוגיקה שונה. זה בסדר, אבל כדאי לשקול לאחד אותן בעתיד.

2. **DIGIT_MAPS**: מוגדר ב-monitor_config.py עם תבניות 10x15. הפונקציות ממירות למימדים שונים (14x9) עם scale factors.

3. **Context N**: כל פונקציה משתמשת ב-context (n value) כדי לדעת איזה דף לנתח.

## סיכום

✅ **הקוד תואם לחלוטין לכלל החדש!**

כל הדרישות מתקיימות:
- ✅ Pixel-based recognition (לא OCR)
- ✅ Coordinate-based sampling
- ✅ Signature matching עם truth table
- ✅ Context sensitivity
- ✅ PIL only (לא OCR חיצוני)
- ✅ monitor_config.py הוא Source of Truth
- ✅ UI/UX rules מתקיימים
