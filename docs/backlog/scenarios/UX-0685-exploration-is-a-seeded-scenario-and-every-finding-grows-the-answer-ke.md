# UX-685: exploration is a seeded scenario, and every finding grows the answer key

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-402 (the journey with an answer key), UX-664 (the walk skill), UX-665 (the page census) | **Serves:** R8 deciding whether the tool is in shape; the implementing session that gets a guard, not a transcript | **Topic:** guards | **Shape:** bounded

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
python3: can't open file '.../tools/dev_scenario.py': [Errno 2] No such file or directory
$ git show 7d6c9fa:.claude/skills/walk/SKILL.md | grep -n "^seed\|driving\|judging\|100k\|50k"
14:the driving. Round 77's control walk cost 336k tokens; the shape
15:below is what brings the next one under 100k.
```

No scenario tool existed; the walk skill named one cost ceiling
(100k) and no driving/judging split, no `seed` field, no `rows added`
field, and no guard read `docs/audits/` for either.

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
$ python3 tools/dev_scenario.py --seed 2 | head -8
scenario   seed=2
area       unassigned (14 tasks)
role       R8 — **The engineering lead** — owns where effort goes
...
$ python3 -m pytest tests/unit/test_a_scenario_is_named_by_its_seed.py -q
9 passed in 0.38s
$ python3 tools/dev_baseline.py --check
clean: 299 finding(s) match .../tests/quality_baseline.json
$ make test-touching
956 passed, 3 skipped, 1 failed (test_the_verification_log_is_true.py::
  TestTheLogIsNotStaleAboutItself::test_the_clause_below_has_commits_to_compare
  — confirmed pre-existing at base 7d6c9fa via a scratch `git worktree
  add --detach 7d6c9fa`, unrelated to this diff)
$ make lint
All checks passed! / clean: 299 finding(s)
```

Seeds 1 and 2 draw different areas, roles and classes (SHA-256 of
`seed:dimension`, not a shared PRNG stream — a shared stream coupled
`role` and `population` across seeds 1/2 in testing). The `walk`
skill now states driving (reporters' model, <100k) and judging (the
session's own model, <50k) as separate sections, each ending in the
report's `seed` and `rows added` fields.

### Mutations verified red and reverted

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `_pick` ignores the seed (`random.Random()`/fixed index) | `test_the_same_seed_reruns_identically` | 1 failed, 8 passed |
| M2 | `_pick` returns `options[0]` for every dimension | `test_two_seeds_draw_different_scenarios` | 1 failed, 8 passed |
| M3 | `report_problems` drops the `_SEED_LINE` check | `test_removing_the_seed_line_reds_the_guard` (the Acceptance Test's own mutation) | 1 failed, 8 passed |
| M4 | `report_problems` drops the `_ROWS_LINE` check | `test_removing_the_rows_added_line_reds_the_guard` | 1 failed, 8 passed |
| M5 | `is_walk_report` returns `True` unconditionally | `test_a_document_that_is_not_walk_shaped_is_left_alone` **and** `test_every_real_walk_shaped_document_names_its_seed_and_rows` (125 real docs/audits files flagged) | 2 failed, 7 passed |

All five reverted from the saved pre-mutation copy (never
`git checkout --`); `make lint` and the guard file are green after
each revert.

**No guard of mine failed to discriminate.** The first cut of
`is_walk_report` (`^capture\b` and `^findings\b`) matched two real,
unrelated documents (`round-41.md`'s prose, `architecture-review.md`'s
table cells) before it was tightened to four two-word compound labels
at their template alignment — a gap `test_every_real_walk_shaped_document_names_its_seed_and_rows`
(run against the real tree) caught before M5 confirmed the tightened
version discriminates.

### Deviation from the Required Fix
