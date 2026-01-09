# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Summation Check is a PyQt5 desktop application for quality assurance of Reactome biocuration data. It automates PDF management and uses the Gemini AI API to critique summation texts against their source scientific papers.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py

# Run with debug logging
python main.py --debug
```

## Architecture

The application follows an MVC-like pattern:

- **main.py** - Entry point, initializes PyQt5 app and wires components together
- **controller.py** - Central hub coordinating UI, file monitoring, and data processing. Contains `AiCritiqueWorker` for background API calls
- **ui_view.py** - All PyQt5 UI components: `MainAppWindow`, `QCWindow` (quality control view), `CritiqueWindow` (AI results dialog)
- **config.py** - Configuration management using `platformdirs` for cross-platform config storage
- **file_monitor.py** - Watchdog-based file system monitoring for downloads folder, PDF folder, and project file changes
- **parse_project.py** - XML parsing for Reactome `.rtpj` project files. Extracts literature references, summations, pathways, and events
- **match_metadata.py** - PDF-to-metadata matching using title comparison (PDF metadata, filename, or cached content extraction)
- **prep_ai_critique.py** - Gemini API integration. Extracts PDF text with PyMuPDF and sends to `gemini-3-pro-preview` with structured output (Pydantic `CritiqueResult`)
- **logger.py** - Custom `QLogHandler` that bridges Python logging to PyQt signals for UI display

## Key Data Flow

1. User selects a Reactome project file (`.rtpj` XML format)
2. `parse_project.py` extracts literature references and event data
3. PDFs downloaded to the downloads folder are automatically moved/copied to the dedicated PDF folder
4. `match_metadata.py` matches PDFs to references by comparing titles (using difflib similarity)
5. Matched PDFs are renamed with `PMID:` prefix
6. QC window shows pathways/events with their literature references and PDF availability status
7. "Get AI Critique" sends summation text + PDF contents to Gemini for verification

## Configuration

Config stored at platform-specific location via `platformdirs.user_config_dir("SummationCheck")`. Key settings:
- `downloads_folder` - Monitored for new PDFs
- `dedicated_pdf_folder` - Where PDFs are stored/organized
- `project_file_path` - Path to `.rtpj` project file
- `GEMINI_API_KEY` - Can also be set via environment variable

## External APIs

- **Gemini API** (`google-generativeai`) - Used for AI critique with `gemini-3-pro-preview` model
