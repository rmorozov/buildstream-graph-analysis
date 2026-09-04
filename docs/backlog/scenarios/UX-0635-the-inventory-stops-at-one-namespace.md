# UX-635: the environment inventory stops at one namespace

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-630 (which built the inventory and the guard) | **Found by:** round 86, measured by UX-630's track and left unfiled by it | **Serves:** anyone driving a Plane 2 or Plane 3 capture by hand, or debugging one that behaved unexpectedly | **Topic:** docs

## Motivation

`UX-630` documented every `BGA_*` name and wrote a guard that scans
`bga/` and `tools/` for them. Its Acceptance Test scoped it to that
prefix, and one namespace over there is a second family the same size:

```text
$ grep -o 'BST_TRACE_[A-Z0-9_]*' -r tools/ | sed 's/.*://' | sort -u | wc -l
21
$ grep -c 'BST_TRACE_[A-Z_]*' tools/native_trace/bwrap_shim.py
26
$ grep -rln 'BST_TRACE_' docs/ --include=*.md \
    | grep -v backlog | grep -v audits
(nothing)
```

Twenty-one names, none documented anywhere a reader looks. They are
not all the same kind: `BST_TRACE_OPENS`, `_SPINE`, `_NO_INJECT` and
`_DIAGNOSTICS` are things a person driving a capture by hand sets;
`_REAL_BWRAP`, `_BIND_SRC/_DST`, `_PRELOAD_SO` are the shim's internal
plumbing; `_SPINE_FAIL_SEIZE`, `_SPINE_FAIL_CONT_AT` and
`_SPINE_SELFTEST` exist so a test can drive a failure path.

The inventory's own guard cannot see any of them, so the surface it
guards is exactly as wide as the prefix somebody typed into it — which
is the shape `UX-630` closed for `BGA_*` and left open one namespace
over.

## Required Fix

The scan reads a **set** of prefixes rather than one, `BST_TRACE_*`
joins it, and the guide's table gains a section for them with the three
kinds above distinguished — a reader must be able to tell "you may set
this" from "the shim sets this for you" from "a test sets this".

Whether the system variables `bga` merely consumes (`TMPDIR`,
`XDG_CACHE_HOME`, `LD_PRELOAD`, `PYTHONPATH`) belong in the same table
is the item's one open question: they are not this project's names, and
a table that lists them is describing the platform. Decide it, do not
inherit it.

## Out of Scope

- Turning any of these into flags — declined: `UX-630` argued that for
  `BGA_RATE` against `UX-158`'s measured 45-line `--help` cap, and the
  same cap applies here with less reason to spend it.
- `BGA_TIER_ANY`, written and never read — that is its own defect and
  its own row when somebody files it, not this table's problem.

## Acceptance Test

A twenty-second `BST_TRACE_*` name added to `bwrap_shim.py`, reddening
the inventory guard by name.

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise held, count exact: 21.** Added to the round at the
repository owner's request rather than left for the next one.

### The gap, measured

```text
$ git grep -oh 'BST_TRACE_[A-Z0-9_]*' -- bga tools | sort -u | wc -l
21
$ git grep -rln 'BST_TRACE_' docs/ --include=*.md \
    | grep -v backlog | grep -v audits
(nothing)
```

### After

`PREFIXES = ("BGA_", "BST_TRACE_")`, and `NAME` is built from it. The
guide's section gains three tables, because the 21 are not one kind:

```text
what you may set, driving a capture by hand    7
what the capture path sets for you            10
what a test sets to reach a failure path       4
```

The system variables `bga` merely consumes (`TMPDIR`, `LD_PRELOAD`,
`XDG_*`, `PATH`, `PYTHONPATH`) are **declined**, in the guide and in
the constant's comment: they are not this project's names, and a table
that listed them would describe the platform rather than the tool.

### The guard of mine that did not discriminate

**`C2` — dropping `BST_TRACE_` from `PREFIXES` came back green.**
`_rows()` built its row pattern from `NAME.pattern`, so narrowing the
population narrowed the *parser* too: the guide's 21 rows stopped being
parsed as rows, both sides shrank together, and every clause passed on
a population it had quietly halved.

That is this round's own thesis committed by the item that names it.
The fix is `ROW_NAME`, a pattern for any shouting name, derived from
nothing the scan uses — so a narrowed `PREFIXES` leaves those rows
parsed and unmatched, and the stale-row clause reddens.

### Mutations verified red and reverted (3, plus one that did not apply)

| # | mutation | reddened |
|---|---|---|
| C1 | a 22nd `BST_TRACE_*` name in `spine.c` — the Acceptance Test | `..._every_name_in_the_tree_has_a_row`, 1 failed 3 passed |
| C2 | `PREFIXES = ("BGA_",)` | `..._every_row_names_something_the_tree_still_has` — **green before the fix above** |
| C3 | `BST_TRACE_ARGV_MAX`'s row cites `spine.c`, which exists and does not name it | `..._each_row_cites_a_file_that_carries_the_name` |

`C1`'s first attempt did not apply — the `sed` did not match the line —
and came back green. Recorded as "did not apply", not as a weakness:
`UX-634`'s `N4` was the same, twice in one round.

### Deviation from the Required Fix

None. The Required Fix asked for the prefix set, the three kinds
distinguished, and the system-variable question *decided rather than
inherited*; all three shipped. `ROW_NAME` is beyond it, and is there
because falsifying the change found the hole.
