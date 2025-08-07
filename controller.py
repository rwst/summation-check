# controller.py
"""
The core logic/controller module for the Summation Check application.

This module acts as the central hub, coordinating interactions between
the UI (view), the file system monitor, and data processing modules.
"""
import os
import logging
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from config import config, save_config
from file_monitor import FileMonitor
from match_metadata import match_pdf_to_metadata
from parse_project import extract_metadata_from_project_file

class Controller(QObject):
    """
    The main controller for the application.
    """
    # Define signals that can be emitted to the UI or other components
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, view, log_handler):
        """
        Initializes the Controller.

        Args:
            view: The main UI window instance.
            log_handler: The UI log handler.
        """
        super().__init__()
        self.view = view
        self.log_handler = log_handler
        self.file_monitor = FileMonitor()
        self.metadata_set = []
        self.connect_signals()
        self.status_updated.emit("Controller initialized.")
        self.file_monitor.start()
        self.load_initial_metadata()

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

        # Connect file monitor signals
        self.file_monitor.event_handler.pdf_detected.connect(self.on_pdf_detected)
        self.file_monitor.event_handler.project_file_changed.connect(self.on_project_file_changed)

    def select_downloads_folder(self):
        """Opens a dialog to select the downloads folder."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select Downloads Folder")
        if folder:
            config["downloads_folder"] = folder
            save_config(config)
            self.view.downloads_button.setText(folder)
            self.status_updated.emit(f"Downloads folder set to: {folder}")
            # Restart the monitor to watch the new folder
            self.file_monitor.update_paths()

    def select_pdf_folder(self):
        """Opens a dialog to select the dedicated PDF folder."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select PDF Folder")
        if folder:
            config["dedicated_pdf_folder"] = folder
            save_config(config)
            self.view.pdf_folder_button.setText(folder)
            self.status_updated.emit(f"PDF folder set to: {folder}")
            self.file_monitor.update_paths()
            self.process_existing_pdfs()

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
            # Restart the monitor to watch the new folder
            self.file_monitor.update_paths()

    def load_initial_metadata(self):
        """Loads metadata from the project file on startup."""
        project_file = config.get("project_file_path")
        if project_file and os.path.exists(project_file):
            self.on_project_file_changed(project_file)

    @pyqtSlot(str)
    def on_pdf_detected(self, file_path):
        """
        Handles the event when a new PDF is detected.
        """
        self.status_updated.emit(f"New PDF detected: {file_path}")
        if not self.metadata_set:
            self.status_updated.emit("No metadata loaded, cannot process new PDF.")
            return
        
        match = match_pdf_to_metadata(file_path, self.metadata_set)
        if match:
            logging.info(f"PDF '{os.path.basename(file_path)}' matched with metadata: '{match['title']}'")
            self.status_updated.emit(f"PDF '{os.path.basename(file_path)}' matched with: '{match['title']}'")
        else:
            logging.info(f"No match found for PDF '{os.path.basename(file_path)}'")
            self.status_updated.emit(f"No match for PDF: '{os.path.basename(file_path)}'")

    @pyqtSlot(str)
    def on_project_file_changed(self, file_path):
        """
        Handles the event when the project file is changed.
        """
        self.status_updated.emit(f"Project file updated: {file_path}. Loading new metadata.")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.metadata_set = extract_metadata_from_project_file(content)
            self.status_updated.emit(f"Successfully loaded {len(self.metadata_set)} metadata entries.")
            self.process_existing_pdfs()
        except Exception as e:
            self.error_occurred.emit(f"Error reading project file: {e}")
            logging.error(f"Error reading project file: {e}")

    def process_existing_pdfs(self):
        """
        Processes all PDFs in the dedicated folder against the current metadata.
        """
        pdf_folder = config.get("dedicated_pdf_folder")
        if not self.metadata_set:
            self.status_updated.emit("No metadata loaded, skipping PDF processing.")
            return

        if not os.path.exists(pdf_folder):
            self.status_updated.emit(f"PDF folder not found: {pdf_folder}")
            return

        self.status_updated.emit(f"Processing PDFs in {pdf_folder}...")
        for filename in os.listdir(pdf_folder):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(pdf_folder, filename)
                match = match_pdf_to_metadata(pdf_path, self.metadata_set)
                if match:
                    logging.info(f"PDF '{filename}' matched with metadata: '{match['title']}'")
                    self.status_updated.emit(f"PDF '{filename}' matched with: '{match['title']}'")
                else:
                    logging.info(f"No match found for PDF '{filename}'")
                    self.status_updated.emit(f"No match for PDF: '{filename}'")

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
        self.process_existing_pdfs()

    def cleanup(self):
        """Stops the file monitor and removes the log handler."""
        self.file_monitor.stop()
        logging.getLogger().removeHandler(self.log_handler)

    # Add other methods to handle application logic here
