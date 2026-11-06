# nyx

![Tests](https://github.com/sowwic/nyx/actions/workflows/unit_tests.yml/badge.svg)
![Code](https://github.com/sowwic/nyx/actions/workflows/code_quality.yml/badge.svg)

 Python execution graph

## Command line

```sh
nyx                          # open the editor
nyx stage run path/to/stage.nyx   # run a stage without the editor
nyx-run-stage path/to/stage.nyx   # the same, as one command
```

`stage run` loads the plugins, starts the bridge server (so stages with Remote Client
nodes can reach Maya, Blender, ...) unless `--no-bridge` is given, and runs the stage
once. `--port N` replaces the configured bridge port for the run. The config is read
but never saved.

Exit codes: `0` the stage ran, `1` it failed (the log names the node), `2` the file was
not found or could not be loaded.

