import enum


class CoreNodes(enum.StrEnum):
    EMPTY = "core:node"
    ACTION = "core:action"
    FLOW_START = "core:flow_start"
    BRANCH = "core:branch"


class CoreNodeComponents(enum.StrEnum):
    VALUE = "core:value"
    FLOW = "core:flow"
