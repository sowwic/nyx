# Components

A component is a plug on a node. Nodes are made of them, and you can add them to a node yourself.

| Name | What it does |
| --- | --- |
| [Comment](comment.md) | Static text for notes. Does not take part in execution. |
| [Flow](flow.md) | Connects the execution flow from one node to the next. |
| [Value](value.md) | Holds a typed value that can be edited, linked to other components or pulled by them. |
| [Script](script.md) | Runs a python file or a module entry point when the node executes. |
| [Remote Script](remote-script.md) | Names a python file or a module entry point to run in an external process, instead of in the application. |
| [File](file.md) | Holds the path of a file, typed or picked with a file dialog. |
| [Object Path](stage-object-path.md) | Holds the path of a node or component in the stage and resolves it to the object. |
