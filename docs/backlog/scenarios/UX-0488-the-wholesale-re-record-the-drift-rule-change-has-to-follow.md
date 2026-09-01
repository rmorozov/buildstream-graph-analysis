# UX-488: the reference is five hand-appends deep, and the re-record has to come after the rule change

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-476` items 1-3, which are what a candidate must be taken *after* | **Found by:** round 73, closing `UX-476` | **Serves:** the round that reads `spread`'s history off the reference's git log and finds one entry repeated five times | **Topic:** guards

## Motivation

`UX-476` item 4 asked for a wholesale re-record of
`tests/ci_reference.json` from one green run's `tier-reference` job,
retiring the hand-appends round 73 added. It is filed separately
rather than done there, for a reason that is about ordering rather
than effort:

**`UX-476` item 2 changed what `--record` writes.** `spread` now takes
its median over `shift_population` — the files the gate divides by —
and reports `shift_files` beside `files`. A candidate taken from a run
that predates that change carries the old quantity, which is precisely
the proxy `UX-476` filed. So the re-record has to come from a run that
already has the fix in it, and the commit that lands the fix cannot
contain that run's output.

The debt it leaves is the one `UX-458` could not read:

```console
$ for c in $(git log --format=%h -- tests/ci_reference.json); do
    git show "$c:tests/ci_reference.json" \
      | python3 -c 'import json,sys; print(json.load(sys.stdin).get("spread"))'
  done | sort -u | head
{'files': 314, 'shift': 1.34, ...}
```

One distinct spread across every commit, because every commit since
`UX-457` is a hand-append that copies the old one forward. `UX-458`'s
Acceptance Test — *"lists at least the agreed number of distinct
spreads"* — cannot be satisfied by appending at all.

The hand-appends to retire, all from round 73:
`test_emphasis_is_a_budget.py` 16.86,
`test_the_shape_conclusions_have_a_negative_case.py` 0.07,
`test_the_trace_census_reads_both_ends.py` 6.76,
`test_a_generated_project_builds.py` 0.17,
`test_a_candidate_is_confirmed_alone.py` 2.32.

## Required Fix

- **One candidate, whole.** From a green run's `ci-reference-candidate`
  artifact, or — `UX-476` added this — the `::group::` block in the
  same step's log, which is what a reader with an API client and no
  artifact access has. Never a local `--record` (`UX-418`, `UX-447`).
- **The run must carry `UX-476`'s `spread`**, so the document's second
  distinct spread is the quantity the gate actually divides by.
- **Both numbers stated** in the commit: the run's shift and the
  spread's, which `UX-476` measured 24% apart on one run before the
  fix and which should now be the same number.

## Out of Scope

- The rule itself — `UX-476` items 1-3 landed and this row does not
  reopen them.
- `CI_DRIFT_FACTOR` — sizing it is what a second spread makes possible,
  and it is the round *after* this one's question.

## Acceptance Test

```bash
python3 -c "import json;print(json.load(open('tests/ci_reference.json'))['spread'])"
```

showing a spread taken from the re-recording run — a second distinct
one in the document's history, with `shift_files` present — and
`git log -- tests/ci_reference.json` showing the append commits behind
it rather than beside it.

## Outcome

_Not started._
