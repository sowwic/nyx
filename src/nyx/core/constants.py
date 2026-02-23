import os
import platformdirs


APPLICATION_TITLE = "nyx"
ORGANIZATION_NAME = "sowwic"
NYX_FILE_EXTENSION = ".nyx"
NYX_FILE_FILTER = f"Nyx files (*{NYX_FILE_EXTENSION});"
DEBUG = int(os.getenv("DEBUG", 0))


APP_DATA_DIR = platformdirs.user_data_path(
    appname=APPLICATION_TITLE,
    appauthor=ORGANIZATION_NAME,
    roaming=False,
    ensure_exists=True,
)
CONFIG_FILE_PATH = APP_DATA_DIR / "config.json"
LOGS_DIRECTORY = APP_DATA_DIR / "logs"
