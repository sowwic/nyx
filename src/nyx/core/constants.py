import enum


class NyxFileExtensions(enum.Enum):
    NYX_STAGE_FILE = ".nyx"
    NYX_NODE_FILE = ".nyxn"


class NyxFileFilters(enum.Enum):
    NYX_STAGE_FILTER = f"Nyx Stage (*{NyxFileExtensions.NYX_NODE_FILE.value})"
    NYX_NODE_FILTER = f"Nyx Node (*{NyxFileExtensions.NYX_NODE_FILE.value})"
