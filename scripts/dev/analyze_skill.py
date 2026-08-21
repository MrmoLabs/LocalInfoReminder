# Skill Detection Analysis Script

import cv2
import numpy as np
import os
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR


ROOT = Path(__file__).resolve().parents[2]

def analyze_images(folder):
    ocr = RapidOCR()
    
    print(f"Analyzing images in {folder}...")
    
    # Red Filter (Same as BossDetector/SkillDetector)
    # HSV Range used in detecting red text
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    for filename in os.listdir(folder):
        if not filename.endswith(".png"): continue
        
        path = os.path.join(folder, filename)
        img = cv2.imread(path)
        if img is None: continue
        
        # 2. Color Analysis (Red Text)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
        red_ratio = cv2.countNonZero(mask_red) / (img.shape[0] * img.shape[1])
        
        # 1. OCR Raw
        # RapidOCR expects RGB usually, but handles BGR if passed as path? 
        # Detectors pass RGB.
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result, _ = ocr(img_rgb)
        
        raw_text = ""
        if result:
             # Result format: [[box, text, score], ...]
             raw_text = " ".join([line[1] for line in result])
             
        # 3. Check Average Color (SkillDetector Logic)
        avg_color = np.mean(img_rgb, axis=(0, 1))
        r, g, b = avg_color
        is_red_avg = r > 85 and r > g + 10 and r > b + 10
        
        print(f"File: {filename}")
        print(f"  Dims: {img.shape}")
        print(f"  Red Ratio: {red_ratio:.4f}")
        print(f"  Avg Color: R={r:.1f} G={g:.1f} B={b:.1f} -> IsRed: {is_red_avg}")
        print(f"  OCR: {raw_text}")
        print("-" * 30)

if __name__ == "__main__":
    analyze_images(os.fspath(ROOT / "debug_imgs"))
