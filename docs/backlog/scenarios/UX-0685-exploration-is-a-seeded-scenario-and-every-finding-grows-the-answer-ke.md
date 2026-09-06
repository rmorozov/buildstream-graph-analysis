# UX-685: exploration is a seeded scenario, and every finding grows the answer key

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-402 (the journey with an answer key), UX-664 (the walk skill), UX-665 (the page census) | **Serves:** R8 deciding whether the tool is in shape; the implementing session that gets a guard, not a transcript | **Topic:** guards | **Shape:** bounded

## Motivation

Hand exploration finds a problem almost every time, and the suite
does not, for a structural reason: 472 files in `tests/unit/` are one
claim each, and three files are journey-shaped (`test_e2e.py`,
`installed_command_sweep.py`, `test_the_journey_has_an_answer_key.py`).
A claim is true the moment it is written; a reader meets the page in
sequence, on a real capture, after twenty other changes landed. The
journey guard holds three planted defects and has not grown since
round 64; every walk since (63, 77, 87, 90) re-derived its own
protocol and paid for it (336k tokens in round 77).

## Required Fix

- `tools/dev_scenario.py --seed N`: draws a scenario from the area
  index (`UX-688`) crossed with the input classes the `decompose`
  skill names (population, contract version, capture mode, Plane 2
  presence, reader, host) and a role, and prints the scripted walk:
  the capture recipe, the commands, the page controls to drive (from
  the census, `UX-665`), the report shape. The seed is the scenario's
  name, so it reruns.
- The `walk` skill runs it in two halves on two models: the
  *driving* half (capture, export, census, drive one control per
  class, diff against the answer key) on the reporters' model; the
  *judging* half (is this the guide's promise, what rule follows) on
  the session's model, over the report and never over the page. The
  ledger row for each half is the cost target: driving under 100k,
  judging under 50k.
- Every finding a walk files adds a row to the journey's answer key
  in the same round (`test_the_journey_has_an_answer_key.py` gains a
  planted case or an assertion), so the next walk with the same seed
  starts from what is held. A guard: every walk report in
  `docs/audits/` names its seed and the answer-key rows it added.

## Out of Scope

- Replacing the guards with walks — the suite verifies what was
  built; the walk verifies what was promised; both stay.
- A calendar cadence — `UX-686` ties the walk to the release.

## Acceptance Test

Two walks with seeds 1 and 2 drive different areas and classes; a
finding from seed 1 becomes an answer-key row and the seed-1 rerun
reports it held; the two ledger rows sit under the targets.
Mutation: remove the seed line from a report — the report guard reds.

## Outcome

### The gap, measured

```text
$ python3 tools/dev_scenario.py --seed 1
python3: can't open file '.../tools/dev_scenario.py': No such file or directory
$ git show 7d6c9fa:.claude/skills/walk/SKILL.md | grep -c "seed\|judging"
0
```

No scenario tool existed; the skill named one cost ceiling (100k) and
no driving/judging split, no `seed` field, no `rows added` field, and
no guard read `docs/audits/` for either.

### The close, measured

```text
$ python3 tools/dev_scenario.py --seed 1 | head -8
scenario   seed=1
area       bga/replay (1 tasks)
role       R7 — **The release manager** — owns dates
Plane 2           absent
capture mode      cold
contract version  current
host              CI only (verify §7)
population        1
$ python3 -m pytest tests/unit/test_a_scenario_is_named_by_its_seed.py -q
11 passed in 0.38s
$ make lint          All checks passed!
```

### Mutations verified red and reverted

| # | mutation | reddened |
|---|---|---|
| M1 | `_pick` ignores the seed | `..._the_same_seed_reruns_identically` |
| M2 | `_pick` returns `options[0]` always | `..._two_seeds_draw_different_scenarios` |
| M3 | `report_problems` drops the seed check | `..._removing_the_seed_line_reds_the_guard` (the item's own mutation) |
| M4 | `report_problems` drops the rows check | `..._removing_the_rows_added_line_reds_the_guard` |
| M5 | `is_walk_report` always `True` | the discrimination clause **and** the real-tree scan, 125 files flagged |

**One guard did not discriminate at first.** `is_walk_report` cut on
`^capture\b`/`^findings\b`, matching `round-41.md`'s prose and
`architecture-review.md`'s cells; the real-tree clause caught it before
M5 did. Four two-word labels at their template alignment now.

### Deviation from the Required Fix

*The seed is a hash, not a PRNG.* `random.Random(seed)` is S311 and
the baseline refuses a new finding (`UX-705`), so the draw is SHA-256
of `seed:dimension` - also the better mechanism, since a shared stream
coupled `role` and `population` across seeds 1 and 2.

*The walk half was run after the track, and the ledger targets are
**missed**.* Two walks, `docs/audits/walk-seed-{1,2}.md`. Seeds 1 and 2
drew different areas, roles and classes as the Acceptance Test asks;
three findings became `UX-723`, `UX-724`, `UX-725`, and each seed added
an answer-key row. But:

```text
seed 1 driving   156,932 tokens    target < 100,000   +57%
seed 2 driving   121,690 tokens    target < 100,000   +22%
```

The targets stand as written and are not met. They came from round
77's 336k against a walk that re-derived the census by hand; the census
exists now and both walks used it, so what is left is the capture.
Whether 100k is reachable is the next walk's measurement, not a number
to move here.

*The answer-key rows record gaps, not rules.* Neither finding is fixed
this round, so a row asserting the promise would be red; each asserts
what the walk **measured** and names the item whose close reddens it.
Seed 1's row sits in `test_a_scenario_is_named_by_its_seed.py`, not the
journey's key - that finding is about the walk's tooling, not a build
report's promise. And it was the *first* thing seed 1 found:
`dev_scenario.py` had nine passing clauses and none ran a command it
prints.
