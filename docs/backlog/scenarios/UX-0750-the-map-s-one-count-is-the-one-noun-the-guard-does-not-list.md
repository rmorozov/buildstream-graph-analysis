# UX-750: the map's one count is the one noun the guard does not list

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-274 (the guard), UX-491/UX-476 (the sentences) | **Serves:** the reader who trusts a guarded sentence because it is guarded | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-274`'s third clause put a guard on the context map so it would
state no count: *"A figure nothing checks is the defect, not the
count, so the map states none."* The guard is
`test_the_map_states_no_count_it_does_not_check`
(`tests/unit/test_the_context_map_is_the_tree.py:448`). It matches a
number followed by one of six nouns:

```python
r"(?:files?|tests?|rows?|elements?|items?|scenarios?)\b"
```

The map contains exactly one counted figure, and its noun is not in
that list. Every digit-run in the guarded text:

```console
$ python3 -c "…_map_text() … re.finditer(r'(?<![\w-])[~]?[\d,]{2,}\s+\S+', text)"
digit-run: '400 lines'
```

One figure, and `lines` is the one noun the guard cannot see — so the
guard passes on a map that states a count, which is the whole thing it
was written to prevent. This is round 103's recurring shape for the
fourth time (`UX-573`, `UX-746`, `UX-748`): **a guard whose population
is narrower than the sentence it checks**, passing vacuously.

The figure has also drifted. `docs/contributing/fixing-guide.md:359`
says the log tail is *"the wrong 400 lines"*; `.github/workflows/ci.yml`
says *"The document above is ~400 lines"* (`:248`) and *"the ~400-line
document `UX-476` prints"* (`:394`). The document is
`ci_reference.candidate.json`, written by `dev_tier_drift.py --record`
at `indent=2`. Its real size, built from the committed reference's own
488-file population:

```console
$ python3 -c "…record(json.load(open('tests/ci_reference.json'))['files']) … len(json.dumps(doc, indent=2).splitlines())"
candidate document lines: 1964
```

1964 with no prior reference passed; CI passes one, which adds `spread`
and `adopted`, so the real candidate is larger still. The claim is ~5x
low. It was true when written — `ci.yml:227` records *"the tail of this
job's log was 370 lines of reference"* as a past observation, which is a
record and stays — but the three sentences above state it as current.

Note what did *not* turn out to be the defect: the guard's regex was
also suspected of false-matching a citation such as `rules.md:12 rows`.
It does match that shape, but no such text is in the map — the
false-positive is latent, not live, and is not what this row fixes.

## Required Fix

1. Widen the guard's noun list so it reads the count the map actually
   states. `lines?` at minimum; prefer deriving the list rather than
   extending it by one, since one-at-a-time is how it got here.
2. **The inverse check before the fix is called done:** the guard must
   redden on the map as it stands today. If widening it leaves the map
   green, the widening is vacuous and the fix is not made.
3. Re-state the three `400` sentences. The map's is a count and must go
   (name the thing, not how many of it there are); `ci.yml:248` and
   `:394` are prose about a real document — date them in `UX-511`'s
   pattern with the command that measures them, or drop the figure.

## Out of Scope

- The latent citation false-positive above. No live text triggers it;
  file it separately if a document ever does.
- `ci.yml:227`'s `370 lines` — a dated past observation, not a claim.
- Any other guard's noun list. Sweeping every guard for the same
  narrowness is a different job and nothing has measured how many
  share the shape; this row fixes only the map's, on the one
  reading above.

## Acceptance Test

`test_the_map_states_no_count_it_does_not_check` reddens on the map at
`4851eb0`, and is green after the three sentences are re-stated. The
mutation table shows the widened noun list reddening on a restored
`400 lines`, and the pre-fix run pasted as the gap.

## Outcome

### The gap

Pre-fix red, the six-noun allowlist widened but the sentences not yet
re-stated:

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py \
  -k test_the_map_states_no_count_it_does_not_check -q
FAILED ...::test_the_map_states_no_count_it_does_not_check
AssertionError: the context map states counted figure(s) nothing
checks: ['400 lines']. Name the thing, not how many of it there are.
```

### The close

Inverted the allowlist to `NOT_A_COUNT`, empty: every id in the map is
already excluded by the existing hyphen lookbehind (`UX-238`, `UX-264`
match nothing), so no entry was needed - one match, `400 lines`, and no
other shape surfaced (checked by exhaustive digit-run scan of
`_map_text()`). Re-stated `dev_junit_tail.py`'s map row to name the
thing. For `ci.yml:248`/`:394`: took the row's second alternative and
dropped the figure - `--record`'s document length depends on CI's own
clock (`UX-418`: "a local report cannot stand in", `ci.yml:218`), so no
command run from a checkout reproduces it; a verifier pass first tried
dating it (3,845, via `record()` fed the checkout's own reference as
both `times` and `reference`) but that is not runnable from CI's actual
inputs, so it was dropped instead. `ci.yml:227`'s `370 lines` untouched,
per Out of Scope.

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q
30 passed in 0.39s
```

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | restore `400 lines` in the map (revert the `dev_junit_tail.py` row) | 1 failed - real count caught |
| M2 | keep M1, revert the guard to the old six-noun allowlist | 30 passed - old regex vacuous, confirms the widening is what catches it |
| M3 | keep M1, add `"400 lines"` to `NOT_A_COUNT` | 30 passed - denylist suppresses, confirms why it ships empty |

### Deviation

None from the Required Fix. `NOT_A_COUNT` ships empty rather than
naming `UX-238`/`UX-264`: the existing lookbehind already excludes
hyphen-prefixed digit runs (ids), verified by scanning every digit run
in `_map_text()` today - adding entries for shapes the regex already
excludes would be dead weight in the set.
