# Graph view memory

The graph view remembers where it was in every node it has shown the contents of. Going
into a node, and coming back out, puts the view back where you left it, and the places are
saved with the stage. This page describes the pieces, for people working on Nyx or on tools
that read and write stages.

## Model

A node stores the view in its **metadata**, under two keys:

| Key | Holds |
| --- | --- |
| `graph_view_position` | `[x, y]`, the scene point the view is centered on |
| `graph_view_zoom` | the zoom level, a number |

`Node.get_graph_view()` returns `(QtCore.QPointF, float)`, or `None` if the contents of the
node were never shown or the stored values can't be read. `Node.set_graph_view(position,
zoom)` stores them. The keys are `Node.GRAPH_VIEW_POSITION_KEY` and
`Node.GRAPH_VIEW_ZOOM_KEY`.

```python
from PySide6 import QtCore

node.set_graph_view(QtCore.QPointF(120.0, -40.0), 2.0)
position, zoom = node.get_graph_view()
```

`StageObject.metadata` is a plain dict of JSON values that every stage object has. It is
written as the `metadata` key of the serialized object (links add their relative path to a
copy of it) and read back for nodes. Files from before it was read load as they did, and a
node keeps what it has when the data has no `metadata`.

!!! note
    Changing metadata is not an edit. It isn't a command, it can't be undone and it doesn't
    mark the stage as modified. That is on purpose: moving the view shouldn't ask you to
    save.

## When it is recorded and restored

`StageGraphEditor` does it, because it owns the view and the scope:

- **Recording** (`record_view_state`) happens in `set_scope_path`, just before the scope
  changes. It stores the view in the metadata of the node that was shown. It also happens
  when the stage is saved, for the scope being shown, so the last place is not lost. Nothing
  is recorded while the view is hidden, because its center means nothing then, or when the
  node doesn't exist anymore (a deleted scope).
- **Restoring** (`restore_view_state`) happens after the scope changed and the scene was
  rebuilt, and after a stage file is loaded, for the scope being shown. A node that has no
  stored view leaves the view where it is.
- Setting the scope that is already shown does nothing, and neither does a silent change
  (`set_scope_path(..., silent=True)`).
- A session file still stores the view of the active scope on its own. When a session is
  restored its view is applied last, so it wins.

## Setting the view exactly

`StageGraphView.apply_view_state` uses `center_on_exactly`. A single `centerOn` lands off the
point by up to a scrollbar step, which is several pixels in a scene as large as this one, and
always the same way, so restoring the same view again and again made it creep. It now asks
again, shifted by what was missed, which settles on the nearest position the scrollbars can
reach. Applying a state a second time doesn't move the view.

The tests are in `tests/core/test_node_metadata.py` (metadata, the graph view accessors,
serialization and files) and `tests/editor/test_graph_view_memory.py` (recording, restoring,
saving, loading, sessions and the stable restore).
