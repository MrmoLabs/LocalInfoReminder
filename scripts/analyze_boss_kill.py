import cv2
import numpy as np
import os
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR

def analyze_color(img):
    """
    Analyze if the image is predominantly Red or Blue.
    Returns: 'Red', 'Blue', or 'Unknown', along with pixel counts.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define Red ranges (Red wraps around 0/180)
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    # Define Blue ranges
    lower_blue = np.array([100, 70, 50])
    upper_blue = np.array([130, 255, 255])
    
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = mask_red1 + mask_red2
    
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    
    red_pixels = cv2.countNonZero(mask_red)
    blue_pixels = cv2.countNonZero(mask_blue)
    
    total_pixels = img.shape[0] * img.shape[1]
    
    if red_pixels > blue_pixels and red_pixels > total_pixels * 0.05: # > 5% pixels
        return "Red (Opponent)", red_pixels, blue_pixels
    elif blue_pixels > red_pixels and blue_pixels > total_pixels * 0.05:
        return "Blue (Friendly)", red_pixels, blue_pixels
    else:
        return "Neutral", red_pixels, blue_pixels

def cv_imread(file_path):
    """Robust image reading for Unicode paths on Windows"""
    cv_img = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), -1)
    return cv_img

def main():
    base_dir = Path(__file__).resolve().parents[1] / "debug_imgs"
    dirs = {
        "Friendly (Blue)": base_dir / "我方大小龙",
        # "Opponent (Red)": base_dir / "敌方大小龙",
    }
    
    engine = RapidOCR()
    
    # Increase column width for filenames
    print(f"{'Type':<15} | {'Filename':<30} | {'Color':<15} | {'Wait'}")
    print("-" * 120)
    
    for label, dir_path in dirs.items():
        if not os.path.exists(dir_path):
            print(f"Directory not found: {dir_path}")
            continue
            
        files = [f for f in os.listdir(dir_path) if f.endswith('.png')]
        # Take first 5 samples
        for f in files[:5]:
            img_path = os.path.join(dir_path, f)
            img = cv_imread(img_path)
            
            if img is None:
                print(f"Failed to read: {f}")
                continue
                
            color_res, r_score, b_score = analyze_color(img)
            
            res, _ = engine(img)
            ocr_text = ""
            if res:
                ocr_text = " ".join([line[1] for line in res])
                
            # Truncate filename for display
            display_name = (f[:15] + '..') if len(f) > 17 else f
            print(f"[{label}] File: {display_name}")
            print(f"  > Color: {color_res} (R:{r_score} vs B:{b_score})")
            print(f"  > Text:  {ocr_text.strip()}")
            print("-" * 40)

if __name__ == "__main__":
    main()
