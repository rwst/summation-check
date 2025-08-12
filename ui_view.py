# ui_view.py
"""
The User Interface (UI) module for the Summation Check application.

This module contains all components related to the graphical user interface,
built with PyQt5.
"""

import sys
import os
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QStatusBar, QSplitter,
    QSizePolicy, QRadioButton, QButtonGroup, QMessageBox, QListWidget, QListWidgetItem,
    QDialog, QFileDialog, QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from config import config, save_config
from parse_project import extract_event_data

class ActionPopup(QDialog):
    def __init__(self, pmid, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Action for PMID: {pmid}")
        self.pmid = pmid

        layout = QVBoxLayout(self)
        
        self.label = QLabel(f"What would you like to do with PMID: {pmid}?")
        layout.addWidget(self.label)

        self.btn_open_browser = QPushButton("Open PMID in browser")
        self.btn_open_and_associate = QPushButton("Open PMID in browser and associate next PDF with PMID")
        self.btn_select_pdf = QPushButton("Select PDF to associate with PMID")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_open_and_associate.setEnabled(True)
        self.btn_select_pdf.setEnabled(True)

        layout.addWidget(self.btn_open_browser)
        layout.addWidget(self.btn_open_and_associate)
        layout.addWidget(self.btn_select_pdf)
        layout.addWidget(self.btn_cancel)

        self.btn_open_browser.clicked.connect(lambda: self.done(1))
        self.btn_open_and_associate.clicked.connect(lambda: self.done(2))
        self.btn_select_pdf.clicked.connect(lambda: self.done(3))
        self.btn_cancel.clicked.connect(self.reject)

class WordWrapButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__("", parent)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.setMinimumHeight(40)

    def setText(self, text):
        self.label.setText(text)
        self.setToolTip(text)

    def text(self):
        return self.label.text()

    def sizeHint(self):
        hint = self.label.sizeHint()
        return hint


class QCWindow(QWidget):
    """
    A window for quality control, showing two lists side-by-side.
    """
    pmid_hint_set = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QC View")
        self.setGeometry(150, 150, 800, 600)
        self.project_data = []

        layout = QHBoxLayout(self)
        
        self.list1 = QListWidget()
        self.list2 = QListWidget()
        self.list1.itemClicked.connect(self.on_left_list_item_clicked)
        self.list2.itemClicked.connect(self.on_right_list_item_clicked)

        # Set the maximum height of the second list to approximately 15 items
        font_height = self.list2.fontMetrics().height()
        self.list2.setMaximumHeight(font_height * 15 + 2 * self.list2.frameWidth())

        # Use a layout to align the second list to the top
        right_list_layout = QVBoxLayout()
        right_list_layout.addWidget(self.list2)
        
        self.ai_critique_button = QPushButton("Get AI Critique")
        self.ai_critique_button.setEnabled(False)
        right_list_layout.addWidget(self.ai_critique_button)
        
        right_list_layout.addStretch()

        layout.addWidget(self.list1)
        layout.addLayout(right_list_layout)

    def on_right_list_item_clicked(self, item):
        """
        Handles clicks on the right list to show a popup with options.
        """
        item_text = item.text()
        parts = item_text.split()

        # The PMID should be the second part of the string, e.g., "✓ 12345678 ..."
        if len(parts) > 1 and parts[1].isdigit():
            pmid = parts[1]
            
            popup = ActionPopup(pmid, self)
            result = popup.exec_()

            if result == 1: # Open PMID in browser
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
                webbrowser.open(url)
            elif result == 2:
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
                webbrowser.open(url)
                self.pmid_hint_set.emit(pmid)
            elif result == 3:
                pdf_folder = config.get("dedicated_pdf_folder", "")
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select PDF to Associate",
                    pdf_folder,
                    "PDF Files (*.pdf)"
                )
                if file_path:
                    try:
                        directory = os.path.dirname(file_path)
                        original_filename = os.path.basename(file_path)
                        new_filename = f"PMID:{pmid}-{original_filename}"
                        new_filepath = os.path.join(directory, new_filename)
                        
                        os.rename(file_path, new_filepath)
                        
                        # Refresh the view to show the change
                        self.refresh_selected_item()
                    except OSError as e:
                        error_dialog = QMessageBox()
                        error_dialog.setIcon(QMessageBox.Critical)
                        error_dialog.setText("Error Renaming File")
                        error_dialog.setInformativeText(f"Could not rename the file.\n\nDetails: {e}")
                        error_dialog.setWindowTitle("Error")
                        error_dialog.exec_()
    def update_data(self, project_data):
        """
        Populates the left list with project data and stores it.
        """
        self.project_data = project_data
        self.list1.clear()
        self.list2.clear()
        
        for item_data in self.project_data:
            name = item_data.get('name', 'Unnamed')
            db_id = item_data.get('DB_ID')
            list_item = QListWidgetItem(name)
            list_item.setData(Qt.UserRole, db_id) # Store DB_ID
            self.list1.addItem(list_item)

    def on_left_list_item_clicked(self, item):
        """
        Handles clicks on the left list to populate the right list.
        """
        clicked_item_db_id = item.data(Qt.UserRole)
        if clicked_item_db_id is None:
            return

        self.list2.clear()
        self.ai_critique_button.setEnabled(False) # Disable by default

        pdf_folder = config.get("dedicated_pdf_folder")
        if not pdf_folder or not os.path.isdir(pdf_folder):
            self.list2.addItem("PDF folder not set or not found.")
            return

        all_files_found = True
        for data_item in self.project_data:
            if data_item.get('DB_ID') == clicked_item_db_id:
                literature_references = data_item.get('literature_references', [])
                if not literature_references:
                    self.list2.addItem("No literature references found.")
                    all_files_found = False
                    break

                for ref in literature_references:
                    pmid = ref[0] if len(ref) > 0 else None
                    title = ref[1] if len(ref) > 1 else 'No Title'

                    if not pmid:
                        self.list2.addItem(f"❌ (No PMID) {title}")
                        all_files_found = False
                        continue

                    file_exists = False
                    for filename in os.listdir(pdf_folder):
                        if filename.startswith(f"PMID:{pmid}"):
                            file_exists = True
                            break
                    
                    if not file_exists:
                        all_files_found = False

                    check_mark = "✓" if file_exists else "❌"
                    self.list2.addItem(f"{check_mark} {pmid} {title}")
                
                # After checking all references for the selected item
                if literature_references: # Only enable if there are references
                    self.ai_critique_button.setEnabled(all_files_found)
                break

    def refresh_selected_item(self):
        """
        Refreshes the right list based on the currently selected item in the left list.
        """
        selected_items = self.list1.selectedItems()
        if selected_items:
            self.on_left_list_item_clicked(selected_items[0])


class MainAppWindow(QMainWindow):
    """
    The main application window.
    """
    def __init__(self):
        super().__init__()
        self.controller = None
        self.setWindowTitle("Summation Check Tool")
        self.setGeometry(100, 100, 1000, 700)  # Increased size for split view

        self.qc_window = None # To hold a reference to the QC window

        # --- Main Layout ---
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- Splitter ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)

        # --- Left Panel ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setAlignment(Qt.AlignTop)
        self.left_panel.setMinimumWidth(200)
        self.left_panel.setMaximumWidth(400)

        # --- Right Panel ---
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)

        # Add panels to splitter
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([300, 700]) # Initial size ratio

        # --- UI Elements (Left Panel) ---
        # Downloads Folder
        self.downloads_label = QLabel("downloads_folder")
        self.downloads_button = WordWrapButton(config.get("downloads_folder", "Not Set"))
        self.downloads_button.setToolTip(config.get("downloads_folder", "Not Set"))

        # File Operation Radio Buttons
        self.file_op_label = QLabel("File Operation:")
        self.file_op_group = QButtonGroup(self)
        self.copy_radio = QRadioButton("Copy")
        self.move_radio = QRadioButton("Move")
        self.file_op_group.addButton(self.copy_radio)
        self.file_op_group.addButton(self.move_radio)

        if config.get("file_operation") == "Copy":
            self.copy_radio.setChecked(True)
        else:
            self.move_radio.setChecked(True)

        self.file_op_group.buttonClicked.connect(self.on_file_op_changed)

        # Dedicated PDF Folder
        self.pdf_folder_label = QLabel("dedicated_pdf_folder")
        self.pdf_folder_button = WordWrapButton(config.get("dedicated_pdf_folder", "Not Set"))
        self.pdf_folder_button.setToolTip(config.get("dedicated_pdf_folder", "Not Set"))

        # Project File
        self.project_file_label = QLabel("project_file")
        self.project_file_button = WordWrapButton(config.get("project_file_path", "Not Set"))
        self.project_file_button.setToolTip(config.get("project_file_path", "Not Set"))

        # Gemini API Key
        self.gemini_api_key_label = QLabel("GEMINI_API_KEY")
        self.gemini_api_key_button = WordWrapButton(config.get("GEMINI_API_KEY", "Not Set"))
        self.gemini_api_key_button.setToolTip(config.get("GEMINI_API_KEY", "Not Set"))
        self.gemini_api_key_button.clicked.connect(self.on_gemini_api_key_clicked)

        # --- UI Elements (Right Panel) ---
        self.status_label = QLabel("Status Log:")
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.start_qc_button = QPushButton("Open QC window")
        self.start_qc_button.setFixedHeight(40)
        self.start_qc_button.clicked.connect(self.open_qc_window)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # --- Layout Management (Left) ---
        self.left_layout.addWidget(self.downloads_label)
        self.left_layout.addWidget(self.downloads_button)
        self.left_layout.addSpacing(20)

        # File Operation Layout
        file_op_layout = QHBoxLayout()
        file_op_layout.addWidget(self.copy_radio)
        file_op_layout.addWidget(self.move_radio)
        self.left_layout.addWidget(self.file_op_label)
        self.left_layout.addLayout(file_op_layout)
        self.left_layout.addSpacing(20)

        self.left_layout.addWidget(self.pdf_folder_label)
        self.left_layout.addWidget(self.pdf_folder_button)
        self.left_layout.addSpacing(20)
        self.left_layout.addWidget(self.project_file_label)
        self.left_layout.addWidget(self.project_file_button)
        self.left_layout.addSpacing(20)
        self.left_layout.addWidget(self.gemini_api_key_label)
        self.left_layout.addWidget(self.gemini_api_key_button)

        # --- Layout Management (Right) ---
        self.right_layout.addWidget(self.status_label)
        self.right_layout.addWidget(self.status_display)
        self.right_layout.addWidget(self.start_qc_button)

    def set_controller(self, controller):
        self.controller = controller

    def open_qc_window(self):
        """
        Opens the QC window and populates it with data from the project file.
        """
        project_file_path = config.get("project_file_path")
        if not project_file_path or not project_file_path.strip():
            self.show_warning_message("Project File Error", "Project file path is not set.")
            return

        try:
            with open(project_file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except FileNotFoundError:
            self.show_warning_message("Project File Error", f"Project file not found at: {project_file_path}")
            return
        except Exception as e:
            self.show_warning_message("File Read Error", f"Could not read project file: {e}")
            return

        event_data = extract_event_data(xml_content)

        if not event_data:
            self.show_warning_message("Data Extraction Error", "No data could be extracted from the project file.")
            return

        if self.qc_window is None:
            self.qc_window = QCWindow()
            if self.controller:
                self.qc_window.pmid_hint_set.connect(self.controller.set_pmid_hint)

        project_file_name = os.path.basename(project_file_path)
        self.qc_window.setWindowTitle(f"QC: {project_file_name}")

        # Sort the data alphabetically by name (case-insensitive)
        sorted_project_data = sorted(event_data, key=lambda x: x.get('name', 'Unnamed').lower())
        
        self.qc_window.update_data(sorted_project_data)

        self.qc_window.show()
        self.update_status_display(f"QC Window opened. Loaded {len(event_data)} items.")

    def closeEvent(self, event):
        """Ensures the QC window is closed when the main window is closed."""
        if self.qc_window:
            self.qc_window.close()
        super().closeEvent(event)

    def show_warning_message(self, title, message):
        """Displays a warning message box."""
        QMessageBox.warning(self, title, message)

    def on_gemini_api_key_clicked(self):
        """Handles clicking the GEMINI_API_KEY button."""
        current_key = config.get("GEMINI_API_KEY", "")
        new_key, ok = QInputDialog.getText(self, "Set Gemini API Key",
                                           "Enter your Gemini API Key:",
                                           QLineEdit.Normal,
                                           current_key)
        if ok and new_key != current_key:
            config["GEMINI_API_KEY"] = new_key
            save_config(config)
            self.gemini_api_key_button.setText(new_key)
            self.gemini_api_key_button.setToolTip(new_key)
            self.update_status_display("GEMINI_API_KEY updated.")

    def on_file_op_changed(self, button):
        """Handles the change in file operation radio buttons."""
        config["file_operation"] = button.text()
        save_config(config)
        self.update_status_display(f"File operation set to {button.text()}")

    def update_status_display(self, message):
        """Updates the status bar and the main status log display."""
        self.status_bar.showMessage(message)
        self.status_display.append(message)
        # Automatically scroll to the bottom
        self.status_display.verticalScrollBar().setValue(self.status_display.verticalScrollBar().maximum())

    def prompt_for_pmid(self):
        """
        Creates a dialog to prompt the user for a PMID.
        (This is a placeholder for a more complex dialog)
        """
        # In a real app, this would be a QInputDialog or a custom QDialog.
        print("UI: Prompting for PMID...")
        # This would need to return the entered value.
        pass

if __name__ == '__main__':
    # Example of how to run the UI directly for testing
    app = QApplication(sys.argv)
    main_window = MainAppWindow()
    main_window.show()
    sys.exit(app.exec_())
