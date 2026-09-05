# UX-681: fan-in — what an element depends on, ranked

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-479 (blast for elements), UX-407 (never-read edges) | **Serves:** R2 minimising incoming dependencies, R3 spotting the suspicious fan-in | **Topic:** analysis | **Shape:** judgement

## Motivation

```text
downstream_count / blast_radius / blast_radius_distribution    bga/findings.py:1256-1391  — fan-out, with deciles
grep fan_in|upstream_count|consumers bga/*.py                   0 hits                     — fan-in does not exist
compute_dominators                                              bga/graph/edg.py:371, called once at :950 — never published
```

The element owner's first question — how many things do I pull in,
and which of them do I actually use — has the second half answered
(`UX-407`'s never-read edges) and no first half. The graph owner's
"suspicious fan-in" is the same number ranked.

## Required Fix

Per element: direct and transitive upstream counts, the share of
those edges Plane 2 saw read (`UX-407`), and the dominator — the one
element every path from the roots passes through, which is the
rebuild gate a developer waits on. Ranked with deciles like the
blast distribution, by kind, with the same structural exemption. A
`fan_in` section and a `fan-in-*` finding family mirroring
`blast-radius-*`.

## Out of Scope

- Pruning edges — the never-read list is the advice; the owner edits
  the recipe.

## Acceptance Test

Example 06: lib-f's transitive fan-in names codegen among the
never-read; the dominator of app.bst is core.bst; mutation: count
direct edges as transitive — the closure guard reds.

## Outcome

**The gap, measured.** The Motivation's three lines held. Both
traversals ran on every analysis and reached no reader:

```text
$ grep -rn "reachable_upstream\|compute_dominators" bga/ --include=*.py \
    | grep -v graph/edg.py
bga/graph/analysis.py:950   compute_dominators(graph)   -> graph_analysis, unread
(no other consumer; grep fan_in|upstream_count -> 0 hits)
```

**The close, measured**, on `tests/fixtures/macro_micro` (example 06,
11 elements, 34 edges, one root):

```text
elements.fan_in[lib-f.bst]  direct 4 · transitive 8 · dominator toolchain.bst
elements.top_fan_in         [app, lib-f, lib-e, lib-d, lib-c]
fan_in_distribution         n=11 min 0 max 10 p50 5 p95 10
element_join[app.bst]       assessed 8 · read_share 0.125 · 7 unused
findings                    fan-in-ranking (graph-owner)
                            fan-in-structural (recipe-author, all.bst 10 up)
```

**The mutation table.** Ten, each reddening a named clause in
`test_what_an_element_pulls_in.py`.

| mutation | clause that reds |
|---|---|
| transitive count is the edge count | `..._a_transitive_only_upstream_is_named` |
| the dominator is the furthest, not the nearest | `..._the_nearest_of_several_is_the_one_published` |
| a root gates on itself | `..._a_root_has_no_gate` |
| structural kinds are ranked | `..._the_largest_fan_in_is_excluded_for_being_structural` |
| elements that pull in nothing are ranked | `..._nothing_that_pulls_in_nothing_is_ranked` |
| the share divides by the unread list alone | `..._the_share_is_of_what_plane_two_could_assess` |
| an unassessed element scores 1.0 | `..._plane_two_measured_but_never_assessed_has_none` |
| the density sentence says "reach" | `..._the_ranking_carries_the_scale_and_the_right_verb` |
| the stack is ranked, not reported | `..._the_widest_fan_in_is_named_as_shape_and_not_ranked` |
| the ranking is the local optimizer's | `..._each_member_names_its_reader` |

**Two of my own guards were vacuous, and mutation found both.** The
zero-closure clause read `toolchain.bst not in top_fan_in(rows)`; with
the rule deleted that element sorts eleventh of eleven and is out of
the top five anyway, so the clause passed whatever the helper did. It
is a constructed graph of leaves now. The absent-share clause read
`toolchain.bst`, which is not in the Plane 2 view **at all** - a
different question - so it never reached the branch it named; a second
clause constructs the element Plane 2 measured and could not assess.

**Four deviations.**

*The read share is not a fan-in column.* The Required Fix asks for it
there; `ELEMENT_PLACEMENT_RULE` says an attribute that needs Plane 2 is
a field on an `element_join` row, and the rule wins - `elements.fan_in`
is on every capture and a Plane 2 column in it is null on every
single-plane run. It is `element_join.dependency_read_share`, and its
denominator is what Plane 2 could *assess* (`used` plus
`unused_candidates`), not the declared edge count, which would have
scored an uncovered dependency as unread.

*Two members, not a family of four.* `fan-in-reach` would restate the
ranking - what an element pulls in **is** the count it is ranked on,
where `blast-radius-reach` adds a cost argument a downstream count does
not carry - and `fan-in-unread` would restate `restructuring`, which
already names the never-read edges and replays the saving (`UX-407`).

*The Acceptance Test was wrong twice, and this file corrects it.*
`codegen` is a **direct** dependency of `lib-f`, so it is in the
closure for free and the named mutation could not fail; `all.bst` (1
direct, 10 transitive) is the discriminating pair. And the dominator of
`app.bst` is `toolchain.bst`, not `core.bst`: `app` depends on
`toolchain` directly, so no path to it passes through `core`. A
dependency and a dominator are different claims.

*Two findings this work falsified elsewhere, filed rather than fixed
here.* `bottleneck.high_fanin_elements` ranks `in_degree`, which on
this edge direction is the element's own **dependencies** - the same
number as `fan_in.direct_count`, verified equal on all eleven
elements, while its prose says "elements many others depend on".
`UX-719`.
And `findings[].evidence.blast_radius_distribution` was never declared:
both committed fixtures are chain-bound, so that finding is not emitted
and its fifteen leaves reached no census. The mirror *is* emitted,
which is how the gap surfaced; both are declared now.

*One thing the diff had to move.* `_compute_diagnostics` sat at exactly
the statement budget `tests/quality_baseline.json` holds it to, so a
single `signals.update(...)` tripped `PLR0915` - and `UX-705` forbids
a suppression. Part 25's blast block is lifted whole into
`_blast_signals`, beside the mirror that is modelled on it. A move: all
seven keys verified present on `macro_micro` after it, and the baseline
is back at 299 findings with nothing forced.

The export bounds move to 443,000 and 497,000 (+5,118 / +8,879). The
3,761 B between them is `macro_micro`'s own fan-in data - eleven rows
plus the distribution - which `golden`'s four elements cannot produce.
The golden depth budget moves 0.49 -> 0.50: an element-keyed map of
records is depth four by construction, as `blast_radius` has been since
`UX-479`.
