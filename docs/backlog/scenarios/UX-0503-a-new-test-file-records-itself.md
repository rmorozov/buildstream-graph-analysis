# UX-503: a new test file records itself in the CI reference

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-420 (the reference), UX-447 (the refresh route), UX-449 | **Serves:** the session that adds a guard and does not want a second commit for it | **Topic:** guards | **Area:** tools

## Motivation

Rounds 66-73, counted from the log:

```text
commits since round 64                                   162
of which "CI: … reaches the tier reference", re-tier,
  reference refresh, or a Backlog row for one            19   (12 %)
```

The mechanism is documented in the verify skill and it is working as
designed: a new file over the medium floor is not in
`tests/ci_reference.json`, the drift gate names it on the run after it
lands, and the session downloads the candidate artifact or appends a
divided row by hand. One item, two or three commits, and a skill
section of forty lines to explain the dance.

## Required Fix

The gate treats a file **absent from the reference** as *record, not
fail*: it writes the row from its own run into the candidate artifact
and prints it as "new, recorded", and a follow-on job (or the same
job on `main`) commits the candidate back when the only diff is added
rows. Drift is still judged for every file the reference already
holds — the two-run confirmation (`UX-442`) is untouched. A file that
*was* recorded and disappeared is still red, as now.

The verify skill's "expect this after adding a test file" paragraph
shrinks to one sentence.

## Out of Scope

- Local `--record` — still refused for the reason `UX-447` gives;
  the rows come from CI's clock.
- Changing the floors or the drift factor — `UX-458` and `UX-496`
  own those questions.

## Acceptance Test

A branch adding one medium-tier file: the drift step is green on its
first run and the candidate carries the new row; a branch making an
existing file slower still reds on the second run. Mutation: remove
the absent-file branch — the first run reds again.

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

A reference holding every tiered file, and a run measuring one more — a
real file in neither tier list, at 12.0s, over `MEDIUM_FLOOR_S`:

```text
1 file(s) slower than CI's own record of them:  ...never_saw.py  12.0s
  and not in the reference at all                    exit=1  <- run ONE
```

"Slower than CI's own record of them", for a file CI has no record of —
fixing guide §5, the proxy being the reference's *coverage*. On run one
because `repeated()` carried `if row[2] is None: confirmed.append(row)`
ahead of `UX-442`'s window, skipping the rule that would have held it
back for the one population with no evidence. Price, from the log: 19 of
162 commits since round 64.

### After

```text
1 file(s) over 1s that the reference does not carry yet - measured here,
not judged (UX-503):  ...test_a_capture_can_say_what_it_never_saw.py  12.0s
tiers ok: 153 file(s) measured against ref.json, x1.00           exit=0
```

Run 2 over the same carry is identical — the run that used to report it
is green too, which a `waiting` bucket would have hidden. `--adopt` then
writes the row back, from a candidate **1.3x slower** at 17.71s:

```text
adopted 1 file(s) into ci_reference.json, on its own clock:  ...believes.py  13.62s
```

13.62, not 17.71: a raw append puts the row 30 % high and makes the file
unjudgeable for as long as it stands — `UX-418`'s cross-clock comparison
by the back door. `--adopt` adds only names the reference lacks, and
refuses (no shared file; shift outside `IMAGE_BAND`) rather than guess.
**Absent** is now recorded, not confirmed; **present and slower** is
unchanged; **present, gone from this run** contributes nothing, which is
what makes a *rename* green and had no clause before this item.

**A guard of ours that did not discriminate.** Both workflow steps
running the tool open with the *same* line, so
`test_ci_reads_the_reference_and_not_the_floors`' `text.split(line, 1)`
cut at the first and checked `--record`'s step against `--against`'s — on
the `HEAD` workflow with `--record` deleted it fails on **0** steps. It
now reads the parsed workflow per step.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| M1 | `repeated()` stops splitting absent rows | 5 clauses |
| M2 | `_against` stops printing them | 1 |
| M3 | `adopt` writes the candidate's own seconds | 1 |
| M4 | `adopt` drops `if name not in known` | 4 |
| M5 | `adopt` drops the `IMAGE_BAND` refusal | 1 |
| M6 | `against` reads an unmeasured file as measured | 1 |
| M7 | the adopt step in `ci.yml` loses `--adopt` | 1 |

M1 reds by `TypeError` too (`say()` has no `None` branch now); the one
that reds cleanly asserts the *bucket* — an absent row in `waiting` is
also a green first run.

### Deviation from the Required Fix

**The commit-back job pushes to the default branch and cannot be verified
from here.** `tier-reference-adopt`: `push` + default branch,
`permissions: contents: write`. Whether the branch accepts a
`GITHUB_TOKEN` push is a repository setting no guard can read, so a
rejection is a `::warning::` and the job stays green — the first merge
after this lands says which. Nothing else. §3.10: the `verify` skill's
paragraph (8 lines → 3), the fixing guide's `ci_reference.json` row.

```text
make test-touching 485 passed 17.40s;  make lint clean
make test          5741 passed, 27 skipped in 334.14s
```
