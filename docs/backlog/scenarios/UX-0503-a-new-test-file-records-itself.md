# UX-503: a new test file records itself in the CI reference

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-420 (the reference), UX-447 (the refresh route), UX-449 | **Serves:** the session that adds a guard and does not want a second commit for it | **Topic:** guards

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
