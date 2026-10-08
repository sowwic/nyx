import enum


class CoreNodes(enum.StrEnum):
    EMPTY = "core:node"
    GET = "core:get"
    SET = "core:set"
    ACTION = "core:action"
    FLOW_START = "core:flow_start"
    BRANCH = "core:branch"
    SEQUENCE = "core:sequence"
    LOG = "core:log"


class CoreNodeComponents(enum.StrEnum):
    VALUE = "core:value"
    FLOW = "core:flow"
    COMMENT = "core:comment"
    SCRIPT = "core:script"


class RestoreUuidOption(enum.IntEnum):
    GENERATE_NEW = enum.auto()
    RESTORE = enum.auto()
    ATTEMPT_RESTORE = enum.auto()


class NodeExecutionStatus(enum.IntEnum):
    SUCCESS = enum.auto()
    ERROR = enum.auto()
    PENDING = enum.auto()
    NOT_RAN = enum.auto()


class NodeExecutionOrderFlag(enum.IntFlag):
    BEFORE_CHILDREN = enum.auto()
    AFTER_CHILDREN = enum.auto()


class NodeComponentFlag(enum.IntFlag):
    NONE = 0
    BUILT_IN = enum.auto()
    ACCEPTS_INPUTS = enum.auto()
    PRODUCES_OUTPUT = enum.auto()
    EDITABLE = enum.auto()
    STATIC = enum.auto()


class ItemSelectionMode(enum.IntEnum):
    REPLACE = 0
    TOGGLE = enum.auto()
    RANGE = enum.auto()


class EditorUIObject(enum.StrEnum):
    NODES_PALETTE_DOCK = "nodes_palette_dock"
    STAGE_TREE_DOCK = "stage_tree_dock"
    UNDO_HISTORY_DOCK = "undo_history_dock"
    LOG_OUTPUT_DOCK = "log_output_dock"
    TOOLBAR_DOCK = "toolbar_dock"
    INSPECTOR_DOCK = "inspector_dock"
