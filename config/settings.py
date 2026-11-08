import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_DIR / ".env"

load_dotenv(ENV_FILE)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8090"))
DEBUG = os.getenv("DEBUG", "false").lower() in ('true', '1', 't')
TIMEZONE_NAME = os.getenv("TIMEZONE_NAME", "Europe/Moscow")

# STT
STT_MODEL = os.getenv("STT_MODEL", "small")
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")
STT_COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")

# Classifier
CLASSIFIER_MODEL = os.getenv("CLASSIFIER_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
CLASSIFIER_THRESHOLD = float(os.getenv("CLASSIFIER_THRESHOLD", 0.55))
CLASSIFIER_MARGIN = float(os.getenv("CLASSIFIER_MARGIN", 0.05))
# TTS
TTS_ENGINE = os.getenv("TTS_ENGINE", "silero").strip().lower()
TTS_VOICE_DIR = PROJECT_DIR / os.getenv("TTS_VOICE_DIR", "tts/voices/marusya")

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8082")

WEATHER_CITY = os.getenv("WEATHER_CITY", "Москва")