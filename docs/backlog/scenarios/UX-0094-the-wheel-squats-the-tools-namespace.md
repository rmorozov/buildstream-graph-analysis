# UX-94: the wheel ships a top-level `tools` package

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-77 (done) | **Topic:** cli

## Motivation

UX-77's fix chose the packaging option its own task file argued
against: `pyproject.toml` now packages `tools*`, so the built wheel
installs a **top-level package named `tools`** into site-packages
(verified: `unzip -l dist/bga-*.whl` shows `tools/…` beside `bga/…`,
and `import tools` resolves to it in a clean venv). `tools` is about
the most generic importable name in Python; any other distribution
shipping or vendoring a `tools` top-level (they exist), or any user
project with its own `tools/` package and a sys.path that prefers
site-packages, now collides with `bga`'s internals — and pip will
happily overwrite files between two distributions that both ship
`tools/`, breaking whichever was installed first, silently.

The alias dispatch itself works from the wheel now (UX-77's acceptance
passes: `bga extract --help` from an empty directory in a clean venv,
exit 0) — the front door is fixed; this is about what it cost.

## Required Fix

Move the package under the namespace it belongs to: `bga._tools` (or
`bga.tools`), with the dispatch importing that, and thin top-level
shims kept **in the repository only** (not in the wheel) so
`python3 -m tools.<module>` keeps working for CI, the docs, and muscle
memory. The wheel then owns exactly one top-level name. `hook.c` and
other data files move with it (they already ship, so the packaging
plumbing exists).

## Out of Scope

- Renaming the modules or changing any CLI surface.
- The repo-checkout invocation style (`python3 -m tools.*` keeps
  working from a checkout via the shims).

## Acceptance Test

`unzip -l` of the built wheel lists only `bga/…` and dist-info at top
level. UX-77's acceptance still passes from that wheel (aliases from an
empty cwd in a clean venv). In the same venv,
`pip install <any package>; python -c "import tools"` fails with
ImportError (nothing squats the name). From a repo checkout,
`python3 -m tools.bst_extract_run --help` still exits 0.

---

## Resolution (round 12)

**Status:** 🟢 Done

Confirmed first — the built wheel really did list `tools/` beside `bga/`
at top level. Fixed, and with considerably less churn than the Required
Fix anticipated.

### The lighter route the task did not consider

The Required Fix proposes moving the code to `bga._tools` and leaving
re-export shims in the repo. The same end state is reachable without
moving anything, because the *repository layout* and the *installed
layout* do not have to agree:

```toml
[tool.setuptools]
package-dir = {"bga._tools" = "tools"}
```

The directory stays `tools/` in the checkout and installs as
`bga._tools`. So the 55 test imports, 34 CI invocations and 263
documented `tools/` paths all keep working untouched, no shim files
exist to drift, and the wheel owns exactly one top-level name.

**What made it possible** was one real change: the modules imported each
other by absolute name (`from tools.bst_show_to_graph import …`), which
breaks the moment the package is installed under a different name. Those
twelve imports are now relative (`from .bst_show_to_graph import …`), so
the package no longer cares what it is called. That is a genuine
improvement independent of packaging.

`bga/tools_dispatch.py` tries the installed name first and falls back to
the checkout name — both are normal states, neither is an error.

### Acceptance test

Built the wheel and ran all four criteria against it:

```text
$ unzip -l dist/bga-*.whl | ... | cut -d/ -f1 | sort -u
    bga
    bga-0.1.0.dist-info                      # (1) one top-level name

$ for a in analyze … gen-synthetic; do (cd /tmp/empty && bga "$a" --help); done
    all 16 aliases exit 0                    # (2) UX-77's acceptance still passes

$ cd /tmp/empty && python -c "import tools"
    ModuleNotFoundError: No module named 'tools'    # (3) the name is free

$ python3 -m tools.bst_extract_run --help
    exit 0                                   # (4) the checkout form still works
```

`hook.c` moved with the package and is present at
`bga/_tools/native_trace/hook.c` in the installed venv.

### Guards

- CI's `packaging` job gained a step that asserts the **built artifact**:
  the wheel's top-level entries are exactly `bga`, and nothing in the
  clean venv is importable as `tools`.
- A unit test asserts the `package-dir` mapping and that every declared
  package is under `bga.` — so a future `include = ["tools*"]` fails
  before it reaches a wheel.

### One trap worth recording

`import bga._tools` fails when run from the repository root even with
the wheel installed, because the checkout's own `bga/` shadows
site-packages. That is not a packaging bug and it is why both the CI
step and the manual check `cd /tmp/empty` first — the same reason
`UX-77`'s original job did.

### The import order is load-bearing, and CI proved it

The first version of `_import_tool` tried the **installed** name first.
That is wrong, and only an editable install can show it: an editable
install has *both* names, and importing one file under two names gives
two module objects with separate globals. `dispatch` therefore ran
`bga._tools.bst_extract_run.main` while everything else in the process —
tests patching it, callers that had imported it — held
`tools.bst_extract_run`.

Five dispatch tests failed in CI on exactly that, across all four Python
versions, and passed locally, because this container's editable install
predated the packaging change and had only one of the two names. The
local pass was the misleading result, not the CI failure.

Fixed by trying the **checkout** name first: wherever `tools` resolves at
all, every consumer agrees on one object, and the installed name is
reached only by a real wheel, where it is the only name that exists.
Verified in both layouts — editable (`dispatch` resolves
`tools.bst_extract_run`, 13 dispatch tests pass) and wheel in a clean
venv (`bga._tools.bst_extract_run`, top-level `tools` absent, all 16
aliases exit 0). Guarded by
`test_dispatch_and_the_rest_of_the_process_agree_on_one_module_object`,
which fails when the ordering is reverted.
