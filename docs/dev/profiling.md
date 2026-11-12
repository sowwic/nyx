# Profiling

Nyx has a small profiling helper in `nyx.utils.profiling`. It combines two things:

- a **timer** that is always on and cheap: the decorated function logs how long it took,
- a **call profiler** (`cProfile`) that is only on when asked for, and writes a file you
  can inspect with `snakeviz`.

## The decorator

```python
from nyx.utils.profiling import profile

@profile()
def rebuild_everything():
    ...

@profile(name="Stages imported", text="{name} in {seconds:.4f}s")
def import_stages(paths):
    ...
```

| Argument | Meaning |
| --- | --- |
| `name` | Label used in the message and available as `{name}`. Defaults to the function name. |
| `text` | Format of the log message, with `{name}` and `{seconds}`. Defaults to `"{name}: {seconds:.4f}s"`. |

The timing message is written at `INFO` level by the `NyxProfiler` logger, on every
call, with or without profiling. The decorator is applied to loading plugins
(`NyxPluginLoader.load_plugins_from_paths`), initializing them
(`NyxPluginManager.initialize_plugins`) and importing stages in the editor
(`editor/utils/io.py`), so the log of every start shows what they cost.

## Turning the call profiler on

Set `NYX_PROFILING` to a number other than `0` (use `1`). The value is read as an integer
when Nyx is imported, so words such as `true` are not accepted.

```sh
NYX_PROFILING=1 nyx
NYX_PROFILING=1 nyx stage run path/to/stage.nyx
```

Each decorated call then runs under `cProfile`, and its statistics are saved to

```text
<user directory>/profiling/<function name>_profile.pstats
```

(see [Customization](../user/customization.md) for the user directory). The log prints
the `snakeviz "<file>"` command to open it. A later call of the same function overwrites
the file.

Nested decorated calls in the same thread are not profiled twice: the outermost call owns
the profiler, and inner functions are only timed.

## Viewing the results

```sh
make pstats                       # opens the profiling folder with snakeviz
snakeviz ~/.config/nyx/profiling/initialize_plugins_profile.pstats
python -m pstats ~/.config/nyx/profiling/initialize_plugins_profile.pstats
```

`make pstats` and the log hint call `snakeviz`, which is not a dependency of the project.
Install it into your environment (`uv tool install snakeviz`, or `pip install snakeviz`).

## Profiling something new

1. Decorate the function with `@profile()`.
2. Run with `NYX_PROFILING=1`, do the operation, and open the `.pstats` file.
3. Remove the decorator again if the function is a hot path: the timer is cheap, but it
   logs at `INFO` on every call.

To profile a whole stage run without editing any code, use `cProfile` directly:

```sh
uv run python -m cProfile -o run.pstats -m nyx stage run stage.nyx
```

## Other tools for finding slowness

- `NYX_DEBUG=1` logs at debug level. Every executed node logs its path and how long it
  took (`Executed in 0.0123: /stage/loop/log`).
- The config option `editor_widgets.graphics_stage.viewport_debug_overlay` (also an
  action in the editor) draws performance numbers over the graph view.
- `editor_widgets.graphics_stage.nodes.hover_diagnostics` shows the model roles as a
  tooltip, useful when a value looks wrong.
