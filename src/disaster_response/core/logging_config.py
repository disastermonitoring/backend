import logging
import logging.config

from src.disaster_response.core.settings import (
    APP_LOG_FILE,
    COMMUNICATION_LOG_FILE,
    DECISION_LOG_FILE,
    FIELD_LOG_FILE,
    LOGS_DIR,
    MODEL_LOG_FILE,
)


def configure_logging() -> None:
    """Configure application logging with separate files per subsystem."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": "INFO",
                },
                "app_file": {
                    "class": "logging.FileHandler",
                    "filename": str(APP_LOG_FILE),
                    "formatter": "standard",
                    "level": "INFO",
                    "encoding": "utf-8",
                },
                "model_file": {
                    "class": "logging.FileHandler",
                    "filename": str(MODEL_LOG_FILE),
                    "formatter": "standard",
                    "level": "INFO",
                    "encoding": "utf-8",
                },
                "decision_file": {
                    "class": "logging.FileHandler",
                    "filename": str(DECISION_LOG_FILE),
                    "formatter": "standard",
                    "level": "INFO",
                    "encoding": "utf-8",
                },
                "communication_file": {
                    "class": "logging.FileHandler",
                    "filename": str(COMMUNICATION_LOG_FILE),
                    "formatter": "standard",
                    "level": "INFO",
                    "encoding": "utf-8",
                },
                "field_file": {
                    "class": "logging.FileHandler",
                    "filename": str(FIELD_LOG_FILE),
                    "formatter": "standard",
                    "level": "INFO",
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "disaster_response": {
                    "handlers": ["console", "app_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "disaster_response.models": {
                    "handlers": ["console", "model_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "disaster_response.decisions": {
                    "handlers": ["console", "decision_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "disaster_response.communications": {
                    "handlers": ["console", "communication_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "disaster_response.field": {
                    "handlers": ["console", "field_file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["console", "app_file"],
                "level": "INFO",
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
