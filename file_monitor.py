# file_monitor.py
"""
File system monitor for the Summation Check application.

This module watches the specified downloads directory and summary file
location for new files or modifications using the 'watchdog' library.
"""

import time
import os
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from PyQt5.QtCore import QObject, pyqtSignal
from config import config

class FileChangeHandler(FileSystemEventHandler, QObject):
    """
    Handles file system events.
    """
    # Signals to notify the controller of file changes
    pdf_detected = pyqtSignal(str)
    summary_file_changed = pyqtSignal(str)

    def __init__(self, summary_file_path, dedicated_pdf_folder):
        QObject.__init__(self)
        FileSystemEventHandler.__init__(self)
        self.summary_file_path = os.path.abspath(summary_file_path)
        self.pdf_folder = dedicated_pdf_folder

    def on_created(self, event):
        """Called when a file or directory is created."""
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            print(f"New PDF detected: {event.src_path}")
            try:
                # Wait a moment for the file to be fully written
                time.sleep(1)
                # Move the file
                file_name = os.path.basename(event.src_path)
                destination_path = os.path.join(self.pdf_folder, file_name)
                shutil.move(event.src_path, destination_path)
                print(f"Moved PDF to: {destination_path}")
                self.pdf_detected.emit(destination_path)
            except (shutil.Error, IOError) as e:
                print(f"Error moving file {event.src_path}: {e}")


    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if isinstance(event, FileModifiedEvent) and os.path.abspath(event.src_path) == self.summary_file_path:
             print(f"Summary file changed: {event.src_path}")
             self.summary_file_changed.emit(event.src_path)


class FileMonitor:
    """
    Manages the file system watching.
    """
    def __init__(self, downloads_path, dedicated_pdf_folder, project_path):
        self.downloads_path = downloads_path
        self.project_path = project_path
        self.dedicated_pdf_folder = dedicated_pdf_folder
        # Ensure the dedicated PDF folder exists
        if not os.path.exists(self.dedicated_pdf_folder):
            os.makedirs(self.dedicated_pdf_folder)
        # Create the event handler and observer
        self.event_handler = FileChangeHandler(self.project_path, self.dedicated_pdf_folder)
        self.observer = Observer()

    def start(self):
        """
        Starts watching the specified directories.
        """
        if os.path.isdir(self.downloads_path):
            self.observer.schedule(self.event_handler, self.downloads_path, recursive=True) # Recursive might be useful
        
        project_dir = os.path.dirname(self.project_path)
        if os.path.isdir(project_dir):
            self.observer.schedule(self.event_handler, project_dir, recursive=False)

        if self.observer.emitters:
            self.observer.start()
            print(f"Started monitoring {self.downloads_path} and {os.path.dirname(self.project_path)}")
        else:
            print("Monitoring could not be started. Check config paths.")


    def stop(self):
        """
        Stops watching the directories.
        """
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            print("Stopped monitoring.")

if __name__ == '__main__':
    # Example usage:
    # Create dummy files/dirs for testing
    if not os.path.exists("test_downloads"):
        os.makedirs("test_downloads")
    if not os.path.exists("test_summary"):
        os.makedirs("test_summary")
    if not os.path.exists("test_pdfs"):
        os.makedirs("test_pdfs")
    with open("test_summary/summary.txt", "w") as f:
        f.write("initial content")

    downloads = "test_downloads"
    summary = "test_summary/summary.txt"
    
    dedicated_pdfs = "test_pdfs"
    monitor = FileMonitor(downloads, summary, dedicated_pdfs)
    monitor.start()
    try:
        print("Monitoring... Create a .pdf file in 'test_downloads' or modify 'test_summary/summary.txt'.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
