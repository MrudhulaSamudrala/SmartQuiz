import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DB_PATH = Path(__file__).resolve().parent / "quiz_history.db"

DIFFICULTIES = ["Easy", "Medium", "Hard"]
TIMER_OPTIONS = [5, 10, 15, 30, 60]
OPTION_LABELS = ["A", "B", "C", "D"]

QUIZ_TYPES = ["MCQ", "True/False", "One Word Answer", "Mixed"]
QUIZ_TYPE_MCQ = "MCQ"
QUIZ_TYPE_TF = "True/False"
QUIZ_TYPE_ONE_WORD = "One Word Answer"
QUIZ_TYPE_MIXED = "Mixed"

TYPE_MCQ = "mcq"
TYPE_TRUE_FALSE = "true_false"
TYPE_ONE_WORD = "one_word"

QUIZ_MODES = ["Timed Quiz", "No Timer Quiz"]
MODE_TIMED = "Timed Quiz"
MODE_UNTIMED = "No Timer Quiz"

QUIZ_SOURCES = ["Topic / Subject", "PDF Upload"]
SOURCE_TOPIC = "Topic / Subject"
SOURCE_PDF = "PDF Upload"

# PDF extracted text limits (topic mode uses short keywords — no min length)
MAX_CONTENT_CHARS = 14_000
MIN_PDF_CONTENT_CHARS = 100

GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "").strip(),
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]
GEMINI_MODELS = [m for m in GEMINI_MODELS if m]

TYPE_LABELS = {
    TYPE_MCQ: "MCQ",
    TYPE_TRUE_FALSE: "True/False",
    TYPE_ONE_WORD: "One Word",
}
