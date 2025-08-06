# ui_view.py
"""
The User Interface (UI) module for the Summation Check application.

This module contains all components related to the graphical user interface,
built with PyQt5.
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QStatusBar, QSplitter, QFrame,
    QSizePolicy, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt
from config import config, save_config

class WordWrapButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__("", parent)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setMinimumHeight(40)

    def setText(self, text):
        self.label.setText(text)
        self.setToolTip(text)

    def text(self):
        return self.label.text()

    def sizeHint(self):
        hint = self.label.sizeHint()
        return hint


class MainAppWindow(QMainWindow):
    """
    The main application window.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Summation Check Tool")
        self.setGeometry(100, 100, 1000, 700)  # Increased size for split view

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

        # --- UI Elements (Right Panel) ---
        self.status_label = QLabel("Status Log:")
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.start_qc_button = QPushButton("Start QC")
        self.start_qc_button.setFixedHeight(40)

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

        # --- Layout Management (Right) ---
        self.right_layout.addWidget(self.status_label)
        self.right_layout.addWidget(self.status_display)
        self.right_layout.addWidget(self.start_qc_button)

    def on_file_op_changed(self, button):
        """Handles the change in file operation radio buttons."""
        config["file_operation"] = button.text()
        save_config(config)
        self.update_status_display(f"File operation set to {button.text()}")

    def update_status_display(self, message):
        """Updates the status bar and the main status log display."""
        self.status_bar.showMessage(message)
        self.status_display.append(message)

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
