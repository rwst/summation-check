# main.py
"""
The main entry point for the Summation Check application. 

This script initializes the application, creates the main window,
and starts the event loop.
"""

import sys
import logging
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

    # Show the main window and start the application
    main_window.show()
    logger.info("Application started successfully.")
    
    # Ensure the file monitor is stopped gracefully when the app closes
    app.aboutToQuit.connect(controller.cleanup)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
