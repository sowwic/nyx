import typing
import contextlib
import html

from PySide6 import QtCore, QtWidgets


if typing.TYPE_CHECKING:
    from ..widgets.stage_graph_editor import StageGraphEditor
    from ...application import NyxEditorApplication


def get_current_stage_graph() -> StageGraphEditor:
    app: NyxEditorApplication = QtWidgets.QApplication.instance()
    return app.main_window().current_stage_graph


def resolve_to_source_index(model_index: QtCore.QModelIndex) -> QtCore.QModelIndex:
    current_model = model_index.model()
    while isinstance(current_model, QtCore.QAbstractProxyModel):
        model_index = current_model.mapToSource(model_index)
        current_model = model_index.model()
    return model_index


@contextlib.contextmanager
def blocked_signals(*objs):
    previous = [o.blockSignals(True) for o in objs]
    try:
        yield
    finally:
        for o, p in zip(objs, previous):
            o.blockSignals(p)


def build_role_tooltip_html(
    model_index: QtCore.QModelIndex, maximum_value_length: int = 200
) -> str:
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
