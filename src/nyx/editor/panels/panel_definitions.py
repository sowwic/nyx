from __future__ import annotations

from nyx.editor.core.actions import ActionId

from .panel_registry import (
    PANEL_REGISTRY,
    PanelArea,
    PanelDefinition,
    PanelRegistry,
    SidebarActionDefinition,
)


class PanelId:
    """Ids of the panels registered by the editor."""

    NODES = "nodes"
    TREE = "tree"
    UNDO = "undo"
    BRIDGE = "bridge"
    INSPECTOR = "inspector"
    CONSOLE = "console"
    HELP = "help"
    SETTINGS = "settings"


PANELS: tuple[PanelDefinition, ...] = (
    PanelDefinition(
        PanelId.TREE,
        "Tree",
        ":/icons/tree_graph",
        lambda window: window.stage_tree_view,
    ),
    PanelDefinition(
        PanelId.NODES,
        "Nodes",
        ":/icons/library",
        lambda window: window.nodes_palette_view,
    ),
    PanelDefinition(
        PanelId.UNDO,
        "History",
        ":/icons/history",
        lambda window: window.undo_view,
    ),
    PanelDefinition(
        PanelId.BRIDGE,
        "Bridge",
        ":/icons/link",
        lambda window: window.bridge_panel,
    ),
    PanelDefinition(
        PanelId.INSPECTOR,
        "Inspector",
        ":/icons/inspector",
        lambda window: window.inspector,
        area=PanelArea.RIGHT,
        has_sidebar_button=False,
    ),
    PanelDefinition(
        PanelId.CONSOLE,
        "Console",
        ":/icons/console",
        lambda window: window.output_log_widget,
        area=PanelArea.BOTTOM,
        is_persistent=True,
    ),
)
"""Panels of the editor, in the order of their sidebar buttons."""

SIDEBAR_ACTIONS: tuple[SidebarActionDefinition, ...] = (
    SidebarActionDefinition(
        PanelId.HELP,
        "Help",
        ":/icons/help",
        menu_action_ids=(
            ActionId.DOCUMENTATION,
            ActionId.SUBMIT_ISSUE,
            ActionId.ABOUT,
        ),
    ),
    SidebarActionDefinition(
        PanelId.SETTINGS,
        "Settings",
        ":/icons/settings",
        ActionId.EDIT_CONFIG,
        menu_action_ids=(ActionId.RESET_CONFIG,),
    ),
)
"""Sidebar buttons of the editor that trigger an action instead of opening a panel."""


def register_panels(registry: PanelRegistry = PANEL_REGISTRY) -> None:
    """Register the editor panels and sidebar action buttons.

    Calling it again replaces them.

    Args:
        registry (PanelRegistry): registry to fill.
    """
    for definition in PANELS:
        registry.register(definition)
    for action_definition in SIDEBAR_ACTIONS:
        registry.register_action_button(action_definition)
