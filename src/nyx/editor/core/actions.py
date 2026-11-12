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
    EDIT_CONFIG = "edit.edit_config"
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
    # View
    VIEWPORT_DEBUG_OVERLAY = "view.viewport_debug_overlay"
    SHOW_ADDRESS_NAMES = "view.show_address_names"
    ALWAYS_ON_TOP = "view.always_on_top"
    # Help
    DOCUMENTATION = "help.documentation"
    ABOUT = "help.about"
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
        D(
            ActionId.NEW_STAGE,
            "New Stage",
            "File",
            default_shortcut="Ctrl+Shift+N",
            icon_path=":/icons/new_file",
        ),
        D(
            ActionId.OPEN_STAGE,
            "Open Stage...",
            "File",
            icon_path=":/icons/file_open",
            default_shortcut="Ctrl+Shift+O",
        ),
        D(
            ActionId.OPEN_STAGE_TAB,
            "Open Stage As New Tab...",
            "File",
            icon_path=":/icons/tab",
        ),
        D(
            ActionId.SAVE_STAGE,
            "Save Stage",
            "File",
            icon_path=":/icons/save",
            default_shortcut="Ctrl+Shift+S",
        ),
        D(
            ActionId.SAVE_STAGE_AS,
            "Save Stage As...",
            "File",
            icon_path=":/icons/save_as",
        ),
        D(ActionId.IMPORT_STAGE, "Import Stage...", "File", icon_path=":/icons/import"),
        D(
            ActionId.REFERENCE_STAGE,
            "Reference Stage...",
            "File",
            icon_path=":/icons/asterisk",
        ),
        D(ActionId.SAVE_SESSION, "Save Session As...", "File", icon_path=":/icons/save"),
        D(
            ActionId.LOAD_SESSION,
            "Load Session...",
            "File",
            icon_path=":/icons/file_open",
        ),
        D(
            ActionId.RESTORE_LAST_SESSION,
            "Restore Last Session",
            "File",
            icon_path=":/icons/restore_page",
        ),
        D(ActionId.UNDO, "Undo", "Edit", default_shortcut="Ctrl+Z"),
        D(ActionId.REDO, "Redo", "Edit", default_shortcut="Ctrl+Y"),
        D(
            ActionId.RENAME_NODE,
            "Rename Selected Node",
            "Edit",
            icon_path=":/icons/edit",
            default_shortcut="F2",
        ),
        D(ActionId.EDIT_CONFIG, "Config...", "Edit", icon_path=":/icons/settings"),
        D(
            ActionId.RESET_CONFIG,
            "Reset Config",
            "Edit",
            icon_path=":/icons/reset_settings",
        ),
        D(
            ActionId.COPY,
            "Copy",
            "Edit",
            default_shortcut="Ctrl+C",
            icon_path=":/icons/copy",
        ),
        D(
            ActionId.CUT,
            "Cut",
            "Edit",
            default_shortcut="Ctrl+X",
            icon_path=":/icons/cut",
        ),
        D(
            ActionId.PASTE,
            "Paste",
            "Edit",
            default_shortcut="Ctrl+V",
            icon_path=":/icons/paste",
        ),
        D(
            ActionId.DELETE,
            "Delete",
            "Edit",
            default_shortcut="Delete",
            icon_path=":/icons/delete",
        ),
        D(
            ActionId.FOCUS_SELECTED,
            "Focus on selected nodes",
            "Edit",
            default_shortcut="F",
            icon_path=":/icons/focus",
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
        D(
            ActionId.COPY_NODE_PATH,
            "Copy path to selected",
            "Node",
            icon_path=":/icons/link",
        ),
        D(ActionId.RELOAD_REFERENCE, "Reload reference", "Node"),
        D(ActionId.OPEN_REFERENCED_STAGE, "Open referenced stage", "Node"),
        D(ActionId.SHOW_PALETTE, "Add Node...", "Node", default_shortcut="Tab"),
        D(
            ActionId.VIEWPORT_DEBUG_OVERLAY,
            "Viewport Debug Overlay",
            "View",
            default_shortcut="F3",
            status_tip="Show performance numbers in the corner of the graph views",
            checkable=True,
        ),
        D(
            ActionId.SHOW_ADDRESS_NAMES,
            "Show Address Names",
            "View",
            status_tip="Show the names paths are made of, instead of the display "
            "names of nodes and components",
            checkable=True,
        ),
        D(
            ActionId.ALWAYS_ON_TOP,
            "Always on Top",
            "View",
            status_tip="Keep the main window above other windows",
            checkable=True,
        ),
        D(
            ActionId.DOCUMENTATION,
            "Documentation",
            "Help",
            icon_path=":/icons/info",
            status_tip="Open the Nyx documentation in the browser",
        ),
        D(ActionId.ABOUT, "About", "Help", status_tip="Show information about Nyx"),
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
