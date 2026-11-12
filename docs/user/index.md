# User Guide

Nyx is a nodal execution graph. You build a **stage** out of nodes, connect their
components with links, and run it, in the editor or from the command line.

## Start here

1. Install Nyx and open the editor, see the [README](https://github.com/sowwic/nyx#installation).
2. Read [How a graph executes](execution.md) to understand flow links, data links and
   evaluation. Everything else builds on it.

## Pages

| Page | What you learn |
| --- | --- |
| [How a graph executes](execution.md) | How the flow moves from node to node, what a node does when it runs, how values are evaluated and pulled. |
| [Datatypes](datatypes.md) | The built-in datatypes, which components can be linked, and how values are converted. |
| [Link pins](link-pins.md) | Routing a link through dots you place on it. |
| [Built-ins](stdlib/index.md) | A page for every component, node and utility object of the standard library. |
| [Referencing stages](referencing.md) | Reusing a stage file inside another stage. |
| [Remote nodes and the bridge](remote-nodes.md) | Running code in Maya, Blender or any other Python process. |
| [Running stages in batch mode](batch.md) | Running stages without the editor, exit codes, CI. |
| [Customization](customization.md) | The user config file and every option in it. |

Looking to extend Nyx with your own nodes? See the [Developer Guide](../dev/index.md).

## Vocabulary

| Term | Meaning |
| --- | --- |
| Stage | A graph document, saved as a `.nyx` file. |
| Node | A box in the graph. Can contain other nodes. |
| Component | A plug on a node: a value, a flow connection, a script, ... |
| Link | A connection between two components. |
| Pin | A dot on a link that the link is drawn through, see [Link pins](link-pins.md). |
| Flow | The path of execution, drawn with white pentagon plugs. |
| Scope | The inside of a node. The stage root is the outermost scope. |
| Util object | A note or a group. Organizes a graph, doesn't execute. |
| Plugin | A package providing nodes, components, datatypes and other content. |
| Bridge | The link to external processes, see [Remote nodes](remote-nodes.md). |
