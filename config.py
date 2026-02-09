"""VoxMind Configuration - Stores user preferences."""
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voxmind_config.json')

DEFAULT_CONFIG = {
    'user_name': None,
    'wake_word': 'vox',
    'voice_speed': 180,
    'voice_volume': 0.9,
    'first_run': True
}

def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Could not save config: {e}")
        return False

def get_user_name():
    """Get the user's name from config."""
    config = load_config()
    return config.get('user_name')

def set_user_name(name):
    """Set the user's name in config."""
    config = load_config()
    config['user_name'] = name
    config['first_run'] = False
    save_config(config)

def is_first_run():
    """Check if this is the first run."""
    config = load_config()
    return config.get('first_run', True) or config.get('user_name') is None

def reset_config():
    """Reset configuration to defaults."""
    save_config(DEFAULT_CONFIG.copy())
