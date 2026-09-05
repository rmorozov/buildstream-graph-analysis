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
