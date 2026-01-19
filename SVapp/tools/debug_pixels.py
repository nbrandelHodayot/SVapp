#debug_pixels.py
import io
import requests
from PIL import Image
from requests.auth import HTTPBasicAuth

# יבוא פנימי
import config_app as config
import monitor_config

def debug_public_lamps():
    print("Connecting to PLC and fetching Public Status screen...")
    n_val = config.CONTEXT_N.get("STATUS_PUBLIC")
    url = f"http://{config.REMOTE_IP}/Dashboard.jpg?N={n_val}"
    
    try:
        response = requests.get(url, auth=HTTPBasicAuth(config.CONTROLLER_USERNAME, config.CONTROLLER_PASSWORD), timeout=5)
        if response.status_code != 200:
            print(f"Error: Failed to fetch image. Status: {response.status_code}")
            return

        img = Image.open(io.BytesIO(response.content)).convert('RGB')
        width, height = img.size
        print(f"Image received. Resolution: {width}x{height}")

        points = monitor_config.MONITOR_POINTS_STATUS_PUBLIC.get("public", {})
        
        print(f"{'Point Name':<20} | {'Coords':<10} | {'RGB Value':<15} | {'Detected'}")
        print("-" * 65)

        for name, (x, y) in points.items():
            if x >= width or y >= height:
                print(f"{name:<20} | ({x},{y}) | OUT OF BOUNDS")
                continue
                
            r, g, b = img.getpixel((x, y))
            
            # לוגיקת זיהוי פשוטה
            status = "UNKNOWN"
            if g > 150 and g > r + 30: status = "ON (GREEN)"
            elif r > 150 and r > g + 30: status = "OFF (RED)"
            elif r < 100 and g < 100 and b < 100: status = "BLACK/DARK"
            elif r > 180 and g > 180 and b > 180: status = "WHITE/BRIGHT"
            
            print(f"{name:<20} | ({x},{y}) | ({r:>3},{g:>3},{b:>3}) | {status}")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    debug_public_lamps()