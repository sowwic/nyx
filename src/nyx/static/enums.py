import enum


class CoreNodes(enum.StrEnum):
    """Type ids of the nodes provided by the core plugin."""

    EMPTY = "core:node"
    GET = "core:get"
    SET = "core:set"
    VALUE = "core:value"
    ACTION = "core:action"
    FLOW_START = "core:flow_start"
    BRANCH = "core:branch"
    SEQUENCE = "core:sequence"
    FOR_LOOP = "core:for_loop"
    FOR_EACH_LOOP = "core:for_each_loop"
    WHILE_LOOP = "core:while_loop"
    LOG = "core:log"
    TYPE_CAST = "core:type_cast"
    GET_TYPE = "core:get_type"
    REFERENCE = "core:reference"
    REMOTE_CLIENT = "core:remote_client"
    REMOTE_ACTION = "core:remote_action"


class CoreUtilObjects(enum.StrEnum):
    """Type ids of the util objects provided by the core plugin."""

    NOTE = "core:note"
    GROUP = "core:group"


class CoreGraphicsObjects(enum.StrEnum):
    """Ids of the graphics objects provided by the editor.

    Types return them from `get_graphics_object_id`.
    """

    NODE = "core.node"
    PLUG = "core.plug"
    LINK = "core.link"
    NOTE = "core.note"
    GROUP = "core.group"


class LinkAnimationStyle(enum.StrEnum):
    """Animations a graphics link can be highlighted with."""

    PULSE = "pulse"
    GLOW = "glow"


class LinkStyle(enum.StrEnum):
    """Shapes a graphics link can be drawn with."""

    BEZIER = "bezier"
    DIRECT = "direct"
    SQUARE = "square"


class StageBackGroundStyle(enum.StrEnum):
    """Patterns the graphics stage background can be drawn with."""

    GRID = "grid"
    DOTS = "dots"


class CoreNodeComponents(enum.StrEnum):
    """Type ids of the node components provided by the core plugin."""

    VALUE = "core:value"
    FLOW = "core:flow"
    COMMENT = "core:comment"
    SCRIPT = "core:script"
    REMOTE_SCRIPT = "core:remote_script"
    FILE = "core:file"
    STAGE_OBJECT_PATH = "core:stage_object_path"


class CoreDatatypes(enum.StrEnum):
    """Type ids of the datatypes provided by the core plugin."""

    OBJECT = "core:object"
    TYPE = "core:type"
    BOOL = "core:bool"
    STRING = "core:string"
    INT = "core:int"
    FLOAT = "core:float"
    PATH = "core:path"
    LIST = "core:list"
    DICT = "core:dict"
    FLOW = "core:flow"
    STAGE_OBJECT_PATH = "core:stage_object_path"


class RestoreUuidOption(enum.IntEnum):
    """How uuids stored in serialized data are used when deserializing.

    Attributes:
        GENERATE_NEW: always generate a new uuid
        RESTORE: always reuse the serialized uuid
        ATTEMPT_RESTORE: reuse the serialized uuid unless it is already taken
    """

    GENERATE_NEW = enum.auto()
    RESTORE = enum.auto()
    ATTEMPT_RESTORE = enum.auto()


class NodeExecutionStatus(enum.IntEnum):
    """Outcome of the last node execution."""

    SUCCESS = enum.auto()
    ERROR = enum.auto()
    PENDING = enum.auto()
    NOT_RAN = enum.auto()


class NodeFlag(enum.IntFlag):
    """Flags describing what the nodes of a type allow.

    Attributes:
        LOCKS_CHILDREN: the nodes inside can't be changed or linked to from the
            outside, like the ones a reference node loads from its source
        LOCKS_STRUCTURE: components can't be added, removed, renamed or given
            another datatype
    """

    NONE = 0
    LOCKS_CHILDREN = enum.auto()
    LOCKS_STRUCTURE = enum.auto()


class NodeExecutionOrderFlag(enum.IntFlag):
    """When a node executes relative to its children."""

    BEFORE_CHILDREN = enum.auto()
    AFTER_CHILDREN = enum.auto()


class NodeComponentFlag(enum.IntFlag):
    """Flags describing what a node component can do.

    Attributes:
        BUILT_IN: created by the node type, can't be removed
        WRITABLE: accepts input links
        READABLE: produces output links
        EDITABLE: value can be edited in the UI
        STATIC: skipped during execution
        SINGLE_OUTPUT: can be the source of one link at most
        INHERITS_DATATYPE: datatype follows the component it takes its value from,
            and can be changed by the user while there is none
    """

    NONE = 0
    BUILT_IN = enum.auto()
    WRITABLE = enum.auto()
    READABLE = enum.auto()
    EDITABLE = enum.auto()
    STATIC = enum.auto()
    SINGLE_OUTPUT = enum.auto()
    INHERITS_DATATYPE = enum.auto()


class NodeComponentValueMask(enum.IntEnum):
    """Selects which value of a component is read.

    Attributes:
        RAW: value as set
        CACHE: evaluated value
        DISPLAY: text shown in the UI
    """

    RAW = 0
    CACHE = enum.auto()
    DISPLAY = enum.auto()


class NoteFormat(enum.StrEnum):
    """How the text of a note is written, and so how it is rendered.

    Attributes:
        PLAIN: text as it is
        MARKDOWN: Markdown, as understood by Qt (CommonMark with GitHub extensions)
        HTML: the subset of HTML that Qt rich text supports
    """

    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"


class ItemSelectionMode(enum.IntEnum):
    """How a clicked item changes the selection.

    Attributes:
        REPLACE: select only the clicked item
        TOGGLE: toggle the clicked item
        RANGE: select from the anchor to the clicked item
    """

    REPLACE = 0
    TOGGLE = enum.auto()
    RANGE = enum.auto()


class EditorUIObject(enum.StrEnum):
    """Object names of the editor docks."""

    NODES_PALETTE_DOCK = "nodes_palette_dock"
    STAGE_TREE_DOCK = "stage_tree_dock"
    UNDO_HISTORY_DOCK = "undo_history_dock"
    LOG_OUTPUT_DOCK = "log_output_dock"
    TOOLBAR_DOCK = "toolbar_dock"
    INSPECTOR_DOCK = "inspector_dock"


class GraphicsPlugShape(enum.IntEnum):
    CIRCLE = 0
    TRIANGLE = enum.auto()
    PENTAGON = enum.auto()
    SQUARE = enum.auto()
    SQUARE_MATRIX = enum.auto()
    BARS = enum.auto()
    DIAMOND = enum.auto()
