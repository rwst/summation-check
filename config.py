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
DEFAULT_CONFIG = {
    "downloads_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
    "project_file_path": "",
    "dedicated_pdf_folder": "",
    "file_operation": "Move",  # "Move" or "Copy"
    "GEMINI_API_KEY": ""
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
    
    # Ensure all default keys are present
    for key, value in DEFAULT_CONFIG.items():
        config_to_load.setdefault(key, value)

    return config_to_load

def save_config(config_data):
    """
    Saves the given configuration data to the config file.
    """
    config_path = get_config_path()
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
    except (IOError, OSError) as e:
        # In a real app, you'd want to log this error properly
        print(f"Error saving configuration or creating directory: {e}")

# Load the configuration at startup so it's available for other modules
config = load_config()
# Save the config on startup to ensure any new default keys or env vars are written to the file
save_config(config)
