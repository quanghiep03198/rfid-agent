import logging
import os


class CustomFormatter(logging.Formatter):
    # Define colors for each level
    __COLORS = {
        "DEBUG": "\033[94m",  # Blue color
        "INFO": "\033[92m",  # Green color
        "WARNING": "\033[93m",  # Yellow color
        "ERROR": "\033[91m",  # Red color
        "CRITICAL": "\033[91m",  # Red color
    }
    __RESET = "\033[0m"  # Reset color

    def format(self, record):
        # Make a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)
        levelname = record_copy.levelname

        record_copy.levelname = f"{self.__COLORS[levelname]}{levelname}{self.__RESET}"

        return super().format(record_copy)


# Create logs directory if it doesn't exist
log_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)
os.makedirs(log_dir, exist_ok=True)

# Error log path
error_log_path = os.path.join(log_dir, "error.log")

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  #

# Create console handler to display logs on console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # Display all logs from DEBUG level and above


console_handler.setFormatter(
    CustomFormatter(
        "\033[90m%(asctime)s\033[0m - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

# Create file handler to write logs to file
file_handler = logging.FileHandler(
    filename=error_log_path,
    mode="a",
    encoding="utf-8",
)
file_handler.setLevel(
    logging.ERROR
)  # Only write logs from ERROR level and above to file
file_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

# Ensure handlers are not added multiple times if file is imported multiple times
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
