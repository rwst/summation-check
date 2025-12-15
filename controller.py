# controller.py
"""
The core logic/controller module for the Summation Check application.

This module acts as the central hub, coordinating interactions between
the UI (view), the file system monitor, and data processing modules.
"""
import os
import logging
import re
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from config import config, save_config
from file_monitor import FileMonitor
from match_metadata import match_pdf_to_metadata
from parse_project import extract_metadata_from_project_file, get_summary_for_event, extract_event_data
from prep_ai_critique import get_pdf_texts_for_pmids, get_ai_critique
from ui_view import CritiqueWindow


class AiCritiqueWorker(QObject):
    """
    Worker thread for running the AI critique API call without blocking the GUI.
    """
    finished = pyqtSignal(object)

    def __init__(self, summary_text, pdf_data, api_key, model, prompt):
        super().__init__()
        self.summary_text = summary_text
        self.pdf_data = pdf_data
        self.api_key = api_key
        self.model = model
        self.prompt = prompt

    @pyqtSlot()
    def run(self):
        """Runs the AI critique and emits the result."""
        result = get_ai_critique(self.summary_text, self.pdf_data, self.api_key, self.model, self.prompt)
        self.finished.emit(result)



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
        self.file_monitor = FileMonitor(self)
        self.metadata_set = []
        self.pmid_hint = None
        self.connect_signals()
        self.status_updated.emit("Controller initialized.")
        self.file_monitor.start()
        self.load_initial_metadata()
        self.critique_thread = None
        self.critique_worker = None

    def connect_signals(self):
        """
        Connects signals from the UI to controller slots (methods).
        """
        self.view.downloads_button.clicked.connect(self.select_downloads_folder)
        self.view.pdf_folder_button.clicked.connect(self.select_pdf_folder)
        self.view.project_file_button.clicked.connect(self.select_project_file)
        self.status_updated.connect(self.view.update_status_display)
        self.error_occurred.connect(self.view.update_status_display)

        # Connect file monitor signals
        self.file_monitor.event_handler.pdf_detected.connect(self.on_pdf_detected)
        self.file_monitor.event_handler.project_file_changed.connect(self.on_project_file_changed)
        self.file_monitor.event_handler.pdf_folder_changed.connect(self.on_pdf_folder_changed)
        self.file_monitor.event_handler.error_occurred.connect(self.show_directory_warning)

    def show_directory_warning(self, message, title="Warning"):
        """Shows a warning message box."""
        self.view.show_warning_message(title, message)

    def _save_config(self):
        if not save_config(config):
            self.show_directory_warning(
                "Configuration Error",
                "Could not save configuration file. Please check permissions for the user config directory."
            )

    def select_downloads_folder(self):
        """Opens a dialog to select the downloads folder."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select Downloads Folder")
        if folder:
            config["downloads_folder"] = folder
            self._save_config()
            self.view.downloads_button.setText(folder)
            self.status_updated.emit(f"Downloads folder set to: {folder}")
            # Restart the monitor to watch the new folder
            self.file_monitor.update_paths()

    def select_pdf_folder(self):
        """Opens a dialog to select the dedicated PDF folder."""
        folder = QFileDialog.getExistingDirectory(self.view, "Select PDF Folder")
        if folder:
            config["dedicated_pdf_folder"] = folder
            self._save_config()
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
            self._save_config()
            self.view.project_file_button.setText(file)
            self.status_updated.emit(f"Project file set to: {file}")
            # Restart the monitor to watch the new folder
            self.file_monitor.update_paths()
            self.on_project_file_changed(file)

    def load_initial_metadata(self):
        """Loads metadata from the project file on startup."""
        project_file = config.get("project_file_path")
        if project_file and os.path.exists(project_file):
            self.on_project_file_changed(project_file)

    @pyqtSlot(str)
    def set_pmid_hint(self, pmid):
        """Sets the PMID hint for the next PDF."""
        self.pmid_hint = pmid
        self.status_updated.emit(f"PMID hint set to {pmid}. The next unmatched PDF will be associated with this PMID.")

    @pyqtSlot(str, str)
    def on_pdf_association_requested(self, pmid, file_path):
        """
        Handles PDF association request from QC window.
        Renames the selected PDF file with PMID prefix.
        """
        try:
            directory = os.path.dirname(file_path)
            original_filename = os.path.basename(file_path)
            new_filename = f"PMID:{pmid}-{original_filename}"
            new_filepath = os.path.join(directory, new_filename)

            os.rename(file_path, new_filepath)
            logging.info(f"Associated PDF '{original_filename}' with PMID:{pmid}")

            # Refresh the QC view
            if self.view.qc_window:
                self.view.qc_window.refresh_selected_item()
        except OSError as e:
            error_message = f"Could not rename the file: {e}"
            logging.error(error_message)
            self.show_directory_warning(error_message, title="Error Renaming File")

    @pyqtSlot(str)
    def on_pdf_detected(self, file_path):
        """
        Handles the event when a new PDF is detected.
        """
        self.status_updated.emit(f"New PDF detected: {file_path}")
        if not self.metadata_set:
            self.status_updated.emit("No metadata loaded, cannot process new PDF.")
            return

        match = None
        if self.pmid_hint:
            match = {'pubMedIdentifier': self.pmid_hint, 'title': f'Manually Associated with PMID:{self.pmid_hint}'}
            self.status_updated.emit(f"Using hint to associate PDF with PMID: {self.pmid_hint}")
        else:
            match = match_pdf_to_metadata(file_path, self.metadata_set)

        if match:
            self._handle_successful_match(file_path, match)
        else:
            logging.info(f"No match found for PDF '{os.path.basename(file_path)}'")

    def _handle_successful_match(self, pdf_path, match):
        """
        Handles the consequences of a successful PDF match: renaming and cache cleanup.
        """
        try:
            # --- Delete .title file ---
            pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
            title_file_path = os.path.join(os.path.dirname(pdf_path), f"{pdf_basename}.title")
            if os.path.exists(title_file_path):
                try:
                    os.remove(title_file_path)
                    logging.info(f"Removed cache file: {os.path.basename(title_file_path)}")
                except OSError as e:
                    logging.error(f"Error removing cache file {title_file_path}: {e}")

            if 'pubMedIdentifier' in match and match['pubMedIdentifier']:
                original_filename = os.path.basename(pdf_path)
                new_filename = f"PMID:{match['pubMedIdentifier']}-{original_filename}"
                new_filepath = os.path.join(os.path.dirname(pdf_path), new_filename)
                
                os.rename(pdf_path, new_filepath)
                
                logging.info(f"PDF '{original_filename}' matched with metadata: '{match['title']}' and renamed to '{new_filename}'")

                # After a successful rename, the "next PDF" has been handled. Clear the hint.
                if self.pmid_hint:
                    self.status_updated.emit(f"Cleared PMID hint ({self.pmid_hint}) after successful match.")
                    self.pmid_hint = None
            else:
                logging.info(f"PDF '{os.path.basename(pdf_path)}' matched with metadata: '{match['title']}' (no PMID for renaming)")
        except (OSError, Exception) as e:
            error_message = f"Error processing file {pdf_path}: {e}"
            logging.error(error_message)
            self.error_occurred.emit(error_message)

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

            # If QC window is open, refresh its data
            if self.view.qc_window and self.view.qc_window.isVisible():
                self.status_updated.emit("Project file changed. Refreshing QC view.")
                event_data = extract_event_data(content)
                if event_data:
                    sorted_project_data = sorted(event_data, key=lambda x: x.get('name', 'Unnamed').lower())
                    self.view.qc_window.update_data(sorted_project_data)
                    project_file_name = os.path.basename(file_path)
                    self.view.qc_window.setWindowTitle(f"QC: {project_file_name}")
                    self.status_updated.emit(f"QC Window updated. Loaded {len(event_data)} items.")
                else:
                    self.view.qc_window.update_data([]) # Clear lists
                    self.status_updated.emit("No data could be extracted from project file, QC view cleared.")

            self.process_existing_pdfs()
        except (IOError, OSError, Exception) as e:
            error_message = f"Error reading project file: {e}"
            self.error_occurred.emit(error_message)
            logging.error(error_message)
            self.show_directory_warning(
                f"Could not read the project file. Please check the file path and permissions.\n\nDetails: {e}",
                title="Project File Error"
            )

    @pyqtSlot()
    def on_pdf_folder_changed(self):
        """
        Handles the event when the PDF folder content changes.
        """
        if self.view.qc_window and self.view.qc_window.isVisible():
            self.status_updated.emit("PDF folder changed. Refreshing QC view.")
            self.view.qc_window.refresh_selected_item()

    def update_timer(self):
        """Updates the timer label in the QC window."""
        if self.view.qc_window:
            self.view.qc_window.elapsed_time += 1
            self.view.qc_window.timer_label.setText(f"Requesting critique... {self.view.qc_window.elapsed_time}s")

    def _reset_critique_state(self):
        """Resets critique running state after an error."""
        if self.view.qc_window:
            self.view.qc_window.timer.stop()
            self.view.qc_window.timer_label.hide()
            self.view.qc_window.is_critique_running = False
            self.view.qc_window.refresh_selected_item()

    def on_ai_critique_clicked(self):
        """
        Handles the click of the 'Get AI Critique' button by running it in a worker thread.
        """
        if not self.view.qc_window:
            return

        # Guard against re-entry
        if self.view.qc_window.is_critique_running:
            return

        # Set running state immediately to prevent re-entry
        self.view.qc_window.is_critique_running = True
        self.view.qc_window.ai_critique_button.setEnabled(False)
        self.view.qc_window.elapsed_time = 0
        self.view.qc_window.timer_label.setText("Requesting critique... 0s")
        self.view.qc_window.timer_label.show()
        self.view.qc_window.timer.start(1000)

        self.status_updated.emit("Starting AI critique preparation...")

        # 1. Get summary text for the selected event
        selected_items = self.view.qc_window.list_events.selectedItems()
        if not selected_items:
            selected_items = self.view.qc_window.list_pathways.selectedItems()
            if not selected_items:
                self.show_directory_warning("No item selected in any list.", title="Selection Error")
                self._reset_critique_state()
                return

        db_id = selected_items[0].data(0x0100) # UserRole
        project_file = config.get("project_file_path")
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except (IOError, OSError) as e:
            self.show_directory_warning(f"Could not read project file: {e}", title="File Error")
            self._reset_critique_state()
            return

        summary_text = get_summary_for_event(xml_content, db_id)
        if not summary_text:
            self.show_directory_warning(f"No summary found for DB_ID {db_id}", title="Data Error")
            self._reset_critique_state()
            return

        # 2. Get PDF texts
        list_widget = self.view.qc_window.list2
        items = [list_widget.item(i).text() for i in range(list_widget.count())]
        pdf_folder = config.get("dedicated_pdf_folder")
        pdf_data = get_pdf_texts_for_pmids(items, pdf_folder)

        if not pdf_data:
            self.show_directory_warning("No PDF data could be extracted.", title="PDF Error")
            self._reset_critique_state()
            return

        self.status_updated.emit("Calling Gemini API for critique...")
        api_key = config.get("GEMINI_API_KEY")
        model = config.get("critique_model", "gemini-2.5-pro")
        prompt = config.get("critique_prompt", "")

        # Setup and start the thread
        self.critique_thread = QThread()
        self.critique_worker = AiCritiqueWorker(summary_text, pdf_data, api_key, model, prompt)
        self.critique_worker.moveToThread(self.critique_thread)
        
        self.critique_thread.started.connect(self.critique_worker.run)
        self.critique_worker.finished.connect(self.on_ai_critique_finished)
        
        self.critique_thread.start()

    def on_ai_critique_finished(self, critique_result):
        """
        Handles the result from the AI critique worker thread.
        """
        # Stop the timer and hide the label
        self.view.qc_window.timer.stop()
        self.view.qc_window.timer_label.hide()

        # Display result in a new window
        critique_window = CritiqueWindow(critique_result, self.view.qc_window)
        critique_window.exec_()
        self.status_updated.emit("Critique window closed.")

        # Clean up the thread
        self.critique_thread.quit()
        self.critique_thread.wait()
        self.critique_thread = None
        self.critique_worker = None

        # Update button state by refreshing the view
        self.view.qc_window.is_critique_running = False
        self.view.qc_window.refresh_selected_item()

    def process_existing_pdfs(self):
        """
        Processes all PDFs in the dedicated folder against the current metadata.
        """
        pdf_folder = config.get("dedicated_pdf_folder")
        if not self.metadata_set:
            self.status_updated.emit("No metadata loaded, skipping PDF processing.")
            return

        if not os.path.exists(pdf_folder):
            message = f"PDF folder not found: {pdf_folder}"
            self.status_updated.emit(message)
            self.show_directory_warning(message, title="PDF Folder Not Found")
            return

        self.status_updated.emit(f"Processing PDFs in {pdf_folder}...")
        for filename in os.listdir(pdf_folder):
            if filename.lower().endswith(".pdf"):
                if re.match(r'PMID:\d+', filename):
                    # Ignoring PDF with PMID in filename
                    continue
                pdf_path = os.path.join(pdf_folder, filename)
                match = match_pdf_to_metadata(pdf_path, self.metadata_set)
                if match:
                    self._handle_successful_match(pdf_path, match)
                else:
                    logging.info(f"No match found for PDF '{filename}'")

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
        """Stops the file monitor and properly shuts down the log handler."""
        self.file_monitor.stop()
        
        # Remove the handler from the logging system
        logging.getLogger().removeHandler(self.log_handler)
        
        # Explicitly close the handler to prevent atexit issues
        self.log_handler.close()

    # Add other methods to handle application logic here
