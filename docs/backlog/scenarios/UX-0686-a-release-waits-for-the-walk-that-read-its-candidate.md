# UX-686: a release waits for the walk that read its candidate

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-251 (releases as contract states), UX-685 | **Serves:** R8 cutting a release; the reader who installs it | **Topic:** docs | **Shape:** bounded

## Motivation

```text
docs/contributing/release-guide.md:29-33   cut when a contract moved and a review row exists at or after the last release
grep -i "walk\|exploratory" release-guide.md rules.md verify/SKILL.md   → 0 hits
CHANGELOG.md:60                            0.4.0 — 2026-09-03; Review 16 on 2026-09-04
```

A release records a contract state, and nothing makes it wait for
anyone having *used* that state. The walk skill exists and is
invoked by audit rounds when they remember.

## Required Fix

The release guide gains a third condition: the release candidate is
the last commit that changed a contract; a walk (`UX-685`, any seed)
has run on or after it, its report is in `docs/audits/`, and every
finding it filed is closed or declined by name in the release's
CHANGELOG row. The release derivation guard reads the walk's date
against the candidate commit's date and the filings' status. Cadence
follows from contract changes, not a calendar.

**Two decisions the first track stopped on, settled here.**

*The candidate commit is over-approximated on purpose.* It is the
newest commit touching a file that `bga.contracts.inventory()` names,
plus `bga/cli.py` and `bga/tools_dispatch.py` (the command surface) —
`git log -1` over that set. Touching `schemas.py` without moving a
`/vN` counts, so the candidate can be newer than the true last
contract move. That is the **safe** direction for a gate: an
over-approximation can only make a release wait longer, never let one
through unreviewed. Bisecting `contracts.ids()` for the exact commit
is a cheaper-to-state, more expensive-to-run alternative and is not
worth it here; say so in the Outcome.

*The design review half is deferred.* A design review report has no
shape a guard can recognise (`UX-727`), so this item checks the
**walk** only. The guide's third condition names the review as a
requirement for a human to satisfy; the derivation guard does not read
it until `UX-727` gives it a head to read.

## Out of Scope

- Blocking a release on *open* filings of other kinds — only the
  walk's and the review's own findings gate it.

## Acceptance Test

With a walk dated before the candidate commit, the release guard
refuses naming the walk's date; with one after, and its findings
closed, it passes. Mutation: drop the date comparison — red.
