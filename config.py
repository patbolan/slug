import json
import os

class Config:
    """
    Singleton class to load and cache configuration from a JSON file.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """
        Loads the configuration from the config.json file.
        """
        config_path = os.path.join(os.path.dirname(__file__), 'local_config.json')
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        with open(config_path, 'r') as f:
            self._config = json.load(f)

    def get(self, key, default=None):
        """
        Retrieves a value from the configuration.
        :param key: The key to look up in the configuration.
        :param default: The default value to return if the key is not found.
        :return: The value from the configuration or the default value.
        """
        return self._config.get(key, default)