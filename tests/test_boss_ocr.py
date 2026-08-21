import cv2
import numpy as np
import os
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR

def analyze_image(path):
    print(f"\n--- Analyzing {os.path.basename(path)} ---")
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    img = cv2.imread(path)
    if img is None:
        print("Failed to load image")
        return

    # Convert to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Color Analysis
    avg_color = np.mean(img_rgb, axis=(0, 1))
    r, g, b = avg_color
    print(f"Average Color (RGB): ({r:.1f}, {g:.1f}, {b:.1f})")

    is_red = r > 85 and r > g + 10 and r > b + 10
    is_blue = b > 80 and b > r + 3 and b > g + 2
    
    color_result = "UNKNOWN"
    if is_red: color_result = "RED (Enemy)"
    elif is_blue: color_result = "BLUE (Ally)"
    
    print(f"Color Detection: {color_result}")

    # 2. OCR
    ocr = RapidOCR()
    result, _ = ocr(img_rgb)
    
    found_text = []
    if result:
        for line in result:
            print(f"OCR Text: {line[1]} (Confidence: {line[2]:.2f})")
            found_text.append(line[1])
    else:
        print("OCR: No text found")
        
    return color_result, found_text

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[1] / "debug_imgs"
    
    # Pick a sample from Ally
    ally_dir = base_dir / "我方大小龙"
    ally_files = os.listdir(ally_dir)
    if ally_files:
        analyze_image(ally_dir / ally_files[0])
        
    # Pick a sample from Enemy
    enemy_dir = base_dir / "敌方大小龙"
    enemy_files = os.listdir(enemy_dir)
    if enemy_files:
        analyze_image(enemy_dir / enemy_files[0])
