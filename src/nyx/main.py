import logging

from nyx.core.logger import NyxLogger
from nyx.utils.logging_fn import add_signal_handler

logging.setLoggerClass(NyxLogger)
ROOT_LOGGER = logging.getLogger()
add_signal_handler(ROOT_LOGGER)
LOGGER = logging.getLogger(__name__)


def main():
    """Run the editor application and save config on a clean exit."""
    from nyx.application import NyxEditorApplication

    app = NyxEditorApplication()
    app.session.autostart_bridge_server()
    status_code = app.exec()
    if status_code:
        LOGGER.error(f"Application exit with code {status_code}")
    else:
        app.config.save()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOGGER.exception("Failed to start nyx application", stack_info=True)
