# logger.py
"""
Logging and error handling module for the Summation Check application.

Provides a centralized way to log application events and handle errors gracefully.
"""

import logging
import os
from PyQt5.QtCore import QObject, pyqtSignal

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "application.log")

class QLogHandler(QObject, logging.Handler):
    """
    A custom logging handler that emits a PyQt signal for each log record.
    """
    log_emitted = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)

    def emit(self, record):
        """
        Emits the formatted log record as a signal.
        """
        msg = self.format(record)
        self.log_emitted.emit(msg)

def setup_logger():
    """
    Sets up the global logger for the application.
    """
    # Create log directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create handlers
    # File handler for writing logs to a file
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)

    # Console handler for printing logs to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Custom Exception examples
class MetadataNotFoundError(Exception):
    """Custom exception for when metadata cannot be found."""
    pass

class PdfProcessingError(Exception):
    """Custom exception for errors during PDF processing."""
    pass

# Custom Exception examples
class MetadataNotFoundError(Exception):
    """Custom exception for when metadata cannot be found."""
    pass

class PdfProcessingError(Exception):
    """Custom exception for errors during PDF processing."""
    pass
