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
and a design review have run on or after it, their reports are in
`docs/audits/`, and every finding they filed is closed or declined
by name in the release's CHANGELOG row. The release derivation guard
reads the audits' dates against the candidate commit's date and the
filings' status. Cadence follows from contract changes, not a
calendar.

## Out of Scope

- Blocking a release on *open* filings of other kinds — only the
  walk's and the review's own findings gate it.

## Acceptance Test

With a walk dated before the candidate commit, the release guard
refuses naming the walk's date; with one after, and its findings
closed, it passes. Mutation: drop the date comparison — red.
