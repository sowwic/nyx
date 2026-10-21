import typing
import contextlib
import html

from PySide6 import QtCore, QtWidgets, QtQml

from ...core.datatypes.datatype import value_to_class_name
from ...core.layered_config import NyxConfig
from ...static.enums import CoreDatatypes
from ...static.vars import DEBUG

if typing.TYPE_CHECKING:
    from ..widgets.stage_graph_editor import StageGraphEditor
    from ...application import NyxEditorApplication
    from ...core.node_component import NodeComponent


def get_application_qml_engine() -> QtQml.QQmlEngine:
    """Get the QML engine of the application.

    Returns:
        QtQml.QQmlEngine: shared QML engine.

    Raises:
        RuntimeError: if no application exists.
    """
    app: NyxEditorApplication | None = QtWidgets.QApplication.instance()
    if app is None:
        raise RuntimeError("Failed to get Qml engine: no QApplication exists yet; ")
    return app.qml_engine


def get_current_stage_graph() -> StageGraphEditor:
    """Get the editor of the active window.

    Returns:
        StageGraphEditor: active editor, None if no window is open.
    """
    app: NyxEditorApplication = QtWidgets.QApplication.instance()
    return app.main_window().current_stage_graph


def resolve_to_source_index(model_index: QtCore.QModelIndex) -> QtCore.QModelIndex:
    """Map an index through proxy models down to the source model.

    Args:
        model_index (QtCore.QModelIndex): index in any model of the proxy chain.

    Returns:
        QtCore.QModelIndex: index in the source model.
    """
    current_model = model_index.model()
    while isinstance(current_model, QtCore.QAbstractProxyModel):
        model_index = current_model.mapToSource(model_index)
        current_model = model_index.model()
    return model_index


@contextlib.contextmanager
def blocked_signals(*objs):
    """Block signals of objects within a context, restoring their previous state after.

    Args:
        *objs (QtCore.QObject): objects to block.

    Yields:
        None: while signals are blocked.
    """
    previous = [o.blockSignals(True) for o in objs]
    try:
        yield
    finally:
        for o, p in zip(objs, previous):
            o.blockSignals(p)


def get_app_config() -> NyxConfig:
    """Get the config of the running application.

    Returns:
        NyxConfig: config the application loaded at startup, so it has the values of
            the user's config file. Without an application a new config is created and
            resolved.
    """
    config = getattr(QtWidgets.QApplication.instance(), "config", None)
    if config is None:
        config = NyxConfig()
        config.resolve()
    return config


def are_hover_diagnostics_enabled() -> bool:
    """Check whether graphics items show their model roles as a tooltip.

    Returns:
        bool: enabled in the config or in debug mode.
    """
    node_config = get_app_config().values.editor_widgets.graphics_stage.nodes
    return bool(node_config.hover_diagnostics or DEBUG)


def build_role_tooltip_html(
    model_index: QtCore.QModelIndex, maximum_value_length: int = 200
) -> str:
    """Build an HTML table of all roles of a model index.

    Args:
        model_index (QtCore.QModelIndex): index to describe.
        maximum_value_length (int): role values are truncated to this length.

    Returns:
        str: HTML table.
    """
    model_of_index = model_index.model()
    role_identifier_to_role_name = model_of_index.roleNames()

    table_row_html_fragments = []
    for role_identifier in sorted(role_identifier_to_role_name):
        if role_identifier == QtCore.Qt.ToolTipRole:
            continue  # reading our own role would recurse forever

        role_name = bytes(role_identifier_to_role_name[role_identifier].data()).decode(
            "utf-8"
        )
        role_value = model_index.data(role_identifier)
        role_value_text = (
            repr(role_value) if not isinstance(role_value, str) else role_value
        )
        if len(role_value_text) > maximum_value_length:
            role_value_text = role_value_text[:maximum_value_length] + "…"

        table_row_html_fragments.append(
            f"<tr><td><b>{html.escape(role_name)}</b>&nbsp;&nbsp;</td>"
            f"<td>{html.escape(role_value_text)}</td></tr>"
        )

    return "<table>" + "".join(table_row_html_fragments) + "</table>"


def build_component_tooltip_html(
    component: NodeComponent, maximum_value_length: int = 200
) -> str:
    """Build the tooltip of a component: a description section, then a value section.

    Args:
        component (NodeComponent): component to describe.
        maximum_value_length (int): values are truncated to this length.

    Returns:
        str: HTML. Components that hold no value, like a flow, only get the description.
    """

    def format_value(value: typing.Any) -> str:
        text = str(value_to_class_name(value))
        if len(text) > maximum_value_length:
            text = text[:maximum_value_length] + "…"
        return html.escape(text)

    def heading(title: str) -> str:
        style = "border-bottom: 1px solid gray"
        return f"<tr><th align='left' style='{style}'>{title}</th></tr>"

    rows = [
        heading("Description"),
        f"<tr><td>{html.escape(component.description)}</td></tr>",
    ]
    if component.datatype_id != CoreDatatypes.FLOW:
        rows += [
            "<tr><td height='6'></td></tr>",
            heading("Value"),
            "<tr><td>"
            f"<b>Raw:</b> {format_value(component.raw_value)}<br>"
            f"<b>Cache:</b> {format_value(component.cached_value)}"
            "</td></tr>",
        ]
    return (
        "<table width='100%' cellspacing='0' cellpadding='0'>"
        + "".join(rows)
        + "</table>"
    )
