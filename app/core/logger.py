import os
from datetime import datetime

class Logger:
    def __init__(self):
        os.makedirs("data/logs", exist_ok=True)
        self.file = "data/logs/system.log"

    def log(self, msg):
        with open(self.file, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {msg}\n")
