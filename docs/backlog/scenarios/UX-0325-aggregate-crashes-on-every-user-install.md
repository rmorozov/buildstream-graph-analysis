# UX-325: --aggregate crashes on every user install

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-234 (the feature), UX-203 (the CI installed-mode lesson this extends) | **Serves:** R1, R5, R7 | **Topic:** store

## Motivation

Round 45's stranger walk, friction 2: `bga snapshot --aggregate` —
named in `docs/README.md` as one of the commands to know — dies
with `ModuleNotFoundError: No module named 'tools.bga_snapshot'`
on a plain `pip install` (bga/store_aggregate.py:506 imports
`from tools.bga_snapshot import store_listing`). The import only
resolves in a contributor checkout, so the feature has never run
once in user mode — the exact class 47a3f83/UX-203 was about (the
wheel ships differently than the checkout), recurring because
CI's installed-mode exercise never grew past the commands it was
written for.

## Required Fix

The import moves inside the package (or `store_listing` does);
and the guard that keeps the class dead: CI's installed-mode job
runs **every documented command** at least to a successful parse
plus one real invocation for those that read fixtures —
mechanically derived from the docs' command inventory (the UX-322
table), not a hand-list that ages.

## Out of Scope

- Restructuring tools/ vs bga/ beyond this import (UX-313's
  boundary questions live elsewhere).

## Acceptance Test

In a scratch venv with plain `pip install .`: `bga snapshot
--aggregate` on a fixture store emits `store-aggregate/v1`
(exit 0); the CI job's command sweep is derived from the
documented inventory and fails if any documented command errors
at parse or on its fixture invocation (mutation: reintroduce the
tools. import → the sweep reds in installed mode).

## Outcome (round 47, 2026-08-27) — 🟢 Done

### The finding was one site; there were three

The filing named `bga/store_aggregate.py:506`. Before fixing it, every
`bga/` module was swept for the same shape and each candidate was
**run** in a scratch venv built with a plain `pip install .`:

```text
BROKEN  store_aggregate.read  -> tools.bga_snapshot          ModuleNotFoundError: No module named 'tools'
BROKEN  hostinfo.collect      -> tools._run_context_common   ModuleNotFoundError: No module named 'tools'
BROKEN  cli._element_completer -> tools.bst_native_build_tracer  ModuleNotFoundError: No module named 'tools'
```

All three now go through `bga.tools_dispatch._import_tool`, which tries
`tools.X` (a checkout) and then `bga._tools.X` (a wheel). In the same
venv, after:

```text
store_aggregate resolver: bga._tools.bga_snapshot
cli resolver:             bga._tools.bst_native_build_tracer
```

### The acceptance test, run

Scratch venv, `pip install .`, a fixture store of three measured
snapshots, invoked from a directory that is not the checkout:

```text
$ bga snapshot --aggregate
Store: …/ux325store
  3 measured run(s) of 3 snapshot(s)
  unknown cpu_model · 8 cores · 16000 MB - 3 run(s)
    Duration: min 2.0s, median 3.0s, p95 4.0s, max 4.0s (MAD 1.0s, n=3)
exit=0

$ bga snapshot --aggregate --format json | jq -r .schema
store-aggregate/v1
```

### Why the class kept recurring, and what replaced the list

`UX-77`, `UX-203`, `UX-325`: three shipments of one defect. The import
is the symptom. The cause is that CI's installed-mode exercise was a
**hand-written list of nineteen aliases**, written in round 12,
`--help`-only, never grown. It could not have found this one twice
over: `--aggregate` is a *flag* on a command, and `--help` never
reaches the import.

`tests/installed_command_sweep.py` derives the list instead. Measured
against the wheel, versus what the step it replaced did:

```text
                              hand-list (round 12)   derived (UX-325)
commands parsed                              19             31
  of which documented                        19             21
commands really invoked                       0             18
parse-only, with a written reason             –              3
```

The three parse-only are `capture` (needs `bst` and a sandbox — the
`installed-capture` job below is its exercise), `baseline` (needs a git
remote carrying published capture refs), and `wrap` (its only argument
shape is `-- bst …`; its non-`bst` path raises rather than refusing,
which is `UX-326`'s subject and not this sweep's to assert).

### The two guards are deliberately different in kind

The sweep is behavioural and cannot reach everything: `hostinfo.collect`
is called only from the extraction path, and `_element_completer` only
under tab completion, so **neither of the other two sites is reachable
from any command a CI runner can invoke**. Saying "the sweep covers it"
would have been false for two of the three.

So `tests/unit/test_no_absolute_tools_import_survives.py` holds the
static half: an AST walk over every module under `bga/`, failing on any
`import tools…` or `from tools… import …`. It is an AST walk and not a
grep because `_import_tool("tools.bga_snapshot")` passes the same text
as a *string*, and that one is the fix. The same file holds the sweep's
coverage honest in both directions and keeps parse-only a minority.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|----|---|
| W1 | reintroduce `from tools.bga_snapshot import store_listing` in the **installed** copy | the sweep, on `bga snapshot --aggregate`, with the traceback quoted |
| W2 | the same import, in the source tree | `test_no_module_under_bga_imports_tools_absolutely` |
| W3 | delete `snapshot`'s entry from `invocations()` | the documented-but-not-swept clause, and the named `--aggregate` clause |
| W4 | remove the `bga view` row from the architecture's table | the swept-but-not-documented clause — the other direction |

### Deviation from the Required Fix

- The Required Fix named one import; **three** were moved, because the
  other two carry the identical defect and were proved broken in
  installed mode by running them, not by reading them.
- It asked for "every documented command … plus one real invocation for
  those that read fixtures". Eighteen of twenty-one are really invoked;
  the three that are not carry a written reason and a guard keeps them
  a minority. A hand-list with no reasons is what this replaced, so an
  exemption that has to be argued in writing is the point rather than a
  shortfall — but it is a judgement, and it is the only one here.
- The sweep runs in CI's packaging job against a wheel, not in the
  local suite: reproducing it locally means building a venv, which is a
  minute per run. What the local suite holds is the static guard.
