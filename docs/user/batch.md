# Running stages in batch mode

A stage doesn't need the editor to run. The command line loads the plugins, loads the
stage, runs it once and exits with a code that tells you how it went. Use it for
scheduled jobs, render farms, build servers and anywhere else no one is there to press
a button.

## The commands

```sh
nyx stage run path/to/stage.nyx
nyx-run-stage path/to/stage.nyx         # the same, as one command
```

Both are installed with the package, and with the standalone app (see the README).

| Option | Effect |
| --- | --- |
| `--no-bridge` | Don't start the bridge server. Use it for stages without Remote nodes, or when the port is needed elsewhere. |
| `--port N` | Use port `N` for the bridge server in this run instead of the configured one. Handy when several runs happen on one machine at once. |

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The stage ran. |
| `1` | The stage failed. The log names the node that failed and the error. |
| `2` | The file doesn't exist or couldn't be loaded. |
| `130` | Interrupted with Ctrl+C. |

### What a run does

1. Starts a Qt application **without a window**. `QT_QPA_PLATFORM` defaults to
   `offscreen`, so no display is needed (servers, containers, CI).
2. Loads the config and the plugins, including those from `plugin_paths` and
   `NYX_PLUGIN_PATH`.
3. Loads the stage file. References are resolved relative to it.
4. Starts the bridge server unless `--no-bridge` is given or the config disables it.
5. Runs the stage once, from the root, following the flow as described in
   [How a graph executes](execution.md), and then shuts the session down.

The config is **read but never saved**. Nothing is written to your user config by a
batch run, so runs are safe on a machine you also use for editing.

!!! note
    A run executes the stage as it is on disk. There is no command line parameter
    for component values. Set the inputs of a batch from outside with the things a
    graph can read: environment variables (the *Get Env* function node), files, or a small *wrapper stage* that
    [references](referencing.md) the real one and sets its components.

## Running many stages

Each run is a process, so the shell does the batching.

```sh
# one after another, stop at the first failure
for stage in stages/*.nyx; do
    nyx-run-stage --no-bridge "$stage" || exit 1
done

# all of them, then count the failures
failed=0
for stage in stages/*.nyx; do
    nyx-run-stage --no-bridge "$stage" || failed=$((failed + 1))
done
echo "$failed failed"

# in parallel, four at a time
ls stages/*.nyx | xargs -P 4 -n 1 nyx-run-stage --no-bridge
```

Stages that need DCC clients and run in parallel must not share a bridge port: give each
run its own `--port`, and a Remote Client node that waits for the client it started with
Launch Process.

From Python:

```python
import pathlib
import subprocess

results = {}
for stage in sorted(pathlib.Path("stages").glob("*.nyx")):
    completed = subprocess.run(["nyx-run-stage", "--no-bridge", str(stage)])
    results[stage.name] = completed.returncode
```

## Logs

The messages go to the console and to the log file in the `logs` folder of the
[user directory](customization.md). Every executed node logs its path and how long it
took, and a failure logs the node and the exception with its traceback.
`logging_level` in the config (or `NYX_DEBUG=1`) makes it more verbose.

## In CI

The standalone app and the package both work. With the package and uv:

```yaml
- uses: astral-sh/setup-uv@v6
- run: uv sync --locked
- run: uv run nyx-run-stage --no-bridge stages/nightly.nyx
```

A non-zero exit code fails the job.

## From your own code

To drive stages from Python without a subprocess, create the application and a stage and
start its crawler, like the CLI does:

```python
from nyx.api.v1 import Stage
from nyx.application import NyxApplication

app = NyxApplication()          # needs QT_QPA_PLATFORM=offscreen without a display
stage = Stage()                 # keep the reference, nodes don't hold the stage
if stage.import_json("stages/nightly.nyx") is None:
    raise SystemExit("could not load the stage")

failed = []
stage.execution_failed.connect(failed.append)
try:
    stage.crawler.start()
except Exception:
    print("failed at", failed[0].path if failed else "the stage")
```

`stage.crawler.request_cancel()` asks a running crawl to stop. Connect to the stage
signals (`execution_started`, `execution_succeeded`, `execution_finished`,
`execution_failed`, `execution_cancelled`) to follow a run.
