#!/usr/bin/env python3
"""
סקריפט לניתוח נתונים מקובץ PDF של זיהוי ספרות
ממיר קואורדינטות אבסולוטיות לפורמט של DIGIT_MAPS
"""

# מהנתונים בקובץ PDF:
# נראה שיש קואורדינטות (400, 276) עד (408, 290)
# Y מ-276 עד 290 (15 שורות)
# X מ-400 עד 408 (9 פיקסלים?)

# אבל הספרה היא 10 פיקסלים רוחב, אז אולי הספרה מתחילה ב-X=399?

def parse_digit_coords(x_start, y_start, coords_list):
    """
    ממיר קואורדינטות אבסולוטיות לפורמט של DIGIT_MAPS
    
    Args:
        x_start: X של הפינה השמאלית העליונה של הספרה
        y_start: Y של הפינה השמאלית העליונה של הספרה
        coords_list: רשימת קואורדינטות (x, y) של כל הפיקסלים שצהובים (חלק מהספרה)
    
    Returns:
        רשימה בפורמט DIGIT_MAPS: [(row_idx, [cols]), ...]
    """
    # יצירת מילון: row -> set של cols
    digit_map = {}
    
    for x, y in coords_list:
        # המרה ליחסי
        rel_x = x - x_start
        rel_y = y - y_start
        
        # בדיקת גבולות (0-9 ל-X, 0-14 ל-Y)
        if 0 <= rel_x < 10 and 0 <= rel_y < 15:
            if rel_y not in digit_map:
                digit_map[rel_y] = set()
            digit_map[rel_y].add(rel_x)
    
    # המרה לפורמט של DIGIT_MAPS
    result = []
    for row in range(15):
        cols = sorted(digit_map.get(row, []))
        result.append((row, cols))
    
    return result

# דוגמה: אם הקואורדינטות בקובץ הן (400, 276) עד (408, 290)
# ואני מניח שהספרה מתחילה ב-X=399 (כדי לקבל 10 פיקסלים):
if __name__ == "__main__":
    # דוגמה - צריך להחליף בנתונים האמיתיים מהקובץ
    # מהנתונים בקובץ, נראה שיש קואורדינטות מ-(400, 276) עד (408, 290)
    # אבל אני לא יודע איזה פיקסלים הם צהובים (חלק מהספרה)
    
    print("""
    כדי להשתמש בסקריפט הזה:
    1. קרא את הקובץ PDF וזהה את כל הפיקסלים שצהובים (חלק מהספרה)
    2. צור רשימה של קואורדינטות: coords = [(x1, y1), (x2, y2), ...]
    3. קבע את x_start ו-y_start (הפינה השמאלית העליונה של הספרה)
    4. קרא ל-parse_digit_coords(x_start, y_start, coords)
    5. העתק את התוצאה ל-DIGIT_MAPS ב-monitor_config.py
    
    דוגמה:
    coords = [(400, 276), (401, 276), ...]  # כל הפיקסלים הצהובים
    x_start = 399  # או 400 - צריך לבדוק
    y_start = 276
    result = parse_digit_coords(x_start, y_start, coords)
    print(result)
    """)
