from .vars import APPLICATION_TITLE, ORGANIZATION_NAME
import platformdirs


APP_DATA_DIR = platformdirs.user_data_path(
    appname=APPLICATION_TITLE,
    appauthor=ORGANIZATION_NAME,
    roaming=False,
    ensure_exists=True,
)
CONFIG_FILE_PATH = APP_DATA_DIR / "config.json"
USER_CONFIG_FILE_PATH = APP_DATA_DIR / "user_config.json"
LOGS_DIRECTORY = APP_DATA_DIR / "logs"
PROFILING_DIR = APP_DATA_DIR / "profiling"
