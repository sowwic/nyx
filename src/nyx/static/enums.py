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


class NodeComponentSolveDirection(enum.IntEnum):
    BACKWARD = enum.auto()
    FORWARD = enum.auto()


class RestoreUuidOption(enum.IntEnum):
    GENERATE_NEW = enum.auto()
    RESTORE = enum.auto()
    ATTEMPT_RESTORE = enum.auto()


class NodeExecutionStatus(enum.IntEnum):
    SUCCESS = enum.auto()
    ERROR = enum.auto()
    PENDING = enum.auto()
    NOT_RAN = enum.auto()


class NodeComponentFlag(enum.IntFlag):
    NONE = 0
    BUILT_IN = enum.auto()
    ACCEPTS_INPUTS = enum.auto()
    PRODUCES_OUTPUT = enum.auto()
    EDITABLE = enum.auto()
