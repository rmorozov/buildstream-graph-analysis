# UX-725: `bga view --export` prints two ERROR lines and exits 0

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-326 (the tool's own sentences are contracts), UX-55 (compare's run-mode refusal) | **Serves:** anyone exporting a run whose neighbour is a different run mode | **Topic:** cli | **Shape:** judgement | **Area:** bga

## Motivation

Found by `UX-685`'s walk at seed 2, reproduced here verbatim:

```text
$ bga view @last --export verify.html; echo "exit=$?"
ERROR bga.cli: Not comparable: baseline run .../20260906T021223Z/run is a
  full run but the candidate is incremental - a noise band may only be built
  from runs of the same kind (UX-55)
Error: baseline run .../20260906T021223Z/run is a full run but the candidate
  is incremental - a noise band may only be built from runs of the same kind
  (UX-55)
Wrote .../verify.html (418 KiB). Open it with a browser - it needs no server
  and no network.
exit=0
```

Three things are wrong at once. The **same sentence prints twice**,
once as a log record and once as `Error:`. It is called an error on a
command that **succeeded** — a complete 428,044 B export was written
and the exit code is 0. And what actually happened is that one
optional section (the comparison band) had no comparable neighbour,
which `UX-388`'s vocabulary calls an absence, not a failure.

`UX-326` is the rule: the tool's own sentences are contracts. A
sentence that says `ERROR` on a run that produced its whole output
teaches a reader to ignore the word.

## Required Fix

The band's unavailability is stated once, in the absence vocabulary
(`UX-388`), on the surface the export itself carries — not as `ERROR`
on stderr. `bga compare`'s hard refusal for the same mismatch stays as
it is: `UX-55` governs a command whose whole output is the comparison,
and this one's is a page.

## Out of Scope

- `bga compare` — its refusal is correct and this item does not touch it.

## Acceptance Test

`bga view --export` on a run whose only neighbour is a different run
mode exits 0, writes the export, prints no line matching `^ERROR|^Error:`,
and the page names the band's absence. Mutation: restore the stderr
pair — the guard reds on the duplicate and on the word.

## Outcome

### Gap measured

Two-run-mode store (`.bga/runs/`, an incremental run then a full one),
`python3 -m bga.cli view CANDIDATE --export verify.html; echo exit=$?`,
before this fix:

```text
ERROR bga.cli: Not comparable: baseline run …/20260101T000000Z/run is a
  incremental run but the candidate is full - a noise band may only be
  built from runs of the same kind (UX-55)
Error: baseline run …/20260101T000000Z/run is a incremental run but the
  candidate is full - a noise band may only be built from runs of the
  same kind (UX-55)
Wrote …/verify.html (437 KiB). …
exit=0
```

### Close measured

Same store, same command, after:

```text
Wrote …/verify.html (437 KiB). Open it with a browser - it needs no
  server and no network.
exit=0
```

No line matches `^ERROR|^Error:`. The exported page's `run` document
carries `comparison_unavailable`, and booting the real export under
Node (`tests/dom_shim.mjs`) shows the rendered section:
`data-section="band" data-empty="true"`, text `"The band No comparison
band: baseline run …/20260101T000000Z/run is a incremental run but the
candidate is full - … (UX-55)"`.

### Mutation table

| # | mutation | reddened |
|---|---|---|
| M1 | `_capture` stops redirecting stderr (the original defect, restored) | 3 of 5 in `test_the_export_names_a_bands_absence.py`: the no-`ERROR`-line clause, the sentence-appears-once clause, and the page's-reason clause (3 failed, 2 passed) |
| M2 | `renderBandUnavailable` drops `data-empty` and the reason text | the render-function clause (1 failed, 4 passed) |

### Verification

```text
pytest tests/unit/test_the_export_names_a_bands_absence.py    5 passed
make test-touching   125 file(s) selected, 2411 passed, 61 skipped, 472.4s
make lint             clean
dev_baseline.py --check   299, unchanged
```
