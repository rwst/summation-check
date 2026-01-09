# Summation Check - Project Context for Qwen Code

## Project Overview

**Summation Check** is a Python desktop application designed to assist Reactome biocurators in their quality control (QC) workflow. Reactome biocurators create detailed pathway diagrams and associated textual summaries for biological processes, which require rigorous validation against scientific literature.

The application automates the tedious process of matching downloaded PDFs to their corresponding literature references in Reactome project files, and provides AI-powered critique of the summaries using Google's Gemini API.

### Core Functionality

1. **File Monitoring**: Continuously monitors specified directories (downloads folder, dedicated PDF folder) and Reactome project files for changes
2. **PDF Matching**: Automatically matches newly downloaded PDFs to literature references in Reactome project files using metadata extraction
3. **File Organization**: Automatically renames and organizes PDFs with PMID prefixes for easy identification
4. **Quality Control**: Provides a UI for reviewing pathway events and their associated literature references
5. **AI Critique**: Uses Google's Gemini API to analyze the scientific accuracy of pathway summaries against supporting literature

### Technologies Used

- **Python 3.x**: Core programming language
- **PyQt5**: GUI framework for the desktop application
- **watchdog**: File system monitoring library
- **PyMuPDF (fitz)**: PDF text extraction
- **PyPDF2**: PDF metadata extraction
- **google-generativeai**: Gemini API integration
- **pydantic**: Data validation and serialization
- **platformdirs**: Cross-platform user directory management

## Project Architecture

The application follows a Model-View-Controller (MVC) pattern:

```
main.py              # Entry point
├── ui_view.py       # View (UI components)
├── controller.py    # Controller (business logic)
├── file_monitor.py  # File system monitoring
├── config.py        # Configuration management
├── logger.py        # Logging utilities
├── parse_project.py # Reactome project file parsing
├── match_metadata.py# PDF-to-metadata matching
└── prep_ai_critique.py # AI critique functionality
```

### Key Components

1. **Main Application (main.py)**: Initializes the application, sets up logging, and starts the Qt event loop
2. **UI View (ui_view.py)**: Contains all PyQt5 UI components including:
   - Main application window with configuration options
   - QC window for reviewing pathway events and literature
   - Critique result display dialog
3. **Controller (controller.py)**: Central coordinator that handles:
   - File operations (selecting folders and files)
   - Event handling from file monitors
   - PDF matching and renaming logic
   - AI critique workflow
4. **File Monitor (file_monitor.py)**: Uses the `watchdog` library to monitor:
   - Downloads folder for new PDFs
   - Reactome project file for changes
   - Dedicated PDF folder for content changes
5. **Configuration (config.py)**: Manages user settings using platform-specific directories
6. **PDF Processing (match_metadata.py)**: Handles PDF metadata extraction and matching against literature references
7. **Project Parsing (parse_project.py)**: Extracts pathway events and literature references from Reactome project files
8. **AI Critique (prep_ai_critique.py)**: Interfaces with Google's Gemini API to analyze summaries

## Development Setup

### Prerequisites

- Python 3.7 or higher
- Google Gemini API key (requires Google Cloud billing account)

### Installation

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python main.py [--debug]
```

The `--debug` flag enables debug-level logging in the main window.

## Configuration

The application stores user configuration in platform-specific directories:
- **Windows**: `%LOCALAPPDATA%\SummationCheck\config.json`
- **macOS**: `~/Library/Application Support/SummationCheck/config.json`
- **Linux**: `~/.local/share/SummationCheck/config.json`

Configuration options include:
- `downloads_folder`: Directory to monitor for new PDF downloads
- `project_file_path`: Path to the Reactome project file (.rtpj)
- `dedicated_pdf_folder`: Directory to store organized PDFs
- `file_operation`: Whether to "Move" or "Copy" PDFs from downloads to the dedicated folder
- `GEMINI_API_KEY`: Google Gemini API key for AI critique functionality

## Development Conventions

### Code Style

- Follow PEP 8 Python style guide
- Use descriptive variable and function names
- Include docstrings for all functions and classes
- Use type hints where appropriate

### Logging

- Use the built-in logging module for all application logging
- Include appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Log important user actions and system events
- Log errors with sufficient context for debugging

### Error Handling

- Use custom exception classes for specific error conditions
- Handle file I/O errors gracefully
- Provide user-friendly error messages in the UI
- Log detailed error information for debugging

### UI Design

- Use PyQt5 for all GUI components
- Follow platform conventions for UI design
- Provide clear status updates to the user
- Use appropriate dialog boxes for user input and warnings

## Testing

Currently, the application lacks a formal testing framework. For development:

1. Manual testing of core functionality
2. Verification of file monitoring and PDF matching
3. Testing of AI critique functionality with valid API key

## Building and Distribution

The application can be packaged as a standalone executable using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```

## Future Improvements

Based on the TODO.txt file, planned enhancements include:
1. Using Gemini to extract text from non-digitized PDFs
2. Storing AI critique results for future reference

## Common Development Tasks

### Adding a New Configuration Option

1. Add the new option to `DEFAULT_CONFIG` in `config.py`
2. Update the UI in `ui_view.py` to display and edit the option
3. Connect UI events to controller methods in `controller.py`
4. Implement the business logic in the controller

### Modifying the AI Critique Prompt

The prompt is located in `prep_ai_critique.py` in the `get_ai_critique` function. Modifications should maintain the core validation rules while potentially improving the critique quality.

### Extending File Monitoring

New file monitoring capabilities can be added by extending the `EventHandler` class in `file_monitor.py` and updating the `start` method to schedule monitoring for additional paths.