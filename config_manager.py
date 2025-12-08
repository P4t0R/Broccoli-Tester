import json
import os

DEFAULT_CONFIG = {
    "apis": [],
    "dynamic": []
}

# CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config.json')
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')


def load_config_json():
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config_json(conf: dict):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(conf, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
