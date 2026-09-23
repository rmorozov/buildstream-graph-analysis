# UX-999: a weekly retro turns repeated bookkeeping into automation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-998 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 15:11: "for any kind of bureaucracy automation is always is right way to solve the problem" | **Serves:** every later round, through the bookkeeping it no longer files | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

The run ledger's friction column is free prose: 276 of 350 rows fit none
of the eight recurring themes a keyword sweep finds, and rounds 132, 133,
135 and 137 have no rows at all, so the process cannot read its own cost.
Bookkeeping recurs by class (derived counts, census bounds, slug markers),
and each class has so far been fixed one instance at a time.

## Required Fix

A `retro` skill and a weekly routine that runs it. It reads the
bookkeeping ledger (`UX-998`), the run ledger and CI history, groups
repeated lines by class, and for the top classes proposes the tool, hook
or derivation that removes the class. The proposals go to the `architect`
as optimization rows (exempt from `UX-994`'s cap). Its one metric is
bookkeeping lines filed per week, which should fall.

## Out of Scope

Implementing any proposal the retro makes.

## Acceptance Test

To be named by the `architect`'s Decision.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     new tools/dev_retro.py: --since defaults to the newest docs/audits/retro-YYYY-MM-DD.md
           date, else 7 days back; reads only lines ADDED since then (git log -p --since) to
           docs/backlog/bookkeeping.md, agent-runs.md's friction cell, and the Decision
           Class:/Guard: of rows turned 🟢 in the window; class key = the first
           tools/dev_*.py, tests/unit/test_*.py or `make <target>` token; prints classes by
           count, the unclassed share, and bookkeeping lines per ISO week; never commits.
           New .claude/skills/retro/SKILL.md runs it, counts failed main runs when gh answers,
           writes docs/audits/retro-<date>.md (table + command, up to 3 proposals marked
           optimization) and opens a `retro: <date>` PR. After merge the session creates a
           weekly routine (cron 0 7 * * 1): "run the `retro` skill and open its PR".
Rejected:  the routine files task files itself - an unattended id races a live session
           keyword themes - 8 themes leave 276 of 350 friction rows unclassed
           re-read the whole ledger - re-counts old lines
           parse UX-998's line format - not fixed yet; would serialise the rows
           an Actions cron - a workflow cannot run a skill, and none pushes to main (UX-997)
Files:     tools/dev_retro.py; .claude/skills/retro/SKILL.md;
           tests/unit/test_a_retro_groups_bookkeeping_by_the_command_that_shows_it.py;
           tests/unit/test_the_skills_point_at_the_guides.py (OWNERS: retro -> fixing-guide);
           CLAUDE.md (the pipeline names `retro`)
Guard:     the new test, on a temp repo with commits both sides of --since: pre-window lines
           uncounted; one finding as list item and table row -> one class; no token ->
           unclassed; a line moved within the ledger is not filed twice; --since defaults to
           the newest retro document
Mutation:  drop --since from git log; key = first backtick span; drop the unclassed row;
           count removed lines as filed; default to 7 days despite a retro document;
           delete `retro` from CLAUDE.md (reddens the existing skill guard)
Class:     bookkeeping - cuts no cost itself; the rows it proposes are the optimization
Split:     one bounded track, parallel with UX-998 (seam: a ledger line names its command)
Question:  none
```
