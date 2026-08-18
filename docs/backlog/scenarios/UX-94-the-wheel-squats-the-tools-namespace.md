# UX-94: the wheel ships a top-level `tools` package

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-77 (done)

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
