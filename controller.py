# controller.py
"""
The core logic/controller module for the Summation Check application.

This module acts as the central hub, coordinating interactions between
the UI (view), the file system monitor, and data processing modules.
"""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

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
        self.status_updated.connect(self.view.update_status_display)
        self.error_occurred.connect(self.view.update_status_display)


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
