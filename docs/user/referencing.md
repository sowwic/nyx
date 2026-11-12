# Referencing stages

A **Reference** node (`core:reference`) stands for another stage file. Use it to build a
graph out of smaller, reusable stages: a "publish a file" stage that you drop into many
pipelines, a shared setup, a sub-graph one person maintains for the team.

## What a reference is

The top node of the stage file you point to (its root, `/stage`) has components: the
inputs and outputs the author of that stage chose to expose. The Reference node gets
the same components. The nodes **inside** the source file become its children.

```text
build_scene.nyx                         main.nyx
/stage                                  /stage
 ├ components: scene_path, result        ├ Flow Start ─▶ reference ─▶ Log
 ├ Flow Start ─▶ Open ─▶ Export          │               source = build_scene.nyx
 └ ...                                   │               scene_path = "a.ma"
                                         │               result  ───────────────┘
                                         └ (Open, Export, ... as locked children)
```

When the stage runs, the Reference node behaves like any node that contains children: it
runs, then the crawler runs the inside from its Flow Start node, then the flow
continues to the next sibling.

## Using a reference

1. Create a Reference node.
2. Set its **source**: a path to a `.nyx` file. A relative path is relative to the
   folder of the stage file the reference is in, or, for a reference inside another
   reference, to the folder of that source file. An unsaved stage can only use absolute
   paths.
3. The components of the source stage appear on the node. Give them values or link
   them like components of any node.

The node's subtitle shows the file name, or the reason the source could not be loaded
(missing file, not a `.nyx` file, unreadable, no source set).

## What you can and can't change

A reference is a *view* of its source, so the source stays in charge of its shape:

| You can | You can't |
| --- | --- |
| Set the values of its components | Add, remove or rename components |
| Link to and from its components | Change the datatype of a component |
| Deactivate the node | Edit, add or delete the nodes inside |
| Look inside the node | Link to or from nodes inside from the outside |

To change what is inside, open and edit the source stage itself.

## Saving and reloading

- The stage file stores the reference node's own settings: the source path, the values
  you set on its components, and links to the outside. It does **not** store the nodes
  inside. They are loaded from the source again every time the stage is opened, so edits
  to the source show up in every stage that references it.
- Use **Reload reference** from the node's context menu after editing its source while
  the stage is open. Reloading keeps the values you set and the links to its
  components. The context menu of a reference node can also open the source stage in
  the editor.
- A reload **clears the undo history** of the stage, because it is not a change the
  history could undo.
- If the author of the source renames a component, the reference recognizes it
  (it matches components by their identity first, then by name) and keeps your value and
  links. A component that was removed from the source, or whose type changed, stays on
  the node marked as *invalid* with the reason, so you can see which links to remove.
  If the source can't be loaded, all components stay with the error as the reason and
  nothing is lost.

## Rules

- A stage **cannot reference itself**, directly or through another reference.
- The source must be a `.nyx` file that exists.
- A source cannot have a component named `source`, since the reference node uses that
  name for its own source setting. It is left out, with a warning in the log.
- References can be nested: the source may contain references of its own.

## Tips

- Treat the components of a stage you plan to reference as its API. Give them clear
  names and descriptions, and mark outputs as readable and inputs as writable.
- Keep referenced stages in the same repository as the stages that use them and use
  relative sources, so the whole set can be moved or checked out elsewhere.
- Run a referenced stage in [batch mode](batch.md) on its own to test it.
