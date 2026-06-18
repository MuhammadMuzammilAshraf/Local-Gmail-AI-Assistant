import logging
import sys

from langchain_ollama import OllamaLLM

from audio_helpers import load_tts, load_whisper
from config import LOG_FILE, OLLAMA_MODEL, POLL_INTERVAL_SECONDS
from gmail_client import get_gmail_service
from watcher import run_watcher_mode

log = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def main():
    setup_logging()

    print("\n" + "=" * 60)
    print("  Gmail Assistant — Kokoro TTS")
    print("=" * 60)

    log.info("Connecting to Gmail...")
    service = get_gmail_service()
    log.info("Gmail connected.")

    log.info(f"Loading {OLLAMA_MODEL}...")
    llm = OllamaLLM(model=OLLAMA_MODEL, temperature=0.2)
    log.info("LLM ready.")

    tts = load_tts()
    whisper_model = load_whisper()

    run_watcher_mode(
        service,
        llm,
        tts,
        whisper_model,
        interval=POLL_INTERVAL_SECONDS,
        fast_mode=False,
    )


if __name__ == "__main__":
    main()
