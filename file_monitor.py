# file_monitor.py
"""
File system monitor for the Summation Check application.

This module watches the specified downloads directory and summary file
location for new files or modifications using the 'watchdog' library.
"""

import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from PyQt5.QtCore import QObject, pyqtSignal

class FileChangeHandler(FileSystemEventHandler, QObject):
    """
    Handles file system events.
    """
    # Signals to notify the controller of file changes
    pdf_detected = pyqtSignal(str)
    summary_file_changed = pyqtSignal(str)

    def __init__(self, summary_file_path):
        QObject.__init__(self)
        FileSystemEventHandler.__init__(self)
        self.summary_file_path = os.path.abspath(summary_file_path)

    def on_created(self, event):
        """Called when a file or directory is created."""
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            print(f"New PDF detected: {event.src_path}")
            self.pdf_detected.emit(event.src_path)

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if isinstance(event, FileModifiedEvent) and os.path.abspath(event.src_path) == self.summary_file_path:
             print(f"Summary file changed: {event.src_path}")
             self.summary_file_changed.emit(event.src_path)


class FileMonitor:
    """
    Manages the file system watching.
    """
    def __init__(self, downloads_path, summary_path):
        self.downloads_path = downloads_path
        self.summary_path = summary_path
        self.event_handler = FileChangeHandler(self.summary_path)
        self.observer = Observer()

    def start(self):
        """
        Starts watching the specified directories.
        """
        if os.path.isdir(self.downloads_path):
            self.observer.schedule(self.event_handler, self.downloads_path, recursive=True) # Recursive might be useful
        
        summary_dir = os.path.dirname(self.summary_path)
        if os.path.isdir(summary_dir):
            self.observer.schedule(self.event_handler, summary_dir, recursive=False)

        if self.observer.emitters:
            self.observer.start()
            print(f"Started monitoring {self.downloads_path} and {os.path.dirname(self.summary_path)}")
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
    with open("test_summary/summary.txt", "w") as f:
        f.write("initial content")

    downloads = "test_downloads"
    summary = "test_summary/summary.txt"
    
    monitor = FileMonitor(downloads, summary)
    monitor.start()
    try:
        print("Monitoring... Create a .pdf file in 'test_downloads' or modify 'test_summary/summary.txt'.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
