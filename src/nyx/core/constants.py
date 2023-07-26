import enum


class NyxFileExtensions(enum.Enum):
    NYX_STAGE_FILE = ".nyx"
    NYX_NODE_FILE = ".nyxn"


class NyxFileFilters(enum.Enum):
    NYX_STAGE_FILTER = f"Nyx Stage (*{NyxFileExtensions.NYX_STAGE_FILE.value})"
    NYX_NODE_FILTER = f"Nyx Node (*{NyxFileExtensions.NYX_NODE_FILE.value})"
    NYX_STAGE_AND_NODES = f"Nyx file (*{NyxFileExtensions.NYX_NODE_FILE.value}, *{NyxFileExtensions.NYX_STAGE_FILE.value})"
