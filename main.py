# main.py
"""
The main entry point for the Summation Check application. 

This script initializes the application, creates the main window,
and starts the event loop.
"""

import sys
from PyQt5.QtWidgets import QApplication
from ui_view import MainAppWindow
from controller import Controller
from logger import setup_logger
from file_monitor import FileMonitor
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

    # Create the main window and controller
    main_window = MainAppWindow()
    controller = Controller(main_window)

    # Set up the file monitor
    downloads_folder = config.get("downloads_folder")
    dedicated_pdf_folder = config.get("dedicated_pdf_folder")
    project_file = config.get("project_file_path")
    
    if not downloads_folder or not project_file or not dedicated_pdf_folder:
        logger.warning("Downloads/PDF folders or project file path not configured.")
    
    file_monitor = FileMonitor(downloads_folder, dedicated_pdf_folder, project_file)
    
    # Connect file monitor signals to controller slots
    file_monitor.event_handler.pdf_detected.connect(controller.on_pdf_detected)
    file_monitor.event_handler.summary_file_changed.connect(controller.on_summary_file_changed)
    
    # Start the monitor
    file_monitor.start()
    logger.info(f"Monitoring '{downloads_folder}' and '{project_file}'")

    # Show the main window and start the application
    main_window.show()
    logger.info("Application started successfully.")
    
    # Ensure the file monitor is stopped gracefully when the app closes
    app.aboutToQuit.connect(file_monitor.stop)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
