# UX-586: the premise detector reads a proxy

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-508 (the process bands), UX-403 (the text-scan shape) | **Serves:** the round that reads the process bands | **Topic:** guards

## Motivation

```text
$ python3 tools/dev_process_bands.py --window 20
mutation reddened 80.0 % · non-discriminating guard 20.0 % · deviated 85.0 % · premise false 0.0 %
```

Round 81's own title is "seven premises falsified by measuring".
The detector is a regex (`dev_process_bands.py:47`:
`false premise|premise…(was|is) false`) and misses "the premise is
falsified" (`UX-542:46`), "premise was wrong" (`UX-556:61`),
"premise is half wrong" (`UX-541:53`) — shape 1 of fixing guide §5,
in the tool that measures the process.

## Required Fix

The premise fact becomes a declared line in the Outcome skeleton
(`Premise: held | falsified — <one line>`), written by `--outcome`
and read by the bands tool as a field, not a phrase; the twenty
Outcomes in the window annotated once so the reading is right from
here.

## Out of Scope

- The other three bands — their regexes read headings the skeleton
  already writes.

## Acceptance Test

`--window 20` reports ≥ 7 for round 81's rows; mutation: remove the
declared line from one Outcome — the skeleton guard reds.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held — the detector read 0.0 % of a window whose round's own summary line says seven.

### The gap, measured

```text
$ python3 tools/dev_process_bands.py --window 20 --json | tail -6   # at b100beb
  "recent": {"falsified": 16, "non_discriminating": 4, "deviated": 17, "premise_false": 0}
```

Zero of the last twenty, against `directions.md:1436` — *"round 81:
twenty-two rows, **seven** premises falsified by measuring"*. It missed
all seven, and they share no phrase to lengthen the regex with: "half
wrong" (`UX-541`), "is falsified" (`UX-542`), "neither candidate is the
shared thing" (`UX-546`), "falsified the premise it was filed on"
(`UX-551`), "the reader exists" (`UX-553`), "was wrong" (`UX-556`), "the
filing's own mechanism was wrong" (`UX-557`).

### After — a declared field, and 25 Outcomes annotated

`--outcome` writes `**Premise:** held | falsified — <one line>` and the
tool reads that line, not the prose around it. `UX-538`..`UX-562` were
annotated by hand, so round 81's rows are a window of 23:

```text
$ python3 tools/dev_process_bands.py --window 23 --json | tail -6
  "recent": {"falsified": 19, ..., "premise_false": 7, "premise_stated": 23}
$ python3 tools/dev_process_bands.py --window 23 | sed -n '7p;10p'
found the premise it was filed on false (of declared)  26.9%   30.4%
declares a Premise field at all       7.4%  100.0%   (26 item(s) of 351)
```

`directions.md`'s seven, derived rather than typed. The rule the 25
verdicts were read by is in the tool's comment: `falsified` is the
**Motivation's** claim not surviving measurement; a Fix option that
turned out unavailable is a *deviation*, the row above. The denominator
is the items that declare the field — a rate over 350 rows of which 325
cannot answer is the wrong population (§5, shape 4).

### Mutations verified red and reverted (8)

`PYTHONDONTWRITEBYTECODE=1`; each applied by a script that asserts the old text is there first.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | the `Premise:` line cut from `OUTCOME_SKELETON` | `..._the_printed_skeleton_declares_a_premise` | 1 failed, 1 passed |
| M2 | the skeleton pre-fills `falsified` first | `..._the_skeleton_pre_fills_no_verdict` | 1 failed, 1 passed |
| M3 | the old prose alternation back in the reader | `..._the_field_beats_the_prose_around_it` | 1 failed, 40 passed |
| M4 | `PREMISE_DECLARED` loosened to the bare word `premise` | 3 of the 4 real sentences read as declarations | 3 failed, 38 passed |
| M5 | the verdict read as `held` rather than `falsified` | both directions, all four written forms | 8 failed, 33 passed |
| M6 | the premise rate back over every closed row | `..._the_denominator_is_the_declared_rows`, 25.0 % against 50.0 % | 1 failed, 40 passed |
| M7 | the declared line deleted from `UX-0551` | `..._every_annotated_outcome_declares_its_premise[UX-0551]` | 1 failed, 40 passed |
| M8 | all seven `falsified` verdicts flipped to `held` | `..._the_reading_is_not_vacuous`, `assert 0 < 0` | 1 failed, 40 passed |

M3 matters most: under it the seven sentences still read as not
falsified — the 0 % reproduced inside a guard. **A guard of mine that
did not discriminate:** `..._is_not_vacuous` also asserted
`len(declared) >= 25`, so M7 reddened it *and* the per-file clause —
one fact, two reds. It claims only that both verdicts appear now.

### Deviation from the Required Fix

**One, and it is the Acceptance Test's own premise.** It asks
`--window 20` to report ≥ 7 for round 81's rows, and round 81 has 23 of
them: a 20-item window cuts `UX-541` and `UX-542`, the two the
Motivation cites. It reads 5 of 20; `--window 23`, round 81's rows
exactly, reads 7. So 25 Outcomes were annotated and not 20, and the
seven at the cap were rewrapped for the room — no word moved.

```text
$ python3 -m pytest tests/unit/test_the_register_is_terse.py -q  112 passed
$ HEAD vs worktree, words less the added line, 25 files:  0 changed
$ make test-touching   17 file(s) selected · 501 passed, 3 skipped in 14.92s
$ make lint            ruff + PyMarkdown, All checks passed!
```

New file `test_the_premise_is_a_declared_field.py` (41 clauses, 0.43s)
needs a **small** tier row; `tiers.py`, `ci_reference.json`, the row move
and the suite gate are the orchestrator's.
