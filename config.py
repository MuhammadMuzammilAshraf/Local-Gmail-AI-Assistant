import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"
LOG_FILE = BASE_DIR / "gmail_assistant.log"

OLLAMA_MODEL = "qwen2.5-coder:3b"

KOKORO_MODEL_FILE = BASE_DIR / "kokoro-v0_19.onnx"
KOKORO_VOICES_FILE = BASE_DIR / "voices.bin"
TTS_VOICE = "af_sarah"
TTS_SPEED = 1.0

WHISPER_MODEL = "base"
RECORD_SAMPLERATE = 16000
RECORD_SECONDS = 15
MAX_DRAFT_EMAILS = 5
POLL_INTERVAL_SECONDS = 120

WATCH_SENDERS = [
    "List of email addresses or domains to watch, e.g. 'example.com'",
]

DEFAULT_USER_NAME = "Your Name"
MAX_EMAIL_PREVIEW = 180
