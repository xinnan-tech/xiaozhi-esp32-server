import os
from config.config_loader import read_config, get_project_dir, load_config


default_config_file = "config.yaml"
config_file_valid = False


def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    """
    Simplified configuration check, only prompting the use of user configuration files
    """
    custom_config_file = get_project_dir() + "data/." + default_config_file
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError(
            "Cannot find the data/.config.yaml file. Please follow the tutorial to confirm whether the configuration file exists."
        )

    # Check if configuration is read from API
    config = load_config()
    if config.get("read_config_from_api", False):
        print("Read configuration from API")
        old_config_origin = read_config(custom_config_file)
        if old_config_origin.get("selected_module") is not None:
            error_msg = "Your configuration file seems to contain both the console configuration and the local configuration:\n"
            error_msg += "\nSuggestions:\n"
            error_msg += "1. Copy the config_from_api.yaml file in the root directory to data and rename it to .config.yaml\n"
            error_msg += "2. Configure the interface address and key according to the tutorial\n"
            raise ValueError(error_msg)
    config_file_valid = True