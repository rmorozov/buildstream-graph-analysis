# UX-866: a key under a bare object is still a documented key

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-858, UX-838 | **Found by:** round 120, review 24 | **Serves:** R4 (the guide names every flag and key the capture writes) | **Topic:** docs | **Area:** bga | **Shape:** mechanical

## Motivation

`UX-858` added `--jobserver-seed N` to `bga capture run` and `seed` to
`run_instance.jobserver`; `docs/guides/cli.md`'s jobserver flag list
names every sibling flag and not this one, and its `run_instance.
jobserver` row lists four keys where the schema hint has five. The
coverage guard (`test_the_documents_keep_up_with_the_contracts.py`)
never sees it: the real schema types `run_instance` as a bare `object`,
so `_consumer_surface()` never descends into it - `UX-838`'s shape one
level up the schema.

## Required Fix

`docs/guides/cli.md`: a `--jobserver-seed N` line in the jobserver
flag list and `seed` in the `run_instance.jobserver` row; the coverage
walk (`_consumer_surface()` or the guard's own reader) also reads the
keys `_RUN_INSTANCE_HINT` declares under `run_instance`, so a key added
there with no guide row reds the guard.

## Decomposition

Input classes: a key under a typed object, a key under a bare object
with a hint, a key with no hint at all; the journey it extends is
review 24's read of the guide against the tree.

## Out of Scope

Typing `run_instance` with `properties` in the published schema (a
contract change, its own row).

## Acceptance Test

`tests/unit/test_the_documents_keep_up_with_the_contracts.py`: the
walk counts `run_instance.jobserver.seed` and the guide names it;
mutation: drop the hint's keys from the walk - the count falls and the
guide's stated reach reds.

## Outcome

**Gap measured.** Before: `_consumer_surface()['seed']` was `None` -
`_row_keys`'s three cases (`items`, `bga:columns`,
`additionalProperties.properties`) never read a plain nested
`properties`, which is how `_RUN_INSTANCE_HINT` (merged into the real
schema by `_document`) declares `run_instance`'s fields, `seed`
included. Widening the walk to that fourth case surfaced eight keys
the schema always had: `started_at_us`, `host_manifest.cpu_count`,
`.memory_bytes`, `jobserver.mode/.ceiling/.seed/.auth/.project_max_jobs`,
295 keys becoming 303. Of those, only `started_at_us` had no prose
anywhere; the other seven were already named (four in the `run_instance.jobserver`
row itself, `cpu_count`/`memory_bytes`/`seed` coincidentally, by
`os.cpu_count()`, `host/v2`'s field and `gen-synthetic --seed 1`).

**Close measured.**
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest
tests/unit/test_the_documents_keep_up_with_the_contracts.py -q` - 26
passed (was 25, +1 new fixture). `test_docs_links_and_commands.py`:
59 passed. `make test-touching`'s 53-file set (via `dev_touching.py
--list` + direct `pytest -n 2`): 1706 passed, 4 skipped. `ruff check
bga/ tools/ tests/ .claude/hooks/`: clean. `dev_sizes.py --check`:
clean, 122 files, none over. `dev_baseline.py --check`: clean, 566
findings match baseline. `pymarkdown scan docs/guides/cli.md`: clean.

**Mutation table** (falsify skill; each reverted from a scratchpad
clean copy, `PYTHONDONTWRITEBYTECODE=1`, reconfirmed green):

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| the walk reads a hint's own nested `properties` (`_hint_keys`, wired into `_consumer_surface`) | drop the `_hint_keys` call from `_consumer_surface` | `test_the_guide_states_the_reach_it_actually_has` (303 stated, 295 actual) | 1 failed |
| `_hint_keys` recurses at any depth (new fixture, `UX-866`'s own) | strip the recursive call, one level only | `test_a_key_under_a_bare_object_is_reached_via_its_hint` (own marker, nested two deep, not found), plus `test_the_guide_states_the_reach_it_actually_has` (303 vs 296) | 2 failed |

**A guard that did not discriminate.** The Acceptance Test's own
mutation - dropping `seed` alone from the guide's `run_instance.jobserver`
row, walk intact - passed all 26 clean. `seed` is already named via
`bga gen-synthetic --seed 1` (three unrelated occurrences in
`cli.md`/`directions.md`), which `code_spanned` finds as the bare
token `seed` regardless of the row. Confirmed: `'seed' in
_named_in_the_documents()` is `True` before and after the row edit.
The row and the `--jobserver-seed N` flag-list bullet stand per the
Required Fix - a reader looking up `run_instance.jobserver` needs the
field named there whether or not the guard's name-based check happens
to discriminate on it, the same shape UX-838 found for `direct`.

Deviation: the widened walk surfaced `started_at_us` with no prose
anywhere (not asked for by name, but "whatever else the hint holds"
committed to it) - documented in the same `run_instance.jobserver` row
alongside `host_manifest.cpu_count`/`.memory_bytes`, one clause,
rather than opening a second row or narrowing the walk to `jobserver`
alone.

**Deviation (merge):** the verifier replayed both mutations and the
task's own `seed` one (26 passed - `seed` is a bare token from
`gen-synthetic --seed 1` elsewhere); of the eight keys the walk gained
only `started_at_us` reds when its prose goes. A fully generic walk
would have added 171 undocumented internal keys (578 in all); the plane2
`jobserver` block alone adds 4, every one already named. At merge the
walk's docstring lost its stale "This walk is 236" figure, which no
guard read.
