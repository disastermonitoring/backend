from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "logs"

APP_LOG_FILE = LOGS_DIR / "app.log"
MODEL_LOG_FILE = LOGS_DIR / "models.log"
DECISION_LOG_FILE = LOGS_DIR / "decisions.log"
COMMUNICATION_LOG_FILE = LOGS_DIR / "communications.log"
FIELD_LOG_FILE = LOGS_DIR / "field_feedback.log"

