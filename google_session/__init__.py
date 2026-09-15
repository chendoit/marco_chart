"""Google session storage paths and browser helpers."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOOGLE_STORAGE_STATE = PROJECT_ROOT / "google_storage_state.json"
MACROMICRO_STORAGE_STATE = PROJECT_ROOT / "macromicro_storage_state.json"
DEFAULT_MACROMICRO_LOGIN_URL = "https://www.macromicro.me/login"

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]
