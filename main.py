# main.py
"""
The main entry point for the Summation Check application. 

This script initializes the application, creates the main window,
and starts the event loop.
"""

import sys
import logging
import atexit
from PyQt5.QtWidgets import QApplication
from ui_view import MainAppWindow
from controller import Controller
from logger import setup_logger, QLogHandler
from config import config  # Import the loaded config

def main():
    """
    Initializes and runs the application.
    """
    # Set up logging
    logger = setup_logger()
    logger.info("Application starting...")

    # --- Prevent logging's atexit hook from running ---
    # This is crucial to avoid a RuntimeError when the QLogHandler (a C++ object)
    # is destroyed by Qt before Python's logging shutdown hook can access it.
    # We will manually handle the shutdown sequence.
    atexit.unregister(logging.shutdown)

    # Create the application instance
    app = QApplication(sys.argv)

    # Set up the logging handler for the UI
    log_handler = QLogHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(formatter)
    logging.getLogger().addHandler(log_handler)

    # Create the main window and controller
    main_window = MainAppWindow()
    controller = Controller(main_window, log_handler)

    # Connect the log handler to the UI
    log_handler.log_emitted.connect(main_window.update_status_display)

    # Show the main window
    main_window.show()
    logger.info("Application started successfully.")
    
    # Start the event loop and wait for it to exit
    exit_code = app.exec_()
    
    # --- Graceful Shutdown ---
    # 1. First, clean up our application's resources, which includes closing
    #    and removing the custom QLogHandler.
    logger.info("Application event loop finished. Cleaning up controller...")
    controller.cleanup()
    
    # 2. Now that the Qt-based handler is gone, we can safely run the standard
    #    logging shutdown process to flush and close any remaining handlers (e.g., file logger).
    logger.info("Shutting down logging.")
    logging.shutdown()
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
