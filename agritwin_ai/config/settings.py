from pathlib import Path
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MAX_STEPS = 5

MAX_RETRIES = 3

MAX_MEMORY = 15