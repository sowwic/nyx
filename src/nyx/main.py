from nyx import get_main_logger
from nyx.utils.logging_fn import get_log_file_path

LOGGER = get_main_logger()


def main():
    from nyx.application import NyxEditorApplication

    app = NyxEditorApplication()
    status_code = app.exec()
    if status_code:
        LOGGER.error(f"Application exit with code {status_code}")
    else:
        app.config().save()
    LOGGER.info(f"Log file: {get_log_file_path(LOGGER)}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOGGER.exception("Failed to start nyx application", stack_info=True)
