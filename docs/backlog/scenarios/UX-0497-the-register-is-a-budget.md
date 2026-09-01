# UX-497: the register is a budget, not a preference

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** every session, on every file it reads; the maintainer's subscription | **Topic:** guards

## Motivation

Round 74 measured what a session reads and writes:

```text
CLAUDE.md + fixing guide + verify/falsify/measure skills   60,328 bytes, before the task file
task file, UX-0440..0496                       median 8,452 B   max 19,169 B   (n = 56)
Outcome section, same range                    median 114 lines max 284
module docstring, tools/dev_*.py + hooks       20..85 lines; 8 of 11 over 25
tools/dev_tier_drift.py                        206 comment lines over 46 of code
since round 64: tests +20,972  backlog docs +19,777  code +8,196 lines
```

Every one of those bytes is paid again by every later session that
opens the file, and the fixing guide's own budget line — "if you have
limited context, read only this file" — points at a 34 KB file. The
words are careful and the numbers are real; the *register* is the
cost. Nothing states a budget, so nothing holds one.

## Required Fix

- A **Register** section in `CLAUDE.md`, loaded every session, with
  the budgets as a table: module docstring ≤ 25 lines, Outcome ≤ 80
  lines from this item on, a comment is one line of why, a commit
  body ≤ 8 lines — and the sentence that carries the rule: the *why*
  is one sentence, the history lives in the task file and `git log`.
- `tests/unit/test_the_register_is_terse.py`: the docstring cap over
  the dev tools and hooks with a grandfather table that may only
  shrink (an entry whose file now fits is itself red), the Outcome
  cap over task files numbered from this one, and the numbers in
  `CLAUDE.md` held to the constants the guard enforces.
- `CLAUDE.md` stays within its 80-line guard; the skills line and the
  new section pay for themselves by folding two bullets.

## Out of Scope

- Bringing the eight grandfathered docstrings under the cap —
  `UX-502`, a refactor with a before/after.
- The Outcome *skeleton* `dev_close_task.py --outcome` prints — it
  still fits the cap when filled tersely; slimming its headings is
  `UX-506`.
- The fixing guide's own 34 KB — `UX-505`, the rules card.
- Comment density as a guarded number — a ratio of comment lines to
  code lines reads a proxy (§5); the docstring and Outcome counts are
  the two direct measurements, so the guard stops there.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_register_is_terse.py tests/unit/test_the_agent_configuration_holds.py -q
```

Green at HEAD; red under each of: a budgeted docstring lengthened past
25; a grandfathered docstring grown by one line; a grandfather entry
kept for a file that now fits; an Outcome over 80 lines on a task
numbered ≥ 497; a budget number in `CLAUDE.md` changed alone.

## Outcome (round 74, 2026-09-01) — 🟢 Done

### The gap, measured

```text
$ wc -c CLAUDE.md docs/contributing/fixing-guide.md .claude/skills/{verify,falsify,measure}/SKILL.md
60328 total                                  read before the task file
Outcome lines, UX-0440..0496 (n=56)          median 114   max 284
module docstrings over 25 lines              8 of 11 (tools/dev_*.py + hooks)
```

### After

`CLAUDE.md` carries the Register section at exactly 80 lines (the
guard's cap); the guard reads 11 modules, 8 grandfathered at their
round-74 counts, and every task file from this one on.

```text
$ python3 -m pytest tests/unit/test_the_register_is_terse.py tests/unit/test_the_agent_configuration_holds.py -q
89 passed in 1.65s
```

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| M1 | `dev_touching.py` docstring 22 → 28 lines | 1 failed, 26 passed |
| M2 | `dev_tier_drift.py` (grandfathered at 77) → 78 | 1 failed, 26 passed |
| M3 | `dev_perfetto_queries.py` cut to 5 lines, entry kept | 1 failed, 26 passed |
| M4 | an 86-line Outcome on this file | 1 failed, 26 passed |
| M5 | `CLAUDE.md` says ≤ 120 where the guard says 80 | 1 failed, 26 passed |

### Deviation from the Required Fix

The first draft skipped task files with no Outcome; a skip is a census
row (`UX-449`), so an unclosed file now simply passes — nothing to
measure yet.
