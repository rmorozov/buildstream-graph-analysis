# UX-719: the bottleneck fan-in and fan-out labels are swapped

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-681 (which measured it) | **Serves:** R3 reading the graph's shape | **Topic:** analysis | **Shape:** judgement | **Area:** bga/structural

## Motivation

`bottleneck.high_fanin_elements` ranks `G.in_degree`, and the edges
run predecessor → successor (`bga/structural/analyzer.py:322-331`), so
an in-edge is a **dependency**. The column's own sentence says the
opposite:

```text
bga/schemas.py:2183-2192  "Elements many others depend on directly"
                          "Elements naming this one as a dependency -
                           an in-degree, not a transitive count"
docs/guides/cli.md:1007   "elements naming this one as a dependency"
```

Measured on `tests/fixtures/macro_micro`, against `UX-681`'s map,
which computes the same quantity from the edge list directly:

```text
element        in_degree  out_degree  fan_in.direct_count
app.bst                8           1                    8
toolchain.bst          0           9                    0
```

`app.bst` has **one** dependent and eight dependencies. It is what the
"many others depend on it" list opens with. `high_fanout_elements`
carries the mirror error.

## Required Fix

Swap the two blocks' prose - `high_fanin_elements` ranks elements with
many dependencies, `high_fanout_elements` elements many others depend
on - in `bga/schemas.py` and `docs/guides/cli.md`. The values are
correct and must not move; only the sentences are wrong.

## Out of Scope

- Renaming the keys. `analyze/v*` is a published contract and the
  names are a defensible reading of a graph drawn this way; the
  sentences are not.

## Acceptance Test

`bottleneck.high_fanin_elements[0].element_uid` on `macro_micro` is
`app.bst`, and the block's description names dependencies rather than
dependents; mutation: restore either old sentence - the guard holding
each description against the degree it ranks reds.

## Outcome

**Gap measured** - re-ran the Motivation's own reading on
`tests/fixtures/macro_micro`, from `graph.json`'s edge list directly
(not the report):

```text
element        in_degree  out_degree  fan_in.direct_count
app.bst                8           1                    8
toolchain.bst          0           9                    0
```

Matches the task file exactly; no correction needed.
`bottleneck.high_fanin_elements[0].element_uid` is `app.bst`
(`fan_in: 8`); `high_fanout_elements[0]` is `toolchain.bst`
(`fan_out: 9`).

**Close measured** - swapped the block description, column title and
column description between `high_fanin_elements` and
`high_fanout_elements` in `bga/schemas.py:2204-2231`, and the one
`cli.md:1010` sentence, in both cases keeping `fan_in`/`fan_out` and
every value untouched. Also dropped a now-stale `UX-719` note on
`elements.fan_in.direct_count` (`bga/schemas.py:2545`) that said the
bottleneck block's prose "has the direction backwards" - true before
this fix, false after.

`make test-touching`: `118 file(s) selected (14 census + 104 naming
the change) · 2267 passed, 41 skipped in 70.18s`. `make lint`: clean.
`dev_baseline.py --check`: 299.

**Mutation table** (`tests/unit/test_a_fan_column_names_the_direction
_it_ranks.py`, scratch-copy edit + restore, never `git checkout --`):

| mutation | clause reddened | result |
|---|---|---|
| restore old `high_fanin_elements` block description | "Elements that depend on many others" | `test_high_fanin_block_says_it_holds_the_dependencies` fails, 1 of 8 |
| restore old `fan_in` column description/title | "Dependencies this element names" | `test_fan_in_column_matches_the_untouched_anchor` fails, 1 of 8 |
| restore old `cli.md` fan_in/fan_out sentence order | "dependencies this element names, and elements naming..." | `test_dependencies_named_before_elements_naming_it` fails, 1 of 8 |

Each mutation reverted from the saved copy; suite green again (8/8)
after each.

**Deviation** - none from the Required Fix. One addition beyond the
two named surfaces: the stale cross-reference at `bga/schemas.py:2545`
(noted above), inside the same file, corrected so it doesn't assert a
now-false claim.
