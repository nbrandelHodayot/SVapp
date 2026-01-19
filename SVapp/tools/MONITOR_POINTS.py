import os
from PIL import Image, ImageDraw

# המילון המלא והמעודכן שבנינו
MONITOR_POINTS = {
    # שורה 1
    'SB_B4_AC': (37, 173), 'SB_B4_R': (37, 199), 'SB_B4_T': (37, 225),
    'SB_B3_AC': (249, 173), 'SB_B3_R': (249, 199), 'SB_B3_T': (249, 225),
    'SB_B2_AC': (461, 173), 'SB_B2_R': (461, 199), 'SB_B2_T': (461, 225),
    'SB_B1_AC': (681, 173), 'SB_B1_R': (681, 199), 'SB_B1_T': (681, 226),
    # שורה 2
    'SB_B11B_WH': (37, 431), 'SB_B11A_WH': (249, 430), 
    'SB_B5_AC': (681, 326), 'SB_B5_R': (681, 352), 'SB_B5_T': (681, 379),
    # מועדונים
    'SB_C1_AC': (37, 514), 'SB_C1_L': (249, 513), 'SB_C1_S': (501, 512),
    'SB_C11_AC': (37, 689), 'SB_C11_L': (249, 688), 'SB_C11_S': (501, 687)
}

def run_verification():
    input_file = 'last_hmi_capture.png'
    output_file = 'debug_map.png'

    # בדיקה אם התמונה קיימת בתיקייה
    if not os.path.exists(input_file):
        print(f"שגיאה: הקובץ {input_file} לא נמצא בתיקייה הזו!")
        print(f"התיקייה הנוכחית היא: {os.getcwd()}")
        return

    try:
        # טעינת התמונה
        img = Image.open(input_file).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        print(f"{'נקודה':<15} | {'צבע RGB':<15}")
        print("-" * 35)

        for name, pos in MONITOR_POINTS.items():
            rgb = img.getpixel(pos)
            print(f"{name:<15} | {str(rgb):<15}")

            # ציור סימון בולט (עיגול טורקיז)
            r = 5
            draw.ellipse((pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r), outline=(0, 255, 255), width=2)
        
        # שמירת התמונה החדשה
        img.save(output_file)
        print("-" * 35)
        print(f"הצלחה! נוצר קובץ חדש בשם: {output_file}")
        print(f"הכתובת המלאה: {os.path.abspath(output_file)}")

    except Exception as e:
        print(f"קרתה שגיאה בזמן ההרצה: {e}")

# הפעלת הפונקציה (השורה הזו קריטית!)
if __name__ == "__main__":
    run_verification()