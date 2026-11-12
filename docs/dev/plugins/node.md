# New node

A node is a `Node` subclass that creates its components in `setup` and does its work in
`evaluate` and `execute`.

## A complete example

```python
# studio_tools/nodes/greeter.py
from nyx.api.v1 import Node, CoreNodeComponents, CoreDatatypes


class GreeterNode(Node):
    """Flow node that builds a greeting for a name."""

    DEFAULT_NAME = "greeter"

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return "studio:greeter"

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Greeter"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return "Builds a greeting for the given name."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags, used to find the node in the palette."""
        return {"common", "text"}

    def setup(self):
        """Add the flow, the name input and the greeting output."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True   # output: the flow can leave through it
        self.flow_cpnt.writable = True   # input: the flow can enter through it

        self.who_cpnt = self.components_model.create_component(CoreNodeComponents.VALUE)
        self.who_cpnt.name = "who"
        self.who_cpnt.description = "Who to greet."
        self.who_cpnt.writable = True        # can be linked to
        self.who_cpnt.is_editable = True     # can be typed in the UI
        self.who_cpnt.is_literal = True      # text is kept as typed, not evaluated
        self.who_cpnt.set_datatype(CoreDatatypes.STRING)
        self.who_cpnt.push_value("World")

        self.greeting_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.greeting_cpnt.name = "greeting"
        self.greeting_cpnt.description = "The greeting."
        self.greeting_cpnt.readable = True   # can be the source of links
        self.greeting_cpnt.is_editable = False
        self.greeting_cpnt.set_datatype(CoreDatatypes.STRING)

        for component in (self.flow_cpnt, self.who_cpnt, self.greeting_cpnt):
            self.components_model.add_component(component)

    def execute(self):
        """Build the greeting from the pulled name."""
        who = self.who_cpnt.pull_value()
        # Not evaluated: a text result would be run as an expression otherwise.
        self.greeting_cpnt.push_value(f"Hello, {who}.", evaluate=False)
```

Register it in the plugin: `plugin.contents.nodes = [GreeterNode]`. It shows up in the
palette under the plugin's palette name.

## What a node class defines

| Member | Required | Purpose |
| --- | --- | --- |
| `get_type_id()` | yes | Unique id stored in stage files, `namespace:name`. |
| `get_type_display_name()` | yes | Name in the UI. |
| `get_description()` | no | One sentence shown in the palette. |
| `get_tags()` | no | Set of strings for searching and filtering in the palette. |
| `get_type_icon()` | no | Qt resource path of the icon. |
| `DEFAULT_NAME` | no | Address name new nodes start with. |
| `setup()` | usually | Creates the components. |
| `get_type_flags()` | no | `NodeFlag` values, see below. |
| `get_type_execution_order()` | no | `BEFORE_CHILDREN` (default) or `AFTER_CHILDREN`. |
| `get_render_options()` | no | `NodeRenderOptions` for how the editor draws the node. |

### Components in `setup`

- `components_model.create_component(type_id)` creates a component of a registered type
  (`CoreNodeComponents.VALUE`, `FLOW`, `SCRIPT`, `FILE`, `COMMENT`, or your own). It is
  not part of the node until `add_component` adds it. `add_component` makes the name
  unique among the node's components.
- The components `setup` creates are marked **built-in**: users can't delete them.
- Keep a reference on `self` (`self.who_cpnt`) to use in `evaluate` and `execute`.
  `node["who"]` also finds a component by name.
- The stdlib sets the properties before `add_component`; do the same.

| Property | Meaning |
| --- | --- |
| `readable` | The component is an output: it can be the source of links. |
| `writable` | The component is an input: it accepts a link. |
| `is_editable` | The value can be edited in the UI. |
| `is_literal` | Text is kept as typed instead of being evaluated as an expression. Use for names and paths. |
| `is_static` | Skipped when the node's components execute. |
| `set_datatype(type_id)` | Datatype of the value, see [New datatype](datatype.md). |
| `default_value`, `push_value(v)` | The value to reset to, and the current one. |
| `description` | Tooltip text. |
| `component_flags` | `NodeComponentFlag` bitmask with all of the above and `INHERITS_DATATYPE`, `INSPECTOR_HIDDEN`, `SINGLE_OUTPUT`. |

A **flow** component is what makes a node part of the execution chain: readable means
the flow can continue through it, writable means the flow can arrive through it.

## When your code runs

For each execution of the node, in this order (see the user guide, [How a graph
executes](../../user/execution.md)):

1. `pre_execution_hook()`
2. `evaluate_components()`, which evaluates every component value,
3. **`evaluate()`**: decide things from the evaluated inputs. Branch sets which flow output
   is active here.
4. `execute_components()`, which runs components like Script,
5. **`execute()`**: the node's work.
6. `post_execution_hook()`

Raise any exception to fail the node: it is logged, the node is marked as failed and the
run stops. Write results with `push_value(value, evaluate=False)` so strings aren't run
as Python expressions.

Read inputs with `pull_value()`. It follows an input link (and casts to the
component's datatype) or returns the component's own value. It never runs the node on the
other end of the link, so producers must come earlier in the flow.

## Reacting to edits

`on_component_edited(component)` is called when a component's value is edited or linked in
the editor. Branch uses it to refresh its active outputs, so the editor shows the right
path before a run:

```python
def evaluate(self):
    chosen = bool(self.value_cpnt.pull_value())
    self.flow_out_true.is_active = chosen
    self.flow_out_false.is_active = not chosen

def on_component_edited(self, component):
    if component is self.value_cpnt:
        self.evaluate()
```

## Containers and scopes

Nodes can contain other nodes. The children of a node run from the node's **Flow Start**
child, while the node's *scope* is open. A node that wants to give something to its
children overrides `enter_scope`:

```python
from nyx.api.v1 import NodeExecutionContext

def enter_scope(self, context: NodeExecutionContext):
    connection = open_connection()
    context.provide(connection)                    # children find it by type
    context.add_cleanup(connection.close)          # runs when the scope ends, even on failure
```

Children use `self.stage.crawler.context.find(Connection)` (or `.require(...)`, which
raises `LookupError` when nothing is provided). Remote Client and Launch Process work like
this.

A node that runs the chain behind one of its flow outputs more than once (a loop) calls
`self.stage.crawler.run_flow_branch(flow_component)`. Use `crawler.wait_for(func, ...)` for
anything that blocks, so the UI stays alive and the run can be cancelled.

## Node flags

Return flags from `get_type_flags()`, adding to the parent's (`super()` first):

| Flag | Effect |
| --- | --- |
| `NodeFlag.LOCKS_CHILDREN` | Nodes inside can't be changed or linked to from outside. Used by Reference. |
| `NodeFlag.LOCKS_STRUCTURE` | Components can't be added, removed, renamed or given another datatype. |

## Saving and loading

A node is saved with its name, position, active state, execution order, components, child
nodes, util objects and links. On load Nyx creates the node from its type id, which runs
`setup`, and then restores the saved components over the ones `setup` made. Consequences:

- `setup` must be **deterministic** and create the same built-in components every time.
- State you want to keep must live in components (the value of a component is saved), not
  in Python attributes. Attributes are lost on load. Reset anything per-run in
  `pre_execution_hook`.
- If the type id of a node isn't registered when a stage is opened (the plugin isn't
  loaded), the registry logs an error naming the id. Keep ids stable.
- For nodes that get their content from elsewhere (like Reference) override
  `serialize_contents` and `deserialize_contents`.

## Subclassing an existing node

A node class can extend another. Remote Action is meant for it: a subclass adds components
and overrides `build_script`, `build_args` and `handle_response`, and leaves `execute`
alone, so a DCC plugin can offer a node with its own script and arguments without any bridge
code.
