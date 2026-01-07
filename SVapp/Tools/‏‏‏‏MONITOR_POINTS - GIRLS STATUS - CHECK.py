from PIL import Image

def diagnose_girls_image(image_path):
    try:
        img = Image.open(image_path)
        width, height = img.size
        print(f"--- אבחון תמונה ---")
        print(f"רוחב: {width}px, גובה: {height}px")
        
        # דגימה של הנורה הראשונה בבית 7 (בדיקה אם היא ב-Y=173)
        test_y = 173
        rgb = img.getpixel((681, test_y))
        print(f"דגימה ב-(681, {test_y}): {rgb} (אם זה שחור, הנורה נמוכה או גבוהה יותר)")
        
    except Exception as e:
        print(f"שגיאה: {e}")

diagnose_girls_image('girls_status.jfif')