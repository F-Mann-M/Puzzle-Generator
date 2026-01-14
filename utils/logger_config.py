import logging.config
import sys


def configure_logging():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,

        # Formatters: How the logs look
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                # For production, you might want a JSON formatter class here
                # But standard string formatting is often sufficient for simple apps
                "format": "%(asctime)s %(levelname)s %(message)s"
            },
        },

        # Handlers: Where the logs go
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": "app_errors.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },

        # Loggers: The configuration for specific modules
        "loggers": {
            "": {  # The "root" logger (captures everything)
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True
            },
            "sqlalchemy.engine": {  # Example: Capture SQL queries
                "handlers": ["console"],
                "level": "WARNING",  # Set to INFO to see SQL queries
                "propagate": False
            },
        }
    }

    logging.config.dictConfig(logging_config)