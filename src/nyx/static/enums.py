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


class PluginContentKind(enum.StrEnum):
    PLUGIN = "plugin"
    NODE = "node"
    NODE_COMPONENT = "node_component"
