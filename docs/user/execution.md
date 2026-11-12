# How a graph executes

This page explains what happens when you run a stage: in which order nodes run, what
a node does when it runs, and how values travel between components.

## The pieces

| Piece | What it is |
| --- | --- |
| **Stage** | The document. It holds one root node, `/stage`, and the undo history. A stage file has the extension `.nyx`. |
| **Node** | A box in the graph. It has components, and may contain other nodes (its *children*). Every node is addressed by a path such as `/stage/loop/log`. |
| **Component** | A plug on a node: a value, a flow connection, a script, a file path, a comment. A component is *writable* (accepts a link into it), *readable* (can be the source of links), or both. |
| **Link** | A connection from a readable component to a writable one. |
| **Scope** | The inside of a node. The root node is the scope of the whole stage; a node containing children is the scope of those children. |

There are two kinds of links, and they do different jobs:

- **Flow links** join *flow components* (white pentagon plugs). They say *which node runs
  next*. They carry no data.
- **Data links** join all other components. They say *where a value comes from*.

## Execution flow: from node to node

Execution does not run every node in the stage. It follows the flow links.

1. **Each scope has a Flow Start node.** The crawler looks for the Flow Start child of
   a scope and begins there. A scope without a Flow Start node runs none of its children.
2. **Flow follows the flow components.** After a node has run, the crawler looks at
   the node's flow components that are readable (outputs) and *active*, and runs the
   node each of them is linked to. Those nodes are siblings: a flow link can only join
   nodes in the same scope, anything else is an error.
3. **A node's children run with the node.** When the crawler reaches a node that contains
   other nodes, it also runs the inside of it, from the Flow Start node of that scope.
   By default the node itself runs first and then its children
   (`BEFORE_CHILDREN`); a node can be set to run after its children
   (`AFTER_CHILDREN`).
4. **The scope is finished before the flow moves on.** The next sibling runs only after
   the node and everything inside it are done. The order is depth first.

```text
/stage
 ├─ Flow Start ──▶ Branch ──true──▶ Log "yes" ──▶ Container
 │                    └────false─▶ Log "no"         ├─ Flow Start ──▶ Log "inside"
 │                                                    └ ...
```

If `Branch` picks `true`, the order is: Flow Start, Branch, Log "yes", Container,
Flow Start (inside), Log "inside". Log "no" never runs.

### Active and inactive

Two switches decide whether something takes part:

- A **node** can be deactivated. An inactive node is skipped, and so the flow stops
  there.
- A **flow component** can be inactive. Before a node is evaluated all its flow outputs
  are active. Nodes that make a decision switch some off while they evaluate:

| Node | Behavior |
| --- | --- |
| **Branch** | Activates `true` or `false` depending on its `condition`. |
| **Sequence** | Several outputs are active at once. Each is followed completely, depth first, one after another. |
| **For Loop**, **For Each Loop**, **While Loop** | Run the chain behind their `loop_body` output again and again, then continue with `completed`. |

A decision is made *after* the node is evaluated, never guessed ahead of time. This is
also what the editor shows when it animates the links of the execution chain.

### Visited once

A node runs at most once per run. If two paths converge on a node, or the links form
a cycle, the node is not run again and a warning goes to the log. Loop nodes are the
way to repeat: they run their body chain several times and reset what was
visited inside it each time.

### Scopes can provide things to their children

Because the inside of a node runs while the node's scope is open, a node can hand
something to the nodes inside it, and have it cleaned up when they are done, however
they end. This is how *Remote Client* gives its connection to the *Remote Action*
nodes inside it, see [Remote nodes](remote-nodes.md).

## What happens when a node runs

For one node the crawler calls `execution_hook`, which does this:

1. Reset the status of the node. Stop here if the node is inactive.
2. Set the status to *pending* and call `pre_execution_hook`.
3. **Evaluate the components.** For every component in order: clear its cached value,
   skip it if it is inactive, otherwise evaluate its value (see below), then call the
   component's own `evaluate`.
4. Call the node's `evaluate`. Nodes that decide something (like Branch) do it here.
5. **Execute the components.** For every component in order: skip it if it is *static*
   or inactive, otherwise call the component's `execute` (a Script component runs its
   file here).
6. Call the node's `execute`. This is the node's work: log a message, call the function,
   send code to a remote client.
7. Call `post_execution_hook`.

If anything raises, the error is logged, the node gets the *error* status, the stage
emits `execution_failed` with the node and the exception stops the whole run. The
editor marks the node and the CLI exits with code `1`. A run can also be cancelled; it
ends quietly and the scopes are cleaned up.

The stage reports the run through signals: `execution_started`, then
`execution_succeeded` and `execution_finished`, or `execution_failed`, or
`execution_cancelled`.

## Evaluation and values

Every value component holds three things: the **raw** value (what you typed or what was
pushed), the **cached** value (the evaluated result) and the **display** text.

**Evaluating** a component turns the raw value into the cached value:

- A text value is evaluated as a Python expression: `1 + 2` gives `3`, `[1, 2, 3]` gives
  a list. If it can't be evaluated, the text stays as it is. Components flagged
  *literal* (script paths, file paths, client names, ...) keep text as typed.
  Expressions run with Python's `eval`, so **a stage can run arbitrary code**: open and
  run only stages you trust, like you would a script.
- The result is cast to the datatype of the component, see [Datatypes](datatypes.md).
  A value that can't be cast makes the component *invalid*; the reason is shown on it.

**Pulling** a value is what a node does when it needs an input, with
`component.pull_value()`:

- If the component has an input link, the value comes from the source component of the
  link (`pull_value` of that component, recursively), cast to the datatype of this
  component. A failed cast is logged as a warning and the value is passed on as it is.
- Otherwise the component's own cached value is used.

!!! important
    Pulling **does not run the source node**. It reads the value the source component
    holds *now*. A value link only gives you the right value if the node that produces
    it has already run, so order nodes with flow links: the producer before the
    consumer.

This is why a graph is built from two things working together: flow links for *when*,
data links for *what*.

### Reading and writing other components

A **Setter** node pushes a value into any component, found by its path
(`/stage/counter.value`), cast to that component's datatype. A **Getter** node reads
one. They let a graph keep state across nodes without a link between them. Both run in
flow order like any other node.

### Functions and scripts

- A **function node** has one value component per parameter and one for the return
  value (`return`). When it runs it pulls the parameters, calls the function and stores
  the result in `return`.
- A **Script** component runs a Python file, or
  a `module:function` entry point, when its node executes. The script sees `nyx_node`
  and `nyx_cpnt` as globals.

## Other things worth knowing

- **The UI stays alive during a run.** The crawler lets the application process events
  regularly. Long waits (a remote client, a process) happen in a helper thread so the run
  can still be cancelled.
- **Util objects** (notes and groups) are not part of the execution. They help you
  organize a graph.
- To run a graph without the editor, see [Running stages in batch mode](batch.md).
