# UX-584: the figures nothing reads — thirteen stale numbers in the process layer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-471 (the count removed from CLAUDE.md), UX-505 (the card), UX-551 (the suite figure) | **Serves:** every session's first read | **Topic:** docs

## Motivation

Round 82 checked every number in the process documents against the
tree. Where a guard reads the figure it is true; where none does it
has drifted:

```text
fixing-guide.md:96        analyze/v2, compare/v1, blast/v1 "analyze is at v2"   schemas.py: v5 / v2 / v2
fixing-guide.md:69,74 · verify SKILL.md:33   small tier 11 s (2026-08-27)       time make test-small: 22.3 s (3,536 tests)
tests/tiers.py:60-70      last re-timed round 56, reads 8.6 s                    neither matches
researcher.md:5,19        "421 task files"                                       560  (UX-471 removed it from CLAUDE.md only)
verify SKILL.md:130       "380 files" in ci_reference                            426
decompose SKILL.md:50-60  "Three files are shared" then four paths; implementer.md says four
decompose SKILL.md:87-92  1.33 commits/task "the only one on file"               round-80.md:23 records 1.83
measure SKILL.md:117 · dev_perfetto_queries.py:13   fourteen questions           questions.js: 17
rules.md:6 · fixing-guide.md:6   guide is 34 KB                                  38,354 B
style-guide.md:15-17      "Two of them are enforced by test"                     five rules say so
release-guide.md:23       twelve contracts                                       23 (14 not superseded)
verify SKILL.md:99-118    the red-job route never names dev_junit_tail           UX-554's tool
```

`test_no_line_carries_a_count_that_a_close_makes_wrong` reads
`CLAUDE.md` only; `test_the_context_map_is_the_tree.py:189` bans
counted nouns in §6 only; the skills guard holds names, links and
paths and no figure.

## Required Fix

- The counted-noun ban extended to `.claude/**/*.md` and
  `docs/contributing/*.md`: a bare count of files/tests/contracts/
  questions is red unless it is *derived* (the `UX-549` pattern) or
  carries a date and a command in the same sentence.
- The thirteen lines corrected or dated; §3.7 reads the versions from
  `bga/schemas.py` (the contracts guard's pattern); the tiers re-timed
  with the load average recorded; the verify skill's red-job route
  names `dev_junit_tail`.

## Out of Scope

- The measure skill's 813 / 311 KB / 40 s — needs a real build to
  re-measure; dated in place, re-measured by the next capture round.

## Acceptance Test

Mutation: type "421 task files" into researcher.md — red; restore
`analyze/v2` in §3.7 — red.
