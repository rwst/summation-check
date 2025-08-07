# file_monitor.py
"""
File system monitor for the Summation Check application.

This module watches the specified downloads directory and project file
location for new files or modifications using the 'watchdog' library.
"""

import time
import os
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from PyQt5.QtCore import QObject, pyqtSignal
from config import config

logger = logging.getLogger(__name__)

class FileChangeHandler(FileSystemEventHandler, QObject):
    """
    Handles file system events.
    """
    # Signals to notify the controller of file changes
    pdf_detected = pyqtSignal(str)
    project_file_changed = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)
        FileSystemEventHandler.__init__(self)
        self.project_file_path = os.path.abspath(config.get("project_file_path"))
        self.pdf_folder = config.get("dedicated_pdf_folder")
        self.processed_files = {}

    def on_created(self, event):
        """Called when a file or directory is created."""
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            # Check if this file has been processed recently
            if event.src_path in self.processed_files and \
               time.time() - self.processed_files[event.src_path] < 5: # 5-second cooldown
                return
            
            logger.info(f"New PDF detected: {event.src_path}")
            try:
                # Wait a moment for the file to be fully written
                time.sleep(1)
                
                file_name = os.path.basename(event.src_path)
                destination_path = os.path.join(self.pdf_folder, file_name)
                
                # Check the file operation from config
                file_operation = config.get("file_operation", "Move") # Default to Move
                
                if file_operation == "Copy":
                    shutil.copy2(event.src_path, destination_path)
                    logger.info(f"Copied PDF to: {destination_path}")
                else: # Default to "Move"
                    shutil.move(event.src_path, destination_path)
                    logger.info(f"Moved PDF to: {destination_path}")
                
                # Mark as processed
                self.processed_files[event.src_path] = time.time()
                self.pdf_detected.emit(destination_path)
            except (shutil.Error, IOError) as e:
                logger.error(f"Error processing file {event.src_path}: {e}")


    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if isinstance(event, FileModifiedEvent) and os.path.abspath(event.src_path) == self.project_file_path:
             logger.info(f"Project file changed: {event.src_path}")
             self.project_file_changed.emit(event.src_path)


class FileMonitor:
    """
    Manages the file system watching.
    """
    def __init__(self):
        self.downloads_path = config.get("downloads_folder")
        self.project_path = config.get("project_file_path")
        self.dedicated_pdf_folder = config.get("dedicated_pdf_folder")
        # Ensure the dedicated PDF folder exists
        if not os.path.exists(self.dedicated_pdf_folder):
            os.makedirs(self.dedicated_pdf_folder)
        # Create the event handler
        self.event_handler = FileChangeHandler()
        self.observer = None

    def start(self):
        """
        Starts watching the specified directories.
        """
        self.observer = Observer()
        if os.path.isdir(self.downloads_path):
            self.observer.schedule(self.event_handler, self.downloads_path, recursive=True)
        
        project_dir = os.path.dirname(self.project_path)
        if os.path.isdir(project_dir):
            self.observer.schedule(self.event_handler, project_dir, recursive=False)

        if self.observer.emitters:
            self.observer.start()
            logger.info(f"Started monitoring {self.downloads_path} and {os.path.dirname(self.project_path)}")
        else:
            logger.warning("Monitoring could not be started. Check config paths.")


    def stop(self):
        """
        Stops watching the directories.
        """
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped monitoring.")


    def update_paths(self):
        """
        Updates the paths to monitor from the config.
        """
        self.downloads_path = config.get("downloads_folder")
        self.project_path = config.get("project_file_path")
        self.event_handler.project_file_path = os.path.abspath(self.project_path)
        self.event_handler.pdf_folder = config.get("dedicated_pdf_folder")
        logger.info(f"Updated monitored paths: {self.downloads_path} and {self.project_path}")
        # The observer needs to be restarted to monitor new paths
        self.stop()
        self.start()
