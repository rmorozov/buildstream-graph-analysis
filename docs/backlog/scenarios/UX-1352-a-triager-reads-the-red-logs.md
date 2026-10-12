# UX-1352: a `triager` reads the red logs so the session reads a table

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1351 | **Found by:** the Haiku 5.5 workflow review, 2026-10-10 — Ruslan in the project thread, 15:45 | **Serves:** every round's gate and every CI red on a round's pull request | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_agent_configuration_holds.py::TestTheSubagentsAreWellFormed::test_the_triager_reads_on_haiku_and_an_undecided_red_is_real`

## Motivation

`CLAUDE.md` says the session reads reports, never logs. Nobody owns the
reading of a red one: `make push-check` output, a CI job's log tail (the
API caps it at 5,000 lines) or a PR's CI event. Round 170's UX-1327
track: "environmental reds (missing records) buried 5 real ones among
119". Sorting a log's reds is high-volume classification, which Haiku 5.5
was built for; a log chunk stays under its 100K-token card.

## Required Fix

A `.claude/agents/triager.md` on `model: haiku` at `effort: medium`,
read-only. Given a log or a command to run, it returns one table: each
failing test or step, its class (environmental / flake / real), and the
log line that decides it, with a count per class. It fixes nothing and
re-runs nothing beyond what the brief names. The `decompose` skill names
it where the session would otherwise open a log.

## Out of Scope

Fixing a red. Re-running CI.

## Acceptance Test

Rebuild round 170's shape in a worktree: no ignored records copied
(the environmental class) and two planted real reds. Run on that
worktree's `make test-touching` log, the triager names both planted
reds as real and classes the rest environmental, priced by `UX-1351`'s
cost cell.

## Outcome (round 174, 2026-10-12) — 🟢 Done

**Premise:** held. Nobody owned the reading of a red log; the session
read it, and round 170's five real reds sat among 119.

### The gap, measured

```text
$ ls .claude/agents/   # at 1038a41a
architect.md closer.md guard-auditor.md implementer.md integrator.md researcher.md verifier.md walker.md
```

No agent reads a log, and the `decompose` skill sends none there.

### After

`.claude/agents/triager.md` (haiku, medium, `Read, Grep, Glob, Bash`, on
`REPORTERS`) classes each failure environmental / flake / real with its
deciding line; an undecided one is real. `decompose` names it beside the verifier.

Acceptance, round 170's shape: a worktree at `a24982f3` with no records
fetched and two planted reds (`CLAUDE.md` "all four" on push; the
pull-request cell moved to `3.14`), 14 files at `-n 2`:

```text
33 failed, 456 passed, 3 skipped in 42.49s            (405-line log)
triager: environmental 25, flake 0, real 8 (33 total)
| 174 | general-purpose | haiku-5-5 | UX-1352 acceptance ... | 78k | 4 | 0.6 m | $0.01 | ...
```

The key: 25 read a missing `ci_reference.json` or `touch_map.json`; 8
are real - the 4 the plants redden, plus 4 from this round's own
unfinished tree (the rules-card slug and census, which `a24982f3` then
fixed, and `triager` not yet on `REPORTERS` there). It named all 8 real,
each with the assertion line, and none of the 25 as real.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `model: haiku` -> `model: sonnet` | the triager clause, 1 failed |
| A2 | an undecided red classed **flake** instead of **real** | the triager clause, 1 failed |
| A3 | `**Fix nothing.**` -> `**Read and class.**` | `test_a_reporter_is_never_put_on_the_editing_list` |
| A4 | `decompose`'s "the `triager` reads a red" reworded | the triager clause, 1 failed |
| A5 | `Edit` added to `tools:` | `test_a_reporting_agent_cannot_edit_the_tree` |

A2 first passed: the sed missed a sentence wrapped across two lines.
Re-applied on the wrapped line, it reddened.

### Deviation from the Required Fix

The live run was `general-purpose` on haiku at medium, briefed with
`triager.md`'s body: an agent type added mid-session is not offered until the next.
