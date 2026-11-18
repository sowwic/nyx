# New inspector widget

An **inspector widget** is the widget the Inspector panel shows for the selected stage
object. The Inspector doesn't know the types it shows: a type names its widget by an id,
and the widget comes from the registry.

```text
stage object type                          inspector widget
   get_inspector_widget_id()  ──id──▶  NYX_REGISTRY.inspector_widgets[id]  ──▶  widget
```

When the selection changes, the Inspector reads `type(obj).get_inspector_widget_id()` of
the first selected object (nodes come before util objects; with nothing selected it shows
the root node), finds the class in the registry, creates it the first time it is needed
and keeps it. The same widget is given every object of its type that is selected later. A
type that returns `None` (the default) gets the placeholder text *No inspector available
for ...*; an id with no registered class logs `Unknown inspector widget ...` once and shows
a placeholder.

| Id | Shows | Registered by |
| --- | --- | --- |
| `core.node_inspector` (`CoreInspectorWidgets.NODE`) | the header, the error and the components of a node | the editor, always |
| `core.note_inspector` (`NOTE`) | the text and color of a note | the `NyxStdlib` plugin |
| `core.group_inspector` (`GROUP`) | the title and color of a group | the `NyxStdlib` plugin |

Only nodes and util objects can be selected for now. Components and links return `None`.

!!! warning
    Inspector widgets belong to the editor (`nyx.editor`), which is **not** part of
    `nyx.api.v1` and isn't versioned like it. The base classes are exported through
    `nyx.api.v1.editor_utils` and live in `nyx.editor.widgets.inspector_widgets`. The
    standard library does the same (`nyx/stdlib/inspector_widgets`), use it as the
    reference and expect to adjust when the editor internals change.

## A complete example: the checklist

For the checklist of [New util object](util-object.md):

```python
# studio_tools/inspector_widgets/checklist.py
from PySide6 import QtCore, QtWidgets

from nyx.api.v1.editor_utils import CommitPlainTextEdit, UtilObjectInspectorWidget


class ChecklistInspector(UtilObjectInspectorWidget):
    """Edits the items of a ChecklistObject, one per line."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the inspector widget is registered with."""
        return "studio.checklist_inspector"

    def _create_form(self, form_layout: QtWidgets.QFormLayout) -> None:
        """Add the rows of the form.

        Args:
            form_layout (QtWidgets.QFormLayout): layout of the form.
        """
        self.items_edit = CommitPlainTextEdit()
        form_layout.addRow("Items", self.items_edit)
        self.items_edit.editing_finished.connect(self.commit_pending_edit)

    def _show_object(self, checklist) -> None:
        """Show the items of the object.

        Args:
            checklist (ChecklistObject): object to show.
        """
        text = "\n".join(checklist.items)
        if self.items_edit.toPlainText() != text:
            with QtCore.QSignalBlocker(self.items_edit):
                self.items_edit.setPlainText(text)

    def commit_pending_edit(self) -> None:
        """Push the items, if they differ from the ones of the object."""
        items = self.items_edit.toPlainText().splitlines()
        self.push_properties({"items": items}, "Edit checklist")
```

The util object returns the id from `get_inspector_widget_id()`:

```python
@classmethod
def get_inspector_widget_id(cls) -> str | None:
    """str | None: id of the inspector widget showing the type."""
    return "studio.checklist_inspector"
```

and the plugin lists the class:

```python
plugin.contents.util_objects = [ChecklistObject]
plugin.contents.graphics_objects = [GraphicsChecklist]
plugin.contents.inspector_widgets = [ChecklistInspector]
```

## What the base classes do for you

`InspectorWidget` (a `QWidget`) is the base of every inspector widget:

| Member | Purpose |
| --- | --- |
| `get_type_id()` | **You implement it.** The id the widget is registered with, the one types return from `get_inspector_widget_id()`. |
| `set_stage_object(obj)` | Called by the Inspector with the object to show, or `None` to show none. Remembers the object by its uuid and calls `refresh` or `clear`. |
| `stage_object`, `stage` | The shown object and its stage, looked up by uuid. `stage_object` is `None` when the object was deleted, so a widget never keeps a deleted object alive. |
| `refresh()` | **You implement it.** Show the current state of `stage_object`. It is also called after every undo or redo, so it must be cheap and must not reset a field the user is typing in. |
| `clear()` | **You implement it.** Show no object. |

`UtilObjectInspectorWidget` adds what util objects share: a header with the type and path
of the object, a read only form while the object is locked, and:

| Member | Purpose |
| --- | --- |
| `_create_form(form_layout)` | **You implement it.** Add your rows to the form, once. |
| `_show_object(util_object)` | **You implement it.** Fill the form from the object. |
| `commit_pending_edit()` | Push what the user typed but did not finish. Called before another object is shown, because the focus can leave a field after the selection changed. |
| `push_properties(properties, text)` | Pushes a `SetUtilObjectPropertiesCommand`, so the change is undoable. Does nothing for a locked object or an unchanged value. **Never change the object directly.** |
| `create_color_combo(presets)`, `show_color(combo, color)` | A color chooser with swatches, showing a color that isn't a preset as *Custom*. |
| `CommitPlainTextEdit` | Multi-line text edit with an `editing_finished` signal, emitted when it loses the focus. Commit on that, not on every key, so one edit is one undo step. |

## Registering

- `NyxPluginContents.inspector_widgets` takes classes with a `get_type_id` **classmethod**.
  The registry skips (and logs) an id that is already registered.
- Inspector widgets are registered when the plugin content is, so they are available when
  the editor opens its first stage.
- Built-in ids are kept when the registry is rebuilt; plugin ones are dropped and
  registered again from the enabled plugins.

## Showing nodes differently

Node types return `core.node_inspector` from `get_inspector_widget_id()`. A node type can
return the id of a widget of your own instead, to show its own editor in place of the
list of components. The node widget (`NodeInspectorWidget` in
`nyx.editor.widgets.inspector_widgets`) is the reference. This isn't used by any plugin in
the repository yet.
