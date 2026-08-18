# UX-77: the installed CLI cannot reach its own capture tools

**Priority:** High | **Status:** 🟢 Done | **Depends on:** —

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

## Fix Implemented

Reproduced first, exactly as filed — a built wheel, a clean venv, an
empty working directory:

```
$ /tmp/pkgvenv/bin/bga extract --help
...
ModuleNotFoundError: No module named 'tools'
```

After: all **15** aliases (`analyze`/`compare`/`correlate` plus the
twelve dispatched ones) exit 0 from that same empty directory.

Three things were needed, not one:

1. **`tools*` is packaged** (`[tool.setuptools.packages.find]`), and
   `tools/native_trace/*.c` with it — `hook.c` is compiled at capture
   time and is not a Python module, so without `package-data` Plane 2
   would have installed broken in a way no `--help` reveals.
2. **`pyyaml` moved to base dependencies.** Found *by* the new handled
   error, not by inspection: with `tools` importable, `bga capture --help`
   still failed, because the tracer imported `yaml` at module scope and
   PyYAML was in the `dev`/`bst` extras only. The import is now lazy —
   matching the three other `yaml` call sites in `tools/`, which already
   were — and PyYAML is a base dependency, because `bga extract` and
   `bga capture --trace-opens` genuinely read BuildStream YAML.
3. **A handled error** with exit 2 and one actionable sentence, for
   whatever partial install remains possible.

### A new CI job, because the old ones structurally could not catch this

`packaging` builds a wheel, installs it into a clean venv, and runs every
alias from `/tmp/empty`. The `cd` is the load-bearing part: a
console-script entry point does not put the working directory on
`sys.path`, which is exactly why running from the repo root hid this from
every prior round.

### One deviation from the Required Fix, recorded rather than silent

The task preferred moving `tools/` under the package with re-export
shims, calling packaging it the lesser option. Packaging is what shipped.
The move touches **49 test import sites** and **41 documented
`python3 -m tools.<module>` invocations**, and the defect being fixed is
that the front door crashes — a large mechanical refactor is a poor
carrier for that. The cost is real and is written into `pyproject.toml`
where the decision lives: `tools` is a generic top-level name to occupy
in `site-packages`, and if this project is ever published the namespaced
move is the right follow-up.

Tests: 2 new in `tests/unit/test_tools_dispatch.py` (every alias resolves
to an importable module with a `main()`; an unimportable one is exit 2
and a sentence, not a traceback). Suite: 1112 → 1114.

## Verification Log

Fixed 2026-08-18. The before/after was a real `python -m build` wheel
installed into a real venv (`python3 -m venv`), invoked from an empty
directory — the same procedure the new `packaging` CI job runs.
