import json
import os

CONFIG_FILENAME = "autoclicker_config.json"


def get_config_path(base_dir=None):
    if base_dir:
        return os.path.join(base_dir, CONFIG_FILENAME)
    return CONFIG_FILENAME


def read_config():
    path = get_config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except Exception as exc:
        print(f"Failed to load config: {exc}")
        return {}


def write_config(config):
    try:
        with open(get_config_path(), "w") as handle:
            json.dump(config, handle)
    except Exception as exc:
        print(f"Failed to save config: {exc}")
