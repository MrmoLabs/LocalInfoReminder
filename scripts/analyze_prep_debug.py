import os
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

def analyze_prep_images(debug_dir="debug_imgs"):
    if not os.path.exists(debug_dir):
        print(f"Directory {debug_dir} not found.")
        return

    ocr = RapidOCR()
    
    # Get all prep debug images
    files = [f for f in os.listdir(debug_dir) if f.startswith("prep_debug_capture") and f.lower().endswith(".png")]
    files.sort()
    
    print(f"--- Analyzing Prep Images in {debug_dir} ---")
    
    out_file = open("analysis_result_prep.txt", "w", encoding="utf-8")
    
    pass_count = 0
    total_count = len(files)
    
    for filename in files:
        filepath = os.path.join(debug_dir, filename)
        
        # Read image
        img = cv2.imread(filepath)
        if img is None:
            continue
            
        # 1. OCR (Try RGB conversion as learned from boss issue)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result, _ = ocr(img_rgb)
        
        ocr_text = ""
        parsed_seconds = -1
        
        if result:
            ocr_text = " ".join([line[1] for line in result]).strip()
            
            # Logic Analysis
            # Case 1: M:SS (e.g. 4:10)
            if ":" in ocr_text:
                parts = ocr_text.split(":")
                # simple validation
                valid = True
                for p in parts:
                    if not p.strip().isdigit():
                        valid = False
                
                if valid and len(parts) >= 2:
                    mins = int(parts[0])
                    secs = int(parts[1])
                    parsed_seconds = mins * 60 + secs
            
            # Case 2: SS (e.g. 59)
            elif ocr_text.isdigit():
                 val = int(ocr_text)
                 if val < 60:
                     parsed_seconds = val
                     
        status = "FAIL"
        reason = "No Text"
        
        if ocr_text:
            if parsed_seconds != -1:
                status = "PASS"
                reason = f"Parsed: {parsed_seconds}s ({parsed_seconds//60}:{parsed_seconds%60:02d})"
                pass_count += 1
            else:
                reason = "Text found but parse failed"
        
        avg_color = np.mean(img, axis=(0, 1))
        
        log_line = f"[{status}] {filename}: OCR='{ocr_text}' | {reason}"
        print(log_line)
        out_file.write(log_line + "\n")

    summary = f"--- Summary: {pass_count}/{total_count} Passed ---"
    print(summary)
    out_file.write(summary + "\n")
    out_file.close()

if __name__ == "__main__":
    analyze_prep_images()
