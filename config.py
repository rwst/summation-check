# config.py
"""
Manages user-configurable settings for the application.

This module handles loading and saving application settings, such as
monitored file paths and other user preferences.
"""

import json
import os

# Define the name of the config file
CONFIG_FILE = "config.json"

# Define the default structure of the configuration
DEFAULT_CONFIG = {
    "downloads_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
    "summary_file_path": os.path.join(os.getcwd(), "summary.txt"),
    "some_other_setting": "default_value"
}

def load_config():
    """
    Loads the application configuration from the config file.
    If the file doesn't exist, it creates a default one.
    """
    if not os.path.exists(CONFIG_FILE):
        print(f"Configuration file not found. Creating a default '{CONFIG_FILE}'.")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading configuration: {e}. Loading default config.")
        # In a real app, you might want to notify the user more formally
        return DEFAULT_CONFIG

def save_config(config_data):
    """
    Saves the given configuration data to the config file.
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        # In a real app, you'd want to log this error properly
        print(f"Error saving configuration: {e}")

# Load the configuration at startup so it's available for other modules
config = load_config()
