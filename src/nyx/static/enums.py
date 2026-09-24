import enum


class CoreNodes(enum.StrEnum):
    EMPTY = "core:node"
    ACTION = "core:action"
    FLOW_START = "core:flow_start"
    BRANCH = "core:branch"
    SEQUENCE = "core:sequence"
    LOG = "core:log"


class CoreNodeComponents(enum.StrEnum):
    VALUE = "core:value"
    FLOW = "core:flow"
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
