# UX-624: the cap dropped a guard that was not noise

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-605 (the cap), UX-522 (the census set), UX-336 (the selector) | **Found by:** round 85, by the contracts track paying for it | **Serves:** a track adding a declared key | **Topic:** guards | **Area:** tools

## Motivation

`UX-605` capped a coverage-map entry at 25 files, because CI's adopted
`tests/touch_map.json` made a one-module diff select 180 of 449. The
cap is right about the noise and wrong about one file it took with it:

```text
$ python3 -c "…dt.select(['bga/schemas.py', 'bga/compare.py'])…"
cap=        25  selected=  53  test_every_number_says_what_it_is.py: False
cap=1000000000  selected= 216  test_every_number_says_what_it_is.py: True
                                why: ['map', 'map']
```

Both entries are over the cap — `bga/schemas.py` maps 189 files,
`bga/compare.py` 30 — so both are discarded whole, and the guard that
reads every declared quantity goes with them.

**Corrected while implementing (round 85):** the sentence that stood
here said the guard is *"reachable only through the map: no grep from
either module names it"*. That is true of the selector and false of
the file — it writes `from bga import schemas` nine times. `tokens_for`
spells that module `bga/schemas.py` and `bga.schemas` and withholds the
bare stem, so the grep half never saw the `from <package> import
<module>` form at all: **253 such edges across the suite**, 70 of them
naming `bga/schemas.py`. The map had been covering a tokenizer gap and
the cap exposed it. The cap is not the defect and neither is the map.

The cost is not hypothetical. `UX-610` added `verdict_provenance` to
`compare/v2`, passed `make test-touching`, and failed that census;
the track amended its commit. The next declared key does the same.

The cap is not the defect. Discarding an over-wide entry *whole* is:
it treats a map entry as one claim when it is 189 of them.

## Required Fix

A guard reachable only through an over-wide map entry still reaches the
selection — by joining the census set (`UX-522`), by the map being
pruned rather than capped, or by the cap dropping the entry's noise and
keeping what a narrower rule would have kept. Argued from the
measurement, not chosen for tidiness.

Whatever is chosen must keep `UX-605`'s property: a one-module diff
does not select a third of the suite.

## Out of Scope

- The map's contents and how CI adopts it — `UX-605` measured that and
  the cap stands.
- `UX-610`, which paid the cost and is closed.

## Acceptance Test

A `bga/schemas.py`-only diff whose selection contains
`test_every_number_says_what_it_is.py` and stays under `UX-605`'s
ceiling — **`{"median": 20, "p90": 45, "max": 130}`**. The 25 written
here first was `HANDFUL`, a different bound in the same file.

## Outcome (round 85, 2026-09-04) — 🔴 Open

**Premise:** held, its explanation wrong. The cap does drop the guard,
but the guard is not "reachable **only** through the map": it writes
`from bga import schemas` nine times, and `tokens_for` spells that
module only `bga/schemas.py` and `bga.schemas` — the stem is withheld
because `schemas` has no `_`. The grep was blind to the `from <package>
import <module>` form and the map had been covering for it.

### The gap, measured

```text
$ python3 -c "…dt.select(['bga/schemas.py', 'bga/compare.py'])…"
cap=        25  selected=  53  test_every_number_says_what_it_is.py: False
cap=1000000000  selected= 216  test_every_number_says_what_it_is.py: True
     why: ['map', 'map']
map size: 85 · bga/schemas.py maps 189 · bga/compare.py maps 30
```

The filing's figures reproduce exactly. Across all 461 test files,
**253** `from x import y` edges existed that no token matched — 70
naming `bga/schemas.py`, 25 reachable only because another name was
written first (`from bga import contracts, schemas`).

### After

```text
$ python3 -c "…dt.select(['bga/schemas.py'])…"
bga/schemas.py-only diff: 87 files selected of 461
test_every_number_says_what_it_is.py: True  why=['bga/schemas.py']
over 85 mapped modules: min=11 median=17 p90=40 max=124
UX-605 ceiling:          median=20 p90=45 max=130
```

`why` is the changed path, not `map` and not `census`: the grep reaches
it, so the cap is never relaxed. `UX-605`'s property holds with room —
median 16→17 against 20, max 118→124 against 130. `bga/contracts.py`
goes 14→27 and joins `WIDE`, argued there.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| M1 | `import_pattern` not appended in `select` | `…_selected_again`, 2 failed |
| M2 | drop the `(?:[\w\s,]*?,\s*)?` multi-name group | `…another_name_written_first…`, 2 failed |
| M3 | drop the `\b` after the module name | `…longer_name_that_starts_the_same`, 1 failed |
| M4 | let `__init__` through `import_pattern` | `…package_init_is_still_not_a_spelling`, 1 failed |
| M5 | `MAP_ENTRY_CAP = 10**9` | `…map_entry_really_is_over_the_cap`, 6 failed |
| M6 | pattern also matches the bare stem | `…did_not_swallow_the_two_misses`, 6 failed |

M5 and M6 are blunt — six clauses each, because they move `UX-605`'s
cap and the grep's looseness, which many clauses read; each is kept as
the only mutation reddening its target for the right reason. M1 and M2
also redden the `WIDE` clause, which is that clause working.

The first draft of `…did_not_swallow_the_two_misses` compared
`select()` to itself and was true by construction. It now recomputes
the derivation's reachable set and asserts `len > 100` before reading
it: an over-broad spelling does not fail that clause, it empties the
input and the clause skips.

### Deviation from the Required Fix

None; the third route, taken at its own word. Route 1 is unavailable,
measured not assumed: the guard fails **both** census conditions —
`_walks_the_repo` is `False`, and four source modules' greps already
select it — so declaring it would redden
`test_nothing_is_declared_that_does_not_read_the_tree`. Route 2 was
measured and rejected: pruning by selectivity drops exactly this guard,
which touches 45 of 85 mapped modules. `tests/tiers.py` is untouched.

```text
$ make lint      → All checks passed!
$ make test-touching → 16 file(s) selected · 634 passed, 3 skipped in 46.85s
$ make test-small    → 1 failed, 4077 passed, 36 skipped in 79.36s
```

The one failure is `test_the_review_has_a_cadence` (30 closed scenarios
against a bound of 25) and fails identically at `245dfed` with this
diff stashed: it asks for an architecture review, not for this change.
