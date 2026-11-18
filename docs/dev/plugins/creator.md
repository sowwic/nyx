# New creator

A **creator** is an entry of the **Create** menu of the graph view. It is how the user adds
something to the stage that isn't a node picked from the palette: the note and the group are
creators, and a util object from a plugin is invisible to users until a creator adds it.

Right-click the graph:

```text
Create >  Node...
          ───────────
          Note
          Group
          <creators of plugins>
```

`Node...` opens the nodes palette. The creators follow in the order they are registered, the
standard library first. The tree view has no Create menu: it can't show util objects.

When the user picks an entry, the editor builds a `CreatorContext` and calls
`creator.create(context)`. The creator pushes its commands to the stage, so the creation is
one undo step, and returns what it created. The editor then selects it.

| Id | Creates | Registered by |
| --- | --- | --- |
| `core.create_note` (`CoreCreators.NOTE`) | a note where the user clicked | the `NyxStdlib` plugin |
| `core.create_group` (`GROUP`) | a group around the selected nodes, or where the user clicked | the `NyxStdlib` plugin |

!!! warning
    Creators belong to the editor (`nyx.editor`), which is **not** part of `nyx.api.v1` and
    isn't versioned like it. The base classes are exported through `nyx.api.v1.editor_utils`
    and live in `nyx.editor.creators`. The standard library does the same
    (`nyx/stdlib/creators`), use it as the reference and expect to adjust when the editor
    internals change.

## A creator for a util object

For the checklist of [New util object](util-object.md) it is a few lines:

```python
# studio_tools/creators/checklist.py
from nyx.api.v1.editor_utils import UtilObjectCreator


class ChecklistCreator(UtilObjectCreator):
    """Creates a checklist where the user clicked."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id the creator is registered with."""
        return "studio.create_checklist"

    @classmethod
    def get_util_object_type_id(cls) -> str:
        """str: type id of the util object created."""
        return "studio:checklist"
```

and the plugin lists it:

```python
plugin.contents.util_objects = [ChecklistObject]
plugin.contents.graphics_objects = [GraphicsChecklist]
plugin.contents.creators = [ChecklistCreator]
```

The name, icon and description of the menu entry come from the util object type
(`get_type_display_name()`, `get_type_icon()`, `get_description()`). To change how the object
starts, override a hook:

| Hook | Default |
| --- | --- |
| `get_creation_geometry(context)` | `(context.position, None)`: where the user clicked, at the default size of the type. Return a size to choose it. The group returns the area around the selected nodes. |
| `get_creation_properties(context)` | `None`: the defaults of the type. Return values as listed by `serialize_properties()` to start with more, for example the first items of a checklist. |

## A creator that creates anything

`Creator` is the base for everything else. Implement three classmethods and, if you want, the
others:

```python
from nyx.api.v1 import CoreNodes, commands
from nyx.api.v1.editor_utils import Creator


class ReadmeNodeCreator(Creator):
    """Creates an empty node named readme, where the user clicked."""

    @classmethod
    def get_type_id(cls) -> str:
        return "studio.create_readme"

    @classmethod
    def get_display_name(cls) -> str:
        return "Readme node"

    @classmethod
    def create(cls, context):
        command = commands.CreateNodeCommand(
            stage=context.stage,
            type_id=CoreNodes.EMPTY,
            parent_node=context.scope_node,
            position=context.position,
            name="readme",
        )
        context.stage.push_command(command)
        return command.result_node
```

| Member | Purpose |
| --- | --- |
| `get_type_id()` | **You implement it.** Unique id of the creator, the key in the registry. |
| `get_display_name()` | **You implement it.** Text of the menu entry. |
| `create(context)` | **You implement it.** Create the thing with commands and return it (a node or a util object) so the editor selects it, or return `None`. Raising `NyxCommandValidationError` shows a warning and changes nothing. |
| `get_icon()` | Resource path of the icon, `:/icons/plus` by default. |
| `get_description()` | Tooltip of the entry, empty by default. |
| `is_available(context)` | Whether the entry is enabled. By default it is disabled in a scope that can't take new objects (the contents of a reference). |

## The context

`create` and `is_available` get a `CreatorContext`:

| Field | Holds |
| --- | --- |
| `stage` | The stage being edited. Push commands to it. |
| `scope_node` | The node whose contents are drawn. New nodes and util objects go in it. |
| `position` | Where the user right-clicked, in scene coordinates. |
| `selection_rect` | The area taken by the selected nodes, `None` if no node is selected. |
| `graph_editor` | The editor of the graph, for anything else you need. |

## Registering

- `NyxPluginContents.creators` takes classes with a `get_type_id` **classmethod**. The registry
  skips (and logs) an id that is already registered.
- The order of the list is the order of the menu. Plugins are registered in discovery order, so
  the creators of the standard library come first.
- Creators are dropped and registered again from the enabled plugins whenever the plugin
  content is rebuilt.
- Plugin creators have no keyboard shortcut. The note and the group keep the shortcuts of
  their own actions (Ctrl+G for a group).
