# config.py
"""
Manages user-configurable settings for the application.

This module handles loading and saving application settings, such as
monitored file paths and other user preferences.
"""

import json
import os
import sys
from platformdirs import user_config_dir

# Define the name of the config file
APP_NAME = "SummationCheck"
CONFIG_FILE = "config.json"

def get_config_path():
    """
    Gets the cross-platform configuration file path.
    """
    return os.path.join(user_config_dir(APP_NAME, roaming=True), CONFIG_FILE)

def is_frozen():
    """
    Checks if the application is running as a PyInstaller executable.
    """
    return getattr(sys, 'frozen', False)

def get_resource_path(relative_path):
    """
    Gets the path to bundled resources in frozen or unfrozen state.
    """
    if is_frozen():
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

# Define the default structure of the configuration
DEFAULT_CRITIQUE_PROMPT = """You are given the concatenated text of one or more scientific articles, and in a second file a short text file with statements, backed up by references. First, check if all references in the short text also correspond to their full text as part of the papers file. Use the delimiter ---END OF PAPER--- to split papers.txt into individual papers. Then, for every part of the short text that ends with references, check: 1. all statements must be directly supported by experimental evidence in experimental papers or statements in review papers; 2. all statements must not misrepresent or exaggerate findings from the article(s); 3. If quantitative data (numbers, percentages, p-values) is mentioned, it must match the article(s) precisely. 4. all statements must not introduce information or conclusions not present in the cited article(s). 5. assuming the short text describes a chemical reaction or process, either the papers don't mention any results about regulators of the reaction/process, or the regulators are mentioned explicitly in the statements. 6. either all results were obtained using human cell lines, or the cell lines used, with their species, are mentioned explicitly in the statements. After judging all statements with references, write out your critique and, if some rules were broken, an improved short text that only changes those statements that you criticized."""

DEFAULT_CONFIG = {
    "downloads_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
    "project_file_path": "",
    "dedicated_pdf_folder": "",
    "file_operation": "Move",  # "Move" or "Copy"
    "GEMINI_API_KEY": "",
    "critique_model": "gemini-2.5-pro",
    "critique_prompt": DEFAULT_CRITIQUE_PROMPT,
    "ncbi_email": "",       # Optional: improves rate limits
    "ncbi_api_key": ""      # Optional: enables 10 req/sec (vs 3 req/sec)
}

def load_config():
    """
    Loads the application configuration from the config file.
    If the file doesn't exist, it creates a default one.
    It also checks for the GEMINI_API_KEY from environment variables if not set in the file.
    """
    config_path = get_config_path()
    config_to_load = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_from_file = json.load(f)
                config_to_load.update(config_from_file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading configuration: {e}. Using default config.")
    else:
        print(f"Configuration file not found. Creating a default at '{config_path}'.")

    # Check for GEMINI_API_KEY from environment variable if not in config
    if not config_to_load.get("GEMINI_API_KEY"):
        env_api_key = os.environ.get("GEMINI_API_KEY")
        if env_api_key:
            config_to_load["GEMINI_API_KEY"] = env_api_key
            print("Loaded GEMINI_API_KEY from environment variable.")

    # Check for NCBI_API_KEY from environment variable if not in config
    if not config_to_load.get("ncbi_api_key"):
        env_ncbi_key = os.environ.get("NCBI_API_KEY")
        if env_ncbi_key:
            config_to_load["ncbi_api_key"] = env_ncbi_key
            print("Loaded NCBI_API_KEY from environment variable.")

    # Ensure all default keys are present
    for key, value in DEFAULT_CONFIG.items():
        config_to_load.setdefault(key, value)

    return config_to_load

def save_config(config_data):
    """
    Saves the given configuration data to the config file.
    Returns True on success, False on failure.
    """
    config_path = get_config_path()
    try:
        config_dir = os.path.dirname(config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        if not os.access(config_dir, os.W_OK):
            print(f"Error: Configuration directory is not writable: {config_dir}")
            return False

        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    except (IOError, OSError) as e:
        print(f"Error saving configuration: {e}")
        return False

# Load the configuration at startup so it's available for other modules
config = load_config()

