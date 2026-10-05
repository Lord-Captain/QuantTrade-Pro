# backend/tests/conftest.py
import sys
from pathlib import Path

# 确保可以 import app 包（tests 从 backend 目录运行时也兼容）
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
