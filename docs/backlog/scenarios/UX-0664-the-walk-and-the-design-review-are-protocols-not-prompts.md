# UX-664: the walk and the design review are protocols, not prompts

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-240 (procedures as skills), UX-499 | **Serves:** the orchestrating session paying for an audit | **Topic:** docs

## Motivation

Rounds 45, 63, 64, 77 and 87 each ran an outsider walk from a prompt
written that day, and rounds 44, 63 and 77 each judged the page's
look from a description of it. The prompts converged — stranger
rules, an answer key, one capture with every plane, drive one control
per class, a fixed report — and were never written down, so each
round re-derived them and paid for a transcript-shaped result
(round 77's control walk: 336k tokens).

## Required Fix

Two skills: `walk` (the protocol above, report ≤ 80 lines, owned by
the fixing guide's audit stream) and `design-review` (seven fixed
screenshots read by a subagent that can see them, measure → judge
against the styleguide § and a short list of craft questions →
propose as a rule with its guard, report ≤ 140 lines, owned by the
styleguide), both registered with the skills guard and named in
`CLAUDE.md`.

## Out of Scope

- The census tool the walk reads — `UX-665`.
- Running either skill's protocol in this task — round 90's design
  review is its first run, recorded in the round document.

## Acceptance Test

Both skills load (`test_the_skills_point_at_the_guides.py` and the
description trigger clause green); each names its owning guide.

## Outcome (round 90, 2026-09-05) — 🟢 Done

### The gap, measured

```text
skills before          7   (orient decompose measure falsify verify derive review)
walk prompts written   5 rounds, none reusable; control walk 336k tokens (round 77)
```

### After

```text
$ ls .claude/skills
decompose derive design-review falsify measure orient review verify walk
$ python3 -m pytest tests/unit/test_the_skills_point_at_the_guides.py tests/unit/test_the_agent_configuration_holds.py -q
214 passed
```

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| M1 | `walk` loses its link to the fixing guide | `test_it_points_at_the_guide_that_owns_the_rule[walk]` — 1 failed (seen on the first install, before the link was added) |

### Deviation from the Required Fix

None. The first `design-review` run's cost is in the ledger's round-90
rows.
