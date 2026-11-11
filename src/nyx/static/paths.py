import os
import pathlib
import sys
import platformdirs
from nyx_bridge.protocol import DEFAULT_ADDRESS_FILE_NAME

from .vars import APPLICATION_TITLE, ORGANIZATION_NAME


def _get_app_data_dir() -> pathlib.Path:
    """Get the directory for user files of the application.

    Returns:
        pathlib.Path: `$XDG_CONFIG_HOME/<app>` (`~/.config/<app>` by default) on Linux
            and macOS, the platform data directory on other systems. Created if missing.
    """
    if sys.platform == "win32":
        return platformdirs.user_data_path(
            appname=APPLICATION_TITLE,
            appauthor=ORGANIZATION_NAME,
            roaming=False,
            ensure_exists=True,
        )
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = pathlib.Path(config_home) if config_home else pathlib.Path.home() / ".config"
    app_dir = base / APPLICATION_TITLE
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DATA_DIR = _get_app_data_dir()
USER_CONFIG_FILE_PATH = APP_DATA_DIR / "user_config.json"
LAST_SESSION_FILE_PATH = APP_DATA_DIR / "session.nyxsession"
BRIDGE_ADDRESS_FILE_PATH = APP_DATA_DIR / DEFAULT_ADDRESS_FILE_NAME
LOGS_DIRECTORY = APP_DATA_DIR / "logs"
PROFILING_DIR = APP_DATA_DIR / "profiling"

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
QML_DIR = PACKAGE_ROOT / "editor" / "qml"
DEFAULT_QML_NODE_COMPONENT_ITEM = QML_DIR / "components_view" / "NodeComponentItem.qml"
