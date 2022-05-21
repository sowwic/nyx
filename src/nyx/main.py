from nyx import get_main_logger
from nyx.application import NyxEditorApplication

LOGGER = get_main_logger()


def main():
    app = NyxEditorApplication()
    status_code = app.exec_()
    if status_code:
        LOGGER.error(f"Application exit with code {status_code}")
    else:
        app.config().save()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        LOGGER.exception(err)
