# UX-635: the environment inventory stops at one namespace

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-630 (which built the inventory and the guard) | **Found by:** round 86, measured by UX-630's track and left unfiled by it | **Serves:** anyone driving a Plane 2 or Plane 3 capture by hand, or debugging one that behaved unexpectedly | **Topic:** docs

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
