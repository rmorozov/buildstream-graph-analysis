# UX-551: every session plans its loop against a suite 62% faster than the real one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the tiers), UX-500 (which measured it) | **Serves:** the implementing session's wall clock | **Topic:** docs

## Motivation

Architecture review 12, checklist 3. `CLAUDE.md` line 16 is the first
table a session reads:

```text
| `make test` | the whole suite, ~5m30s at `-n auto`. **Required …** |
```

Measured this round, same container, `make test` at `-n auto`:

```text
claimed  (round 74)   ~5m30s ·  5,635 passed, 81 skipped, 328s
measured (round 80)    8m52s ·  6,181 passed, 29 skipped, 532.74s
                       tests +546 · skips 81 → 29 · wall 1.62x
```

`docs/contributing/fixing-guide.md:58` and `.claude/skills/verify`
carry the same figure and both **date** it ("round 74"), so by reviews
5 and 7's precedent those are records. `CLAUDE.md`'s is undated and
reads as current — the exact shape `UX-471` removed from that file.

It is not cosmetic: `UX-500` decided this round that the suite runs
once per item, so a session budgets its round against this number, and
the number is out by three and a half minutes per run.

## Required Fix

Re-measure and restate, dated. `CLAUDE.md` is a summary, so the figure
either carries its round the way the guide's does, or points at the
guide rather than repeating it — one copy is the standing preference.

Note the skip count as well as the wall clock: 81 → 29 is `UX-449`'s
census retiring skips, and a document that quotes one and not the other
describes a suite that never existed.

## Out of Scope

- Making the suite faster; `UX-336` did the parallel half and the
  question here is what the documents say, not what it costs.
- The tier floors — `tests/tiers.py` is measured per file and current.

## Acceptance Test

`CLAUDE.md`'s figure matches a pasted `make test` line from the round
that wrote it, or names no figure at all.
