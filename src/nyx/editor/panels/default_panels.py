from __future__ import annotations

from nyx.editor.core.actions import ActionId

from .panel_registry import (
    PANEL_REGISTRY,
    PanelArea,
    PanelDefinition,
    PanelRegistry,
    SidebarActionDefinition,
)


class DefaultPanelId:
    """Ids of the panels registered by the editor."""

    NODES = "nodes"
    TREE = "tree"
    UNDO = "undo"
    BRIDGE = "bridge"
    INSPECTOR = "inspector"
    CONSOLE = "console"
    DOCS = "docs"
    SETTINGS = "settings"


def register_default_panels(registry: PanelRegistry = PANEL_REGISTRY) -> None:
    """Register the editor panels and sidebar action buttons.

    Calling it again replaces them.

    Args:
        registry (PanelRegistry): registry to fill.
    """
    for definition in (
        PanelDefinition(
            DefaultPanelId.TREE,
            "Tree",
            ":/icons/stage_object",
            lambda window: window.stage_tree_view,
        ),
        PanelDefinition(
            DefaultPanelId.NODES,
            "Nodes",
            ":/icons/plus",
            lambda window: window.nodes_palette_view,
        ),
        PanelDefinition(
            DefaultPanelId.UNDO,
            "History",
            ":/icons/history",
            lambda window: window.undo_view,
        ),
        PanelDefinition(
            DefaultPanelId.BRIDGE,
            "Bridge",
            ":/icons/link",
            lambda window: window.bridge_panel,
        ),
        PanelDefinition(
            DefaultPanelId.INSPECTOR,
            "Inspector",
            ":/icons/info",
            lambda window: window.inspector,
            area=PanelArea.RIGHT,
            has_sidebar_button=False,
        ),
        PanelDefinition(
            DefaultPanelId.CONSOLE,
            "Console",
            ":/icons/frame_bug",
            lambda window: window.output_log_widget,
            area=PanelArea.BOTTOM,
            is_persistent=True,
        ),
    ):
        registry.register(definition)
    for action_definition in (
        SidebarActionDefinition(
            DefaultPanelId.DOCS, "Docs", ":/icons/file_open", ActionId.DOCUMENTATION
        ),
        SidebarActionDefinition(
            DefaultPanelId.SETTINGS,
            "Settings",
            ":/icons/settings",
            ActionId.EDIT_CONFIG,
            menu_action_ids=(ActionId.RESET_CONFIG,),
        ),
    ):
        registry.register_action_button(action_definition)
