import os
import pathlib

APPLICATION_TITLE = "nyx"

ORGANIZATION_NAME = "sowwic"
NYX_FILE_EXTENSION = ".nyx"
NYX_FILE_FILTER = f"Nyx files (*{NYX_FILE_EXTENSION});;All Files (*)"
DEBUG = int(os.getenv("NYX_DEBUG", 0))
PROFILING = int(os.environ.get("NYX_PROFILING", 0))
ROOT_NODE_PATH = pathlib.PurePosixPath("/stage")
NODE_TYPE_MIME = "application/nyx-node-type"
