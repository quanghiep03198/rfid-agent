import logging
import os

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the minimum logging level


class CustomFormatter(logging.Formatter):
    # Define color codes for different log levels
    COLORS = {
        "DEBUG": "\033[94m",  # Indigo
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m",  # Magenta
    }
    RESET = "\033[0m"  # Reset màu
    TIME_COLOR = "\033[90m"  # Grey for time

    def format(self, record):
        levelname = record.levelname
        # Only colorize if the output is to the console (StreamHandler)
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


# Create console handler for output to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Set the minimum logging level for console
console_handler.setFormatter(
    CustomFormatter(
        "\033[90m%(asctime)s\033[0m - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)


# Add handlers to the logger if they haven't been added already
if not logger.handlers:
    logger.addHandler(console_handler)
