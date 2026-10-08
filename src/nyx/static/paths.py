import pathlib
import platformdirs

from .vars import APPLICATION_TITLE, ORGANIZATION_NAME


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

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]
QML_DIR = PACKAGE_ROOT / "editor" / "qml"
DEFAULT_QML_NODE_COMPONENT_ITEM = QML_DIR / "components_view" / "NodeComponentItem.qml"
