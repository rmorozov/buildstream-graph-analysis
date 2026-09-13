# UX-830: the serial chains, ranked, not the longest one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-719 (the bottleneck view), UX-681 (fan-in) | **Found by:** round 115, the design review | **Serves:** R3 deciding which chain to split | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`bottleneck` draws one "Longest serial chain" (walk capture:
toolchain.bst → storm.bst → all.bst, length 3) beside a "Waiting on it"
list. Blast has a ranked table with a detail row per element; a chain
has one exhibit. On a graph where the second chain is a second's
shorter than the first, splitting the first moves the critical path to
the second and the page says nothing about it until the next capture.

## Required Fix

`serial_chains`: the top N chains by duration-weighted length,
disjoint or overlapping as measured, each with its members, its wall
share and the element whose split shortens it most; the bottleneck
section draws them as a ranked table with the members as a folded cell
(`UX-532`'s shape). N follows the row cap.

## Decomposition

Input classes: a chain graph (`a_chain_beside_a_crowd`), a wide flat
graph (`shared_base_wide`, chains of length 2), and the scale graph;
the journey is R3's "which chain" question in the answer key.

## Out of Scope

- What-if on a split — `whatif/v1` already prices a lowered duration; a split is a graph change, Direction 17's question.
- The rail's per-element view — `UX-254`.

## Acceptance Test

On the scale export the table has ≥ 5 chains, the first equal to
today's longest chain; mutation: return one chain — the guard on the
count reds.

## Outcome

**Gap measured.** `longest_serial_chain` walks only a root (in-degree
0) once and gives up the instant it branches. On the two topology
fixtures and the scale run the sole root branches immediately, so
today's "longest chain" is length 1: `a_chain_beside_a_crowd` →
`['lib0.bst']` (a real length-4 chain, `lib0→lib1→lib2→lib3`, sits
unseen); `shared_base_wide` → `['toolchain.bst']` (six real length-2
chains unseen); the scale run (1,202 elements, seed 1) →
`['toolchain.bst']`, while 3,209 real chains exist. On `golden` the
root does not branch and the gap does not hold: `longest_serial_chain`
is `['base.bst','lib.bst','app.bst']`, equal to `serial_chains[0]` -
the Acceptance Test's "first equal to today's longest chain" holds
there.

**Close measured.** `serial_chains` (`_find_serial_chains`,
`bga/structural/analyzer.py`) starts a walk at every root/join point
(in-degree != 1); each outgoing edge is extended by `_extend_chain`
through 1-in-1-out nodes only, stopping at the next join or leaf - a
join is the tail of every chain reaching it and the head of its own,
so chains overlap only at their ends (fixed post-review: the first cut
reused `_find_longest_serial_chain_from`, which checks only the
current node's out-degree and sailed through a join; a diamond
`A,B->C->D->E` gave `[A,C,D,E]` instead of `[A,C]`/`[B,C]`/`[C,D,E]`).
Capped at `SERIAL_CHAINS_MAX = 40` (mirrors `TABLE_OPENS_BOUNDED_ABOVE`).
`longest_serial_chain`/`serial_chain_length` untouched byte for byte.
Scale run, re-measured after the fix: 40 rows (down from 3,209
candidates), rank 1 = 2 elements (`layer05/mod033.bst`,
`layer06/mod005.bst`), 17,700,000us, `wall_share` 0.21 - shorter than
the first cut's 7-element/0.45 answer, because most of that answer
sailed through join nodes it should have stopped at. `members` needed
no viewer code: `CONTROLS.FOLDED_LIST` already folds an array over
`ARRAY_INLINE_ITEMS` (6), and the table never exceeds the row cap.

**Mutations verified red and reverted (3):** `rows[:SERIAL_CHAINS_MAX]`
→ `rows[:1]` reddened every count assertion, including the planted
diamond's three-chain count; reverted, re-ran green (5 passed, 5.35s).
`rows.sort(key=(-w,-l,name))` → ascending reddened `_assert_ranked`'s
descending check ("not descending", `8000000 <= 5000000`); reverted,
green. Dropping `_extend_chain`'s in-degree stop
(`while out_degree==1` alone) reddened only the diamond case
(`[A,C,D,E]` for `[A,C]`), the guard the fix was for; reverted, green.

Additively surfaced nine mechanical consequences, each fixed in its
own surface (never `tests/tiers.py`/`ci_reference.json`/README/
closed.md): two "same selection twice" false positives (a length-2
chain is an edge; `serial_chains`/`binary_cost` coincide on
`macro_micro`), a label restating its unit ("Wall share" → "Of longest
path"), cli.md's key count (263→269) plus a prose row, the
`test-touching` spread, a wide-module addition avoided by renaming a
test method (`_shared` substring), `golden`'s nesting-depth ratchet
(0.51→0.52), styleguide.md §7's §3a row, and the page volume budget
(§3e: 50-class height 36,300→38,200; 4,100-class height 32,000→36,500,
words 9,400→9,600, nodes 5,500→6,000 - `make test`, not
`test-touching`, caught this one, the `UX-717` miss again).

Left alone, pre-existing on the true baseline (`git stash`-verified):
`start_offset_us` undocumented (`UX-828`), both size-budget bounds
already over in this worktree's path length, CLAUDE.md's stale ledger
figure, and `test_a_distribution_twin_draws_every_mark.py`'s (`UX-827`)
lint failure.
