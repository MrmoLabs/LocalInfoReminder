import cv2
import numpy as np
import os
import sys

# Add src to path just in case, though we only use libraries
sys.path.append(os.path.join(os.getcwd(), 'src'))

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    print("RapidOCR not found. Please ensure it is installed.")
    sys.exit(1)

ocr = RapidOCR()

def analyze_color(img_bgr):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    avg_color = np.mean(img_rgb, axis=(0, 1))
    r, g, b = avg_color
    
    # Current Logic from screen_monitor.py
    is_red = r > 85 and r > g + 15 and r > b + 15
    is_blue = b > 80 and b > r + 5 and b > g + 2
    
    return r, g, b, is_red, is_blue, img_rgb

def cv2_imread_utf8(file_path):
    # Read file as binary to handle unicode paths on Windows
    with open(file_path, 'rb') as f:
        data = f.read()
    data_np = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(data_np, cv2.IMREAD_COLOR)
    return img

def log(msg):
    with open("analysis_result.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def process_folder(folder_path, expected_type):
    log(f"\n--- Analyzing {folder_path} (Expected: {expected_type}) ---")
    if not os.path.exists(folder_path):
        log(f"Folder not found: {folder_path}")
        return

    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        log("No images found.")
        return

    for f in files:
        path = os.path.join(folder_path, f)
        img = cv2_imread_utf8(path)
        if img is None:
            log(f"Failed to read {f}")
            continue

        r, g, b, is_red, is_blue, img_rgb = analyze_color(img)
        
        # OCR
        result, _ = ocr(img_rgb)
        text = ""
        if result:
            text = " ".join([line[1] for line in result])
        
        status = "FAIL"
        fail_reason = []
        
        # KEYWORD MATCHING UPDATE
        match_found = any(k in text for k in ["釜底抽薪", "底抽薪", "减疗", "降疗"])

        if expected_type == "RED":
            if not is_red: fail_reason.append("Color(Red)")
            if not match_found: fail_reason.append("OCR(Text)")
            if not fail_reason: status = "PASS"
            
        elif expected_type == "BLUE":
            if not is_blue: fail_reason.append("Color(Blue)")
            if not match_found: fail_reason.append("OCR(Text)")
            if not fail_reason: status = "PASS"
            
        reason_str = ", ".join(fail_reason) if fail_reason else "OK"
        log(f"[{status}] {f}: R={r:.1f} G={g:.1f} B={b:.1f} | IsRed={is_red} IsBlue={is_blue} | OCR='{text}' | Reason: {reason_str}")

if __name__ == "__main__":
    if os.path.exists("analysis_result.txt"):
        os.remove("analysis_result.txt")
    process_folder("debug_imgs/釜底抽薪", "RED")
    process_folder("debug_imgs/釜底抽薪(己)", "BLUE")
