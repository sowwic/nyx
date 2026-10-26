import os
import pathlib

APPLICATION_TITLE = "nyx"

ORGANIZATION_NAME = "sowwic"
NYX_FILE_EXTENSION = ".nyx"
NYX_FILE_FILTER = f"Nyx files (*{NYX_FILE_EXTENSION});;All Files (*)"
DEBUG = int(os.getenv("NYX_DEBUG", 0))
PROFILING = int(os.environ.get("NYX_PROFILING", 0))
ROOT_NODE_PATH = pathlib.PurePosixPath("/stage")
DEFAULT_UNDO_LIMIT = 100
DEFAULT_NOTE_COLOR = "#e8c95a"
DEFAULT_GROUP_COLOR = "#5b8def"
"""int: commands a stage remembers by default. A group of commands counts as one."""
NODE_TYPE_MIME = "application/nyx-node-type"
