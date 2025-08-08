import json
import os

class Config:
    """
    Singleton class to load and cache configuration from a JSON file.
    This class allows for shared parameters across all instances, which can be set and retrieved.
    It loads the configuration from a file named 'local_config.json' located in the same directory as this script.
    You an also set global params explicitly like this:
        Config.set_param('MODE', args.mode)
    Note that this will override any value in the config file.
    """
    _instance = None
    _shared_params = {}  # Class-level dictionary to store shared parameters

    def __new__(cls, **kwargs):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        # Update shared parameters with any new ones passed during instantiation
        cls._shared_params.update(kwargs)
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
        Retrieves a value from the configuration or shared parameters.
        :param key: The key to look up in the configuration or shared parameters.
        :param default: The default value to return if the key is not found.
        :return: The value from the configuration or shared parameters, or the default value.
        """
        # Check shared parameters first, then the loaded config
        return self._shared_params.get(key, self._config.get(key, default))

    @classmethod
    def set_param(cls, key, value):
        """
        Sets a shared parameter for all instances of the Config class.
        :param key: The key to set.
        :param value: The value to set.
        """
        cls._shared_params[key] = value

    @classmethod
    def get_param(cls, key, default=None):
        """
        Retrieves a shared parameter for all instances of the Config class.
        :param key: The key to look up.
        :param default: The default value to return if the key is not found.
        :return: The value of the shared parameter or the default value.
        """
        return cls._shared_params.get(key, default)