import os
from PIL import Image, ImageDraw

# המילון המעודכן לאחר התיקון הוויזואלי
MONITOR_POINTS_GIRLS_FIXED = {
    # טור ימני - תוקן ל-666
    'B7_AC1': (666, 144), 'B7_AC2': (666, 168), 'B7_WH': (666, 240),
    'B8_AC':  (666, 281), 'B10_AC1': (666, 418), 
    
    # טורים אמצעיים ושמאליים
    'B12A_AC': (456, 168), 'B12B_AC': (247, 168), 'B12C_AC': (37, 168),
    'B13C_AC': (37, 305), 
    
    # קרוואנים ומועדונים
    'CV24_AC': (37, 442), 'CV26_AC': (37, 558),
    'C13C_AC': (37, 754)
}

def run_final_verify():
    input_file = 'girls_status.jfif'
    output_file = 'debug_girls_final_v2.png'

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    img = Image.open(input_file).convert('RGB')
    draw = ImageDraw.Draw(img)
    
    for name, pos in MONITOR_POINTS_GIRLS_FIXED.items():
        # ציור עיגול טורקיז
        r = 5
        draw.ellipse((pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r), outline=(0, 255, 255), width=2)
        # נקודה מרכזית בלבן
        draw.point(pos, fill=(255, 255, 255))
        
    img.save(output_file)
    print(f"Done! Check {output_file}")

if __name__ == "__main__":
    run_final_verify()