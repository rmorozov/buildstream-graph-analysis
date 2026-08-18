# UX-77: the installed CLI cannot reach its own capture tools

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** —

## Motivation

Every capture/conversion alias — `bga wrap`, `bga extract`, `bga capture`,
`bga run-context`, all twelve of them — dispatches by importing a module
from the `tools` package (`bga/tools_dispatch.py:127`,
`importlib.import_module("tools.…")`). But `pyproject.toml` packages only
`bga*` (`[tool.setuptools.packages.find] include = ["bga*"]`), so `tools`
is never installed, and a console-script entry point does not put the
current working directory on `sys.path`. Reproduced in a clean venv
(`pip install -e .`, BuildStream 2.7.0 present), **from the repo root**:

```
$ bga capture run --wrapped-log /tmp/p1.log --trace-opens \
    examples/06-macro-micro-optimization /tmp/p2.json -- bst build all.bst
...
ModuleNotFoundError: No module named 'tools'
```

A raw traceback, not a handled error — and it is the very first command
`README.md`'s "Use it on your real project" section tells a new user to
run. The entire documented real-project workflow (`README.md:154-156`,
`docs/cli.md`'s "One entry point" section, `docs/real-project-guide.md`)
is broken for anyone who installed the package.

Nothing ever caught this because every consumer avoids the alias path:
CI invokes `python3 -m tools.<module>` with an explicit `PYTHONPATH`
(`.github/workflows/real-project-capture.yml`), pytest runs from the repo
root (where `python -m` semantics differ), and older pip versions'
legacy editable installs put the whole repo root on `sys.path` as a side
effect — which is presumably how every audit round to date ran it.
Whether `bga extract` works today depends on *which pip installed it*.

## Required Fix

Make the dispatch work from any install:

1. Either move `tools/` under the package (e.g. `bga/_tools/`, keeping
   `python3 -m tools.<module>` as thin re-export shims for compatibility
   with CI and docs), or add `tools*` to the packaged set. Moving is the
   honest fix — `tools` is not an optional convenience, it is the
   documented capture path.
2. `bga/tools_dispatch.py` should fail with a handled, actionable error
   (exit 2, one sentence) if the module genuinely cannot be imported,
   never a raw traceback.

## Out of Scope

- Restructuring the tools themselves or their CLIs.
- The `--invocation-log` capture-defaults problem (UX-80).

## Acceptance Test

In a fresh venv, `pip install <built wheel>` (not editable, not from the
repo directory), `cd` to an empty directory, and run:

```
bga extract --help
bga capture --help
```

Both must exit 0 and print usage. A CI step performing exactly this
(build wheel → install in clean venv → run an alias from an empty cwd)
must be added so the packaging cannot regress silently.
