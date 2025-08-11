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
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from PyQt5.QtCore import QObject, pyqtSignal
from config import config

logger = logging.getLogger(__name__)

def check_directory(path):
    """
    Checks if a directory exists and is accessible (readable and writable).
    
    Args:
        path (str): The path to the directory.
        
    Returns:
        bool: True if the directory exists and is accessible, False otherwise.
    """
    if not path or not os.path.isdir(path):
        logger.warning(f"Directory does not exist or is not set: {path}")
        return False
    if not os.access(path, os.R_OK | os.W_OK):
        logger.warning(f"Directory is not readable/writable: {path}")
        return False
    return True

class EventHandler(FileSystemEventHandler, QObject):
    """
    Handles file system events for downloads, project file, and PDF folder.
    """
    # Signals to notify the controller of file changes
    pdf_detected = pyqtSignal(str)
    project_file_changed = pyqtSignal(str)
    pdf_folder_changed = pyqtSignal()

    def __init__(self, controller):
        QObject.__init__(self)
        FileSystemEventHandler.__init__(self)
        self.controller = controller
        self.project_file_path = os.path.abspath(config.get("project_file_path", ""))
        self.pdf_folder = os.path.abspath(config.get("dedicated_pdf_folder", ""))
        self.downloads_folder = os.path.abspath(config.get("downloads_folder", ""))
        self.processed_files = {}

    def on_created(self, event):
        """Called when a file or directory is created."""
        if event.is_directory:
            return

        src_path_abs = os.path.abspath(event.src_path)
        
        # Event in Downloads Folder
        if src_path_abs.startswith(self.downloads_folder) and src_path_abs.lower().endswith('.pdf'):
            self.handle_new_download(src_path_abs)
        
        # Event in PDF Folder
        elif src_path_abs.startswith(self.pdf_folder):
            logger.info(f"Change detected in PDF folder (created): {src_path_abs}")
            self.pdf_folder_changed.emit()

    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        if event.is_directory:
            return
        
        src_path_abs = os.path.abspath(event.src_path)
        if src_path_abs.startswith(self.pdf_folder):
            logger.info(f"Change detected in PDF folder (deleted): {src_path_abs}")
            self.pdf_folder_changed.emit()

    def on_moved(self, event):
        """Called when a file or directory is moved or renamed."""
        if event.is_directory:
            return

        src_path_abs = os.path.abspath(event.src_path)
        dest_path_abs = os.path.abspath(event.dest_path)

        # If a file is moved out of or into the PDF folder
        if src_path_abs.startswith(self.pdf_folder) or dest_path_abs.startswith(self.pdf_folder):
            logger.info(f"Change detected in PDF folder (moved): {event.src_path} to {event.dest_path}")
            self.pdf_folder_changed.emit()

    def handle_new_download(self, src_path):
        """Handles a new PDF detected in the downloads folder."""
        if src_path in self.processed_files and \
           time.time() - self.processed_files[src_path] < 5: # 5-second cooldown
            return

        file_name = os.path.basename(src_path)
        if re.match(r'PMID:\d+', file_name):
            return
        
        logger.info(f"New PDF detected in downloads: {src_path}")
        try:
            time.sleep(1) # Wait for the file to be fully written
            
            destination_path = os.path.join(self.pdf_folder, file_name)
            file_operation = config.get("file_operation", "Move")
            
            if file_operation == "Copy":
                shutil.copy2(src_path, destination_path)
                logger.info(f"Copied PDF to: {destination_path}")
            else: # Default to "Move"
                shutil.move(src_path, destination_path)
                logger.info(f"Moved PDF to: {destination_path}")
            
            self.processed_files[src_path] = time.time()
            self.pdf_detected.emit(destination_path)
        except (shutil.Error, IOError, OSError) as e:
            error_message = f"Error processing file {src_path}: {e}"
            logger.error(error_message)
            self.controller.show_directory_warning(
                f"A file operation failed. Please check permissions.\n\nDetails: {error_message}"
            )

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if not event.is_directory and os.path.abspath(event.src_path) == self.project_file_path:
             logger.info(f"Project file changed: {event.src_path}")
             self.project_file_changed.emit(event.src_path)


class FileMonitor:
    """
    Manages the file system watching.
    """
    def __init__(self, controller):
        self.controller = controller
        self.observer = None
        self.event_handler = EventHandler(self.controller)
        self.update_paths() # Initialize paths

    def start(self):
        """
        Starts watching the specified directories if they are accessible.
        """
        if self.observer and self.observer.is_alive():
            self.stop()

        self.observer = Observer()
        
        # Schedule monitoring for accessible paths
        if self.downloads_folder_accessible:
            self.observer.schedule(self.event_handler, self.downloads_path, recursive=True)
        
        if self.project_path and os.path.isdir(os.path.dirname(self.project_path)):
            self.observer.schedule(self.event_handler, os.path.dirname(self.project_path), recursive=False)

        if self.pdf_folder_accessible:
            self.observer.schedule(self.event_handler, self.dedicated_pdf_folder, recursive=True)

        if self.observer.emitters:
            self.observer.start()
            logger.info("Started monitoring accessible paths.")
        else:
            logger.warning("Monitoring could not be started. Check config paths and permissions.")

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
        Updates the paths to monitor from the config and checks accessibility.
        """
        self.downloads_path = config.get("downloads_folder")
        self.project_path = config.get("project_file_path")
        self.dedicated_pdf_folder = config.get("dedicated_pdf_folder")

        # Update paths in the handler
        self.event_handler.downloads_folder = os.path.abspath(self.downloads_path) if self.downloads_path else ""
        self.event_handler.project_file_path = os.path.abspath(self.project_path) if self.project_path else ""
        self.event_handler.pdf_folder = os.path.abspath(self.dedicated_pdf_folder) if self.dedicated_pdf_folder else ""

        # Check accessibility
        self.downloads_folder_accessible = check_directory(self.downloads_path)
        self.pdf_folder_accessible = check_directory(self.dedicated_pdf_folder)
        
        logger.info("Updated monitored paths.")
        self.start() # Restart observer with new paths