"""Helpers for plugins that add to the editor: widgets, QML, icons and tooltips.

Most of them need a running `QApplication`, and `get_current_stage_graph` the editor
window, so they are for code that runs in the editor, not in a headless run.
"""

from nyx.editor.creators import Creator, CreatorContext, UtilObjectCreator
from nyx.editor.widgets.common_widgets import CommitPlainTextEdit
from nyx.editor.widgets.inspector_widgets import (
    InspectorWidget,
    UtilObjectInspectorWidget,
)
from nyx.editor.utils.common import (
    blocked_signals,
    build_component_tooltip_html,
    build_role_tooltip_html,
    get_application_qml_engine,
    get_current_stage_graph,
    note_to_html,
    resolve_to_source_index,
)
from nyx.utils.icon_fn import create_mono_icon, create_mono_image

__all__ = [
    "CommitPlainTextEdit",
    "Creator",
    "CreatorContext",
    "UtilObjectCreator",
    "InspectorWidget",
    "UtilObjectInspectorWidget",
    "blocked_signals",
    "build_component_tooltip_html",
    "build_role_tooltip_html",
    "create_mono_icon",
    "create_mono_image",
    "get_application_qml_engine",
    "get_current_stage_graph",
    "note_to_html",
    "resolve_to_source_index",
]
