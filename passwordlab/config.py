from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(__file__).resolve().parent / "passwordlab.db"

# Fixed lab endpoint; never accept this value from natural-language input.
LAB_BASE_URL = "http://127.0.0.1:8000"
HEALTH_URL = f"{LAB_BASE_URL}/health"
ACCOUNTS_URL = f"{LAB_BASE_URL}/lab/accounts"
LOGIN_URL = f"{LAB_BASE_URL}/login"

HARD_MAX_ATTEMPTS = 2000
DEFAULT_MAX_ATTEMPTS = 100
REQUEST_TIMEOUT_SECONDS = 2
MAX_RUN_SECONDS = 120

# Deliberately tiny search space for classroom demonstration.
BRUTE_ALPHABET = "abc123"
BRUTE_MAX_LENGTH = 3
