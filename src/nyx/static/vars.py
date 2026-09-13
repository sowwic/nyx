import os

APPLICATION_TITLE = "nyx"

ORGANIZATION_NAME = "sowwic"
NYX_FILE_EXTENSION = ".nyx"
NYX_FILE_FILTER = f"Nyx files (*{NYX_FILE_EXTENSION});"
DEBUG = int(os.getenv("DEBUG", 0))
