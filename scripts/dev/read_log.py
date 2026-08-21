
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = ROOT / "logs" / "runtime" / "debug.log"

try:
    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        print("Last 200 lines:")
        for line in lines[-200:]:
            print(line.strip())
except Exception as e:
    print(f"Error reading log: {e}")
