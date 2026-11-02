# UX-1356: a junctioned target reaches `bst show` without its junction

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** field report (2026-10-30) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_junctioned_target_reaches_bst_show_whole.py`

## Motivation

`bga snapshot -- bst build some_junction:my_recipe.bst` fails: the run
directory's `bst show` is called on `my_recipe.bst`. `extract_run` takes
its targets from the log's `Targets:` header, and BuildStream 2.8.1
prints `Element.name` there (`_frontend/widget.py:509`), the name inside
the junctioned project, not the qualified one typed.

## Decomposition

Input classes: a top-level target; one junction (`j.bst:x.bst`); nested
(`a.bst:b.bst:c.bst`); two junctions shipping one name; targets after a
subcommand option's value; no typed target. Journey: `bga snapshot -- bst
build j.bst:x.bst`, the run directory's `bst show`.

## Required Fix

Qualify each header name from the command the capture ran: a typed
target whose part after its last `:` is that name replaces it, in order,
so nested `a.bst:b.bst:c.bst` and two junctions shipping one name each
survive. Anything else stands as printed.

## Out of Scope

A capture whose command names no target (a wrapper script, `bga extract`
on a bare log): the header stays the only source. The log's `Pipeline`
block does print qualified names and could close it, as its own row.

## Acceptance Test

The guard, real `bst` on `tests/fixtures/bst_show_project`, building
`subproj-junction.bst:libfoo.bst`: the run's `targets` and its
`graph.json` requested target are the qualified name. Reading: this
container, bst 2.8.1.

## Outcome (2026-10-30) — 🟢 Done

**Premise:** held — the header drops the junction, measured on a real
bst 2.8.1 build in this container (bubblewrap from Ubuntu's archive).

### The gap, measured

```text
$ bst build some_junction.bst:my_recipe.bst | grep -E 'Targets|my_recipe'   # a two-project local junction
    Targets:       my_recipe.bst
      cached e5d1c063... some_junction.bst:my_recipe.bst
$ bst show my_recipe.bst
Could not find element 'my_recipe.bst' in elements directory '.../jp/elements'
```

The header is the only target source `extract_run` reads, so every
junctioned target was replayed into `bst show` by its short name.

### After

```text
$ PATH=<bst 2.8.1>:$PATH python -m pytest -q -n0 tests/unit/test_a_junctioned_target_reaches_bst_show_whole.py
6 passed in 5.59s
```

`_cmd_targets` reads every typed target; `qualify_targets` restores each
header name's junction. The real build of `subproj-junction.bst:libfoo.bst`
publishes it as both `targets` and the graph's requested target.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A1 | `extract_run` reads the header alone | 5 of 6; the real build: `bst show failed (exit 255) for targets ['libfoo.bst']` |
| A2 | the tracer's call site drops `command_targets` | `test_the_capture_hands_its_own_command_to_the_extraction` |
| A3 | `split(":", 1)` for `rsplit` | `test_nested_and_mixed_targets_keep_their_order_past_options` |
| A4 | a matched typed target is not consumed | `test_two_junctions_shipping_one_name_each_keep_their_own` |

### Deviation from the Required Fix

None. A junctioned run's `run_identity.targets` now reads qualified, so
`cache_trend`'s series key splits from older captures of the same build.
