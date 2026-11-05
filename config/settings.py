import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"

load_dotenv(ENV_FILE)

TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Europe/Moscow")