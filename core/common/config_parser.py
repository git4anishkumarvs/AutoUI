import configparser
import os

def load_config(config_path="config.ini"):
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found.")
    config.read(config_path)
    return config
