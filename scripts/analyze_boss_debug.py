import cv2
import numpy as np
import os
import sys

# Add src to path just in case
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    print("RapidOCR not found. Please ensure it is installed.")
    sys.exit(1)

ocr = RapidOCR()

def cv2_imread_utf8(file_path):
    # Read file as binary to handle unicode paths on Windows
    with open(file_path, 'rb') as f:
        data = f.read()
    data_np = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(data_np, cv2.IMREAD_COLOR)
    return img

def log(msg):
    with open("analysis_result_target_event.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def analyze_color(img_bgr):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    avg_color = np.mean(img_rgb, axis=(0, 1))
    r, g, b = avg_color
    
    # Target event text logic (assumed yellow/gold text)
    # Yellow = High R + High G, Low B
    # Sample logic: r>100, g>100, b < r*0.8
    is_yellow = r > 100 and g > 100 and (r + g) > (b * 1.5)
    
    return r, g, b, is_yellow, False, img_rgb

def process_boss_images():
    folder_path = "debug_imgs"
    log(f"\n--- Analyzing Target Event Images in {folder_path} ---")
    
    if not os.path.exists(folder_path):
        log("Debug folder not found.")
        return

    files = [f for f in os.listdir(folder_path) if f.startswith("boss_region_debug") and f.endswith(('.png', '.jpg'))]
    if not files:
        log("No target event debug images found.")
        return

    pass_count = 0
    total = 0

    for f in files:
        path = os.path.join(folder_path, f)
        img = cv2_imread_utf8(path)
        if img is None:
            log(f"Failed to read {f}")
            continue

        total += 1
        r, g, b, is_yellow, _, img_rgb = analyze_color(img)
        
        # OCR
        result, _ = ocr(img_rgb)
        text = ""
        box_text = []
        if result:
            text = " ".join([line[1] for line in result])
            box_text = [line[1] for line in result]
        
        status = "FAIL"
        fail_reason = []
        
        # KEYWORD MATCHING
        # Example OCR matches from the monitored target event area
        keywords = ["目标A", "目标B", "即将", "完成"]
        match_found = any(k in text for k in keywords)

        if not match_found: fail_reason.append("OCR(Text)")
        # if not is_yellow: fail_reason.append("Color(Yellow)") 
        
        if not fail_reason: 
            status = "PASS"
            pass_count += 1
            
        reason_str = ", ".join(fail_reason) if fail_reason else "OK"
        log(f"[{status}] {f}: R={r:.1f} G={g:.1f} B={b:.1f} | IsYellow={is_yellow} | OCR='{text}' | Reason: {reason_str}")
    
    log(f"--- Summary: {pass_count}/{total} Passed ---")

if __name__ == "__main__":
    if os.path.exists("analysis_result_target_event.txt"):
        os.remove("analysis_result_target_event.txt")
        
    process_boss_images()
