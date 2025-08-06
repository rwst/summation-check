# controller.py
"""
The core logic/controller module for the Summation Check application.

This module acts as the central hub, coordinating interactions between
the UI (view), the file system monitor, and data processing modules.
"""
import os
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from config import config, save_config

class Controller(QObject):
    """
    The main controller for the application.
    """
    # Define signals that can be emitted to the UI or other components
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, view):
        """
        Initializes the Controller.

        Args:
            view: The main UI window instance.
        """
        super().__init__()
        self.view = view
        self.connect_signals()
        self.status_updated.emit("Controller initialized.")

    def connect_signals(self):
        """
        Connects signals from the UI to controller slots (methods).
        """
        self.view.start_qc_button.clicked.connect(self.start_qc_process)
        self.view.downloads_button.clicked.connect(self.select_downloads_folder)
        self.view.pdf_folder_button.clicked.connect(self.select_pdf_folder)
        self.view.project_file_button.clicked.connect(self.select_project_file)
        self.status_updated.connect(self.view.update_status_display)
        self.error_occurred.connect(self.view.update_status_display)

    def select_downloads_folder(self):
        """Opens a dialog to select the downloads folder."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select Downloads Folder")
        if folder:
            config["downloads_folder"] = folder
            save_config(config)
            self.view.downloads_button.setText(folder)
            self.status_updated.emit(f"Downloads folder set to: {folder}")

    def select_pdf_folder(self):
        """Opens a dialog to select the dedicated PDF folder."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select PDF Folder")
        if folder:
            config["dedicated_pdf_folder"] = folder
            save_config(config)
            self.view.pdf_folder_button.setText(folder)
            self.status_updated.emit(f"PDF folder set to: {folder}")

    def select_project_file(self):
        """Opens a dialog to select the project file."""
        file, _ = QFileDialog.getOpenFileName(
            self.view, 
            "Select Project File", 
            "", 
            "Reactome Project Files (*.rtpj)"
        )
        if file:
            config["project_file_path"] = file
            save_config(config)
            self.view.project_file_button.setText(file)
            self.status_updated.emit(f"Project file set to: {file}")

    @pyqtSlot(str)
    def on_pdf_detected(self, file_path):
        """
        Handles the event when a new PDF is detected.
        """
        self.status_updated.emit(f"New PDF detected: {file_path}")
        # Here you would add logic to process the PDF

    @pyqtSlot(str)
    def on_summary_file_changed(self, file_path):
        """
        Handles the event when the summary file is changed.
        """
        self.status_updated.emit(f"Summary file updated: {file_path}")
        # Here you would add logic to parse the summary file

    def start_qc_process(self):
        """
        Placeholder method for starting the Quality Control process.
        """
        self.status_updated.emit("QC process started.")
        # In a real application, this would trigger a series of actions:
        # 1. Validate that all necessary files are present.
        # 2. Start the PDF processing and metadata matching.
        # 3. Update the UI with the results.
        print("QC Process Started!")

    # Add other methods to handle application logic here
