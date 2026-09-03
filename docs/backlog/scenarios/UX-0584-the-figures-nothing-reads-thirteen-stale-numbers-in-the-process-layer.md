# UX-584: the figures nothing reads — thirteen stale numbers in the process layer

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-471 (the count removed from CLAUDE.md), UX-505 (the card), UX-551 (the suite figure) | **Serves:** every session's first read | **Topic:** docs

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

## Outcome (round 83, 2026-09-03) — 🔴 handed back for the close

### The gap, re-measured on `5b4c05f` — twelve rows, not thirteen

```text
guide §3.7   analyze/v2,compare/v1,blast/v1  schemas.py: v5 / v2 / v2  STALE
guide:69,74 · verify:33 · tiers.py  11 s / 8.6 s  20.5 s, 3,698 tests  STALE
researcher.md:5,19   421 task files       589 (the Motivation says 560) STALE
verify:130           380 files            426                          STALE
decompose:50-60      "Three files"        four paths listed            STALE
decompose:87-92      1.33, "the only one  round-76.md:135 1.43;         STALE
                      on file"             round-80.md:23 1.83
measure:117          fourteen questions   reads "seventeen"; 17    ALREADY FIXED
rules:6 · guide:6    34 KB                40,796 B                     STALE
style-guide.md:15-17 "Two ... by test"    4 close **Enforced by test**  STALE
release-guide.md:23  twelve contracts     23 ids, 14 live              STALE
verify:99-118        no dev_junit_tail    confirmed absent             STALE
```

Two premises falsified: the question-count row **was already closed**
by `UX-576` this round, and "thirteen" over-counts a twelve-row block.
A **thirteenth**, unlisted, sits on the line the fix cites:
`fixing-guide.md:105` said Part 32 spans **1515-1788**; its own
headings give **1515-1888**.

```bash
$ uptime; time make test-small
 15:35:41 load average: 0.13   3698 passed, 36 skipped in 20.46s  real 0m20.8s
$ uptime; time make test-medium      # other worktrees running
 15:36:29 load average: 1.05   2289 passed in 172.53s             real 2m52.8s
 15:47:46 load average: 17.16  the same tier, saturated            real 12m22.8s
$ uptime; time make test-large
 15:39:27 load average: 6.02    558 passed in 125.94s             real 2m6.2s
```

One tier, **2m53s at load 1.05 and 12m23s at load 17.2** — 4.3x.

### The close, measured

```bash
$ python3 -m pytest tests/unit/test_the_process_documents_derive_their_figures.py -q
12 passed in 0.32s
$ make test-touching
27 file(s) selected · 624 passed, 3 skipped in 36.18s
$ make lint
All checks passed!
```

### Mutations verified red and reverted (6)

| mutation | reddened | run |
|---|---|---|
| `421 task files` back into `researcher.md` | `test_every_count_is_derived_or_pinned` | 1 failed |
| `analyze/v2` back into §3.7's pinning clause | `test_the_guide_pins_a_version_that_is_not_superseded` | 1 failed |
| a path dropped from decompose's hotspot block | `..._carries_the_derived_sentence[decompose, implementer]` | 2 failed, 5 passed |
| `426 rows` typed into the verify skill | `test_the_verify_skill_no_longer_counts_the_reference` | 1 failed |
| the derived `Four` retyped as `Two` | `..._carries_the_derived_sentence[style-guide]` | 1 failed |
| the scan's population aimed at a dead path | `test_the_ban_reads_a_non_empty_population` | 1 failed, 1 passed |

### Two guards that did not discriminate

1. **Mutation 1 passed green first time.** The splitter did not break
   before `(`, so the parenthetical citing `UX-584` merged with the
   sentence above and `PINNED` exempted it — the guard matching its own
   explanation. Splits on `(` and `"` now.
2. The style guide's count read `**Enforced by test` over the whole
   file, counting the header sentence *stating* it: five, not four.
   Reads below `## 1.` only — rules are the subject, header the argument.

### Deviation from the Required Fix

- `tests/tiers.py` **not edited** (merge hotspot); readings above.
- The measure skill's 813 / 311 KB / 40 s stay undated: no date is on
  file for them and inventing one is this item's own defect.
- `test_docs_links_and_commands.py:808` types `assert "analyze/v2" in
  guide` — another track's file, so §3.7's history clause keeps the
  literal. That guard should derive it. **Needs a row.**
- `UX-505`'s Outcome says `34,400 B` (now 41,358): a dated measurement
  of a closed item, so this Outcome is §3.6's annotation.
