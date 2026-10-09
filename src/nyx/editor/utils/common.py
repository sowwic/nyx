import typing
import contextlib

from PySide6 import QtWidgets


if typing.TYPE_CHECKING:
    from ..widgets.stage_graph_editor import StageGraphEditor
    from ...application import NyxEditorApplication


def get_current_stage_graph() -> StageGraphEditor:
    app: NyxEditorApplication = QtWidgets.QApplication.instance()
    return app.main_window().current_stage_graph


@contextlib.contextmanager
def blocked_signals(*objs):
    previous = [o.blockSignals(True) for o in objs]
    try:
        yield
    finally:
        for o, p in zip(objs, previous):
            o.blockSignals(p)
