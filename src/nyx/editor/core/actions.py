"""Default editor action definitions."""

from enum import StrEnum

from nyx.editor.core.action_registry import (
    ACTION_REGISTRY,
    ActionDefinition,
    ActionRegistry,
)


class ActionId(StrEnum):
    """Ids of the default editor actions, grouped by menu."""

    # File
    NEW_STAGE = "file.new_stage"
    OPEN_STAGE = "file.open_stage"
    OPEN_STAGE_TAB = "file.open_stage_tab"
    SAVE_STAGE = "file.save_stage"
    SAVE_STAGE_AS = "file.save_stage_as"
    IMPORT_STAGE = "file.import_stage"
    REFERENCE_STAGE = "file.reference_stage"
    SAVE_SESSION = "file.save_session"
    LOAD_SESSION = "file.load_session"
    RESTORE_LAST_SESSION = "file.restore_last_session"
    # Edit
    UNDO = "edit.undo"
    REDO = "edit.redo"
    RENAME_NODE = "edit.rename_node"
    RESET_CONFIG = "edit.reset_config"
    COPY = "edit.copy"
    CUT = "edit.cut"
    PASTE = "edit.paste"
    DELETE = "edit.delete"
    FOCUS_SELECTED = "edit.focus_selected"
    # Node
    CREATE_NODE = "node.create"
    DELETE_NODE = "node.delete"
    CREATE_NOTE = "node.create_note"
    CREATE_GROUP = "node.create_group"
    COPY_NODE_PATH = "node.copy_path"
    RELOAD_REFERENCE = "node.reload_reference"
    OPEN_REFERENCED_STAGE = "node.open_referenced_stage"
    SHOW_PALETTE = "node.show_palette"
    # Stage
    EXECUTE_STAGE = "stage.execute"
    EXECUTE_FROM_SELECTED = "stage.execute_from_selected"


def default_definitions() -> list[ActionDefinition]:
    """Get the definitions of the default editor actions.

    Returns:
        list[ActionDefinition]: default action definitions.
    """
    D = ActionDefinition
    return [
        D(ActionId.NEW_STAGE, "New Stage", "File", default_shortcut="Ctrl+Shift+N"),
        D(
            ActionId.OPEN_STAGE,
            "Open Stage...",
            "File",
            default_shortcut="Ctrl+Shift+O",
        ),
        D(ActionId.OPEN_STAGE_TAB, "Open Stage As New Tab...", "File"),
        D(
            ActionId.SAVE_STAGE,
            "Save Stage",
            "File",
            default_shortcut="Ctrl+Shift+S",
        ),
        D(ActionId.SAVE_STAGE_AS, "Save Stage As...", "File"),
        D(ActionId.IMPORT_STAGE, "Import Stage...", "File"),
        D(ActionId.REFERENCE_STAGE, "Reference Stage...", "File"),
        D(ActionId.SAVE_SESSION, "Save Session As...", "File"),
        D(ActionId.LOAD_SESSION, "Load Session...", "File"),
        D(ActionId.RESTORE_LAST_SESSION, "Restore Last Session", "File"),
        D(ActionId.UNDO, "Undo", "Edit", default_shortcut="Ctrl+Z"),
        D(ActionId.REDO, "Redo", "Edit", default_shortcut="Ctrl+Y"),
        D(
            ActionId.RENAME_NODE,
            "Rename Selected Node",
            "Edit",
            default_shortcut="F2",
        ),
        D(ActionId.RESET_CONFIG, "Reset Config", "Edit"),
        D(ActionId.COPY, "Copy", "Edit", default_shortcut="Ctrl+C"),
        D(ActionId.CUT, "Cut", "Edit", default_shortcut="Ctrl+X"),
        D(ActionId.PASTE, "Paste", "Edit", default_shortcut="Ctrl+V"),
        D(ActionId.DELETE, "Delete", "Edit", default_shortcut="Delete"),
        D(
            ActionId.FOCUS_SELECTED,
            "Focus on selected nodes",
            "Edit",
            default_shortcut="F",
        ),
        D(ActionId.CREATE_NODE, "Create node", "Node", icon_path=":/icons/plus"),
        D(ActionId.DELETE_NODE, "Delete node", "Node", icon_path=":/icons/delete"),
        D(ActionId.CREATE_NOTE, "Create note", "Node", icon_path=":/icons/sticky_note"),
        D(
            ActionId.CREATE_GROUP,
            "Create group",
            "Node",
            default_shortcut="Ctrl+G",
            icon_path=":/icons/group",
        ),
        D(ActionId.COPY_NODE_PATH, "Copy path to selected", "Node"),
        D(ActionId.RELOAD_REFERENCE, "Reload reference", "Node"),
        D(ActionId.OPEN_REFERENCED_STAGE, "Open referenced stage", "Node"),
        D(ActionId.SHOW_PALETTE, "Add Node...", "Node", default_shortcut="Tab"),
        D(
            ActionId.EXECUTE_STAGE,
            "Execute stage",
            "Stage",
            icon_path=":/icons/exec_stage",
        ),
        D(
            ActionId.EXECUTE_FROM_SELECTED,
            "Execute from selected node",
            "Stage",
            icon_path=":/icons/exec_from",
        ),
    ]


def register_default_actions(registry: ActionRegistry = ACTION_REGISTRY) -> None:
    """Register default definitions. Safe to call more than once."""
    registry.register_definitions(
        d for d in default_definitions() if not registry.has_definition(d.action_id)
    )
