import os
import sys
import configparser

def get_base_path():
    """Returns the base path of the executable or script."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_path():
    return os.path.join(get_base_path(), 'config.ini')

def get_session_path():
    return os.path.join(get_base_path(), 'bloco_tg')

def load_config():
    """Reads config.ini."""
    config_path = get_config_path()
    config = configparser.ConfigParser()
    if os.path.exists(config_path):
        config.read(config_path)
        if 'Telegram' in config:
            return config['Telegram']
    return None

def save_config(api_id, api_hash, phone):
    """Saves credentials to config.ini."""
    config = configparser.ConfigParser()
    config['Telegram'] = {
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone
    }
    with open(get_config_path(), 'w') as f:
        config.write(f)
