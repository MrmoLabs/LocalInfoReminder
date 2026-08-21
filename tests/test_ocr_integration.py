import unittest
import sys
import os
from pathlib import Path
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from core.vision.time_recognizer import TimeRecognizer
from core.vision.skill_detector import SkillDetector
from core.vision.boss_detector import BossDetector

class MockMss:
    def __init__(self, img_bgr):
        # Convert BGR (cv2 default) to BGRA (mss default)
        self.img_bgra = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2BGRA)
        self.monitors = [{}, {"top": 0, "left": 0, "width": img_bgr.shape[1], "height": img_bgr.shape[0]}]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def grab(self, region):
        # region: top, left, width, height
        x = region['left']
        y = region['top']
        w = region['width']
        h = region['height']
        
        # Crop safely
        return self.img_bgra[y:y+h, x:x+w]

class TestOCRIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("RUN_OCR_INTEGRATION") != "1":
            raise unittest.SkipTest("Set RUN_OCR_INTEGRATION=1 to run screenshot OCR tests")
        print("Loading RapidOCR model...")
        cls.ocr = RapidOCR()
        cls.base_path = Path(__file__).resolve().parents[1] / "debug_imgs"

    def _load_images_from_folder(self, folder_name):
        full_path = os.path.join(self.base_path, folder_name)
        if not os.path.exists(full_path):
            print(f"[WARN] Folder not found: {folder_name}")
            return []
            
        images = []
        for f in os.listdir(full_path):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                p = os.path.join(full_path, f)
                img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), -1) # Handle unicode path
                if img is not None:
                    images.append((f, img))
        return images

    def test_time_main_timer(self):
        """Verify Main Timer (<30m) detection."""
        images = self._load_images_from_folder("time_main")
        if not images: self.skipTest("No time_main images")
        
        tr = TimeRecognizer(self.ocr)
        
        for name, img in images:
            h, w = img.shape[:2]
            monitor = {"top": 0, "left": 0, "width": w, "height": h}
            
            # Mock MSS
            mss_mock = MockMss(img)
            
            # Force Process
            res = tr.process(mss_mock, monitor, sync_requested=True)
            print(f"Image {name}: {res}")
            
            self.assertIsNotNone(res, f"Failed to detect time in {name}")
            self.assertTrue(":" in res, f"Invalid time format in {name}: {res}")

    @unittest.skip("Skipped by user request due to ROI mismatch in provided assets")
    def test_time_prep_timer(self):
        """Verify Prep Timer (>30m) detection logic."""
        images = self._load_images_from_folder("time_prep")
        if not images: self.skipTest("No time_prep images")
        
        tr = TimeRecognizer(self.ocr)
        
        # Enable debug capture to ensure code path coverage
        tr.trigger_debug_prep_capture()
        
        for name, img in images:
            h, w = img.shape[:2]
            monitor = {"top": 0, "left": 0, "width": w, "height": h}
            
            mss_mock = MockMss(img)
            res = tr.process(mss_mock, monitor, sync_requested=True)
            print(f"Image {name}: {res}")
            
            self.assertIsNotNone(res, f"Failed to detect prep time in {name} (Strict Mode)")
            mins = int(res.split(":")[0])
            self.assertGreaterEqual(mins, 30, f"Prep time logic failed in {name}: {res}")

    def test_skill_enemy(self):
        """Verify Command Skill Detection (Red Text)."""
        images = self._load_images_from_folder("skill_enemy")
        if not images: self.skipTest("No skill_enemy images")
        
        sd = SkillDetector(self.ocr)
        sd.trigger_cooldown = 0 # Disable debounce
        
        for name, img in images:
            h, w = img.shape[:2]
            monitor = {"top": 0, "left": 0, "width": w, "height": h}
            
            mss_mock = MockMss(img)
            res = sd.process(mss_mock, monitor, paused=False)
            print(f"Image {name}: {res}")
            
            self.assertIsNotNone(res, f"Failed to detect command skill in {name}")
            # Ensure it is NOT ally
            self.assertNotEqual(res, "Ally Healing Reduction")

    def test_boss_spawn(self):
        """Verify target event appearance notification."""
        images = self._load_images_from_folder("boss_reappears") # Legacy name from task
        if not images: 
            # Try new name
            images = self._load_images_from_folder("boss_spawn")
            
        if not images: self.skipTest("No boss_spawn images")
        
        bd = BossDetector(self.ocr)
        bd.set_spawn_check(True)
        bd.last_boss_trigger_time = 0 # Reset throttle
        
        for name, img in images:
            h, w = img.shape[:2]
            monitor = {"top": 0, "left": 0, "width": w, "height": h}
            
            # Reset throttle per image
            bd.last_boss_trigger_time = 0
            
            mss_mock = MockMss(img)
            events = bd.process(mss_mock, monitor)
            print(f"Image {name}: {events}")
            
            self.assertTrue(any(e[0] == 'spawn' for e in events), f"Failed to detect spawn in {name}")

    def test_boss_kill(self):
        """Verify target event completion side detection."""
        # Ally Checks
        images_ally = self._load_images_from_folder("boss_kill_ally")
        bd = BossDetector(self.ocr)
        bd.set_kill_check(True)
        
        for name, img in images_ally:
            h, w = img.shape[:2]
            monitor = {"top": 0, "left": 0, "width": w, "height": h}
            mss_mock = MockMss(img)
            
            # Reset throttle PER IMAGE
            bd.last_boss_kill_check_time = 0
            bd.last_kill_signal_time = 0
            
            events = bd.process(mss_mock, monitor)
            print(f"Image {name}: {events}")
            
            kills = [e for e in events if e[0] == 'kill']
            self.assertTrue(kills, f"No kill detected in {name}")
            self.assertEqual(kills[0][1], "ally", f"Expected friendly-side completion in {name}")

        # Enemy Checks
        images_enemy = self._load_images_from_folder("boss_kill_enemy")
        
        for name, img in images_enemy:
            h, w = img.shape[:2]
            monitor = {"top": 0, "left": 0, "width": w, "height": h}
            mss_mock = MockMss(img)
            
            # Reset throttle PER IMAGE
            bd.last_boss_kill_check_time = 0
            bd.last_kill_signal_time = 0
            
            events = bd.process(mss_mock, monitor)
            print(f"Image {name}: {events}")
            
            kills = [e for e in events if e[0] == 'kill']
            self.assertTrue(kills, f"No kill detected in {name}")
            self.assertEqual(kills[0][1], "enemy", f"Expected opponent-side completion in {name}")

if __name__ == '__main__':
    unittest.main()
