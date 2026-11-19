# New spawner

A **spawner** creates stage objects when the user asks for them. They are how a util object
from a plugin gets into a stage: it is invisible to users until a spawner adds it. The note
and the group are created by spawners.

Right-click the graph:

```text
Create >  Node...
          ───────────
          Note
          Group
          <spawners of plugins>
```

`Node...` opens the nodes palette. The spawners follow in the order they are registered, the
standard library first. The tree view has no Create menu: it can't show util objects.

When the user picks an entry, the editor builds a `SpawnContext` and calls
`spawner.spawn(context)`. The spawner pushes a create command to the stage, so the creation
is one undo step, and returns what it created. The editor then selects it.

## The family

```text
StageObjectSpawner            base: push a create command, report the result
├── NodeSpawner               nodes picked in the nodes palette
├── NodeComponentSpawner      components picked in the components list
└── UtilObjectSpawner         util objects, and what plugins register for the Create menu
```

| Class | Used by | Plugin content |
| --- | --- | --- |
| `StageObjectSpawner` | the base of the others, in `nyx.editor.controllers.stage_object_spawner` | a spawner of another kind subclasses it |
| `UtilObjectSpawner` | the Create menu, through `NoteSpawner`, `GroupSpawner` and the spawners of plugins | yes, the ready-made helper |
| `NodeSpawner` | the nodes palette (QML) | no, nothing registers it |
| `NodeComponentSpawner` | the components list (QML) | no, nothing registers it |

All of them push the command with `_spawn(stage, command, get_result)`. It returns the
created object and emits `spawned`; a command the stage refuses (an unknown type, a scope
that is locked) gives a warning and returns `None`, so a refused creation never raises into
QML or the menu.

| Id | Creates | Registered by |
| --- | --- | --- |
| `core.note_spawner` (`CoreSpawners.NOTE`) | a note where the user clicked | the `NyxStdlib` plugin |
| `core.group_spawner` (`GROUP`) | a group around the selected nodes, or where the user clicked | the `NyxStdlib` plugin |

!!! warning
    Spawners belong to the editor (`nyx.editor`), which is **not** part of `nyx.api.v1` and
    isn't versioned like it. The base classes are exported through `nyx.api.v1.editor_utils`
    and live in `nyx.editor.controllers`. The standard library does the same
    (`nyx/stdlib/spawners`), use it as the reference and expect to adjust when the editor
    internals change.

## A spawner for a util object

For the checklist of [New util object](util-object.md) it is a few lines:

```python
# studio_tools/spawners/checklist.py
from nyx.api.v1.editor_utils import UtilObjectSpawner


class ChecklistSpawner(UtilObjectSpawner):
    """Creates a checklist where the user clicked."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the spawner is registered with."""
        return "studio.checklist_spawner"

    @classmethod
    def get_util_object_type_id(cls) -> str:
        """str: type id of the util object created."""
        return "studio:checklist"
```

and the plugin lists it:

```python
plugin.contents.util_objects = [ChecklistObject]
plugin.contents.graphics_objects = [GraphicsChecklist]
plugin.contents.spawners = [ChecklistSpawner]
```

The name, icon and description of the menu entry come from the util object type
(`get_type_display_name()`, `get_type_icon()`, `get_description()`). To change how the object
starts, override a hook:

| Hook | Default |
| --- | --- |
| `get_creation_geometry(context)` | `(context.position, None)`: where the user clicked, at the default size of the type. Return a size to choose it. The group returns the area around the selected nodes. |
| `get_creation_properties(context)` | `None`: the defaults of the type. Return values as listed by `serialize_properties()` to start with more, for example the first items of a checklist. |

## A spawner that creates anything

A spawner that doesn't make a util object subclasses `StageObjectSpawner` and implements the
menu contract itself:

```python
from nyx.api.v1 import CoreNodes, commands
from nyx.api.v1.editor_utils import StageObjectSpawner


class ReadmeNodeSpawner(StageObjectSpawner):
    """Creates an empty node named readme, where the user clicked."""

    @classmethod
    def get_type_id(cls) -> str:
        return "studio.readme_node_spawner"

    @classmethod
    def get_display_name(cls) -> str:
        return "Readme node"

    def spawn(self, context):
        command = commands.CreateNodeCommand(
            stage=context.stage,
            type_id=CoreNodes.EMPTY,
            parent_node=context.scope_node,
            position=context.position,
            name="readme",
        )
        return self._spawn(context.stage, command, lambda: command.result_node)
```

| Member | Purpose |
| --- | --- |
| `get_type_id()` | **You implement it.** Unique id of the spawner, the key in the registry. |
| `get_display_name()` | **You implement it.** Text of the menu entry. |
| `spawn(context)` | **You implement it.** Create the thing with `_spawn` and return it (a node or a util object) so the editor selects it, or return `None`. A spawner that pushes commands itself may raise `NyxCommandValidationError`: it shows a warning and changes nothing. |
| `get_icon()` | Resource path of the icon, `:/icons/plus` by default. |
| `get_description()` | Tooltip of the entry, empty by default. |
| `is_available(context)` | Whether the entry is enabled. By default it is disabled in a scope that can't take new objects (the contents of a reference). |

The editor makes one instance of a registered spawner for each graph view, the first time it
is used, so a spawner may keep state between uses.

## The context

`spawn` and `is_available` get a `SpawnContext`:

| Field | Holds |
| --- | --- |
| `stage` | The stage being edited. Push commands to it. |
| `scope_node` | The node whose contents are drawn. New nodes and util objects go in it. |
| `position` | Where the user right-clicked, in scene coordinates. |
| `selection_rect` | The area taken by the selected nodes, `None` if no node is selected. |
| `graph_editor` | The editor of the graph, for anything else you need. |

## Registering

- `NyxPluginContents.spawners` takes classes with a `get_type_id` **classmethod**. The registry
  skips (and logs) an id that is already registered.
- The order of the list is the order of the menu. Plugins are registered in discovery order, so
  the spawners of the standard library come first.
- Spawners are dropped and registered again from the enabled plugins whenever the plugin
  content is rebuilt.
- Plugin spawners have no keyboard shortcut. The note and the group keep the shortcuts of
  their own actions (Ctrl+G for a group).
