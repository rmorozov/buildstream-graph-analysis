---
name: measure
description: The recipes this repository re-derives every round - regenerating the golden snapshot, building the 1,202-element synthetic run, measuring the exported report's size, and re-timing the test tiers. Use when a claim needs a number rather than an adjective.
---

# measure

Every claim here is a pasted measurement (style guide rule 4,
[`docs/contributing/style-guide.md`](../../../docs/contributing/style-guide.md)).
These are the four that get rediscovered from a docstring each round.

## The golden snapshot, after a deliberate behaviour change

```bash
PYTHONPATH=. python3 -m bga.cli analyze \
    "$PWD/tests/fixtures/golden/mixed_task_kinds" \
    --format json --diagnostics \
  | sed "s|$PWD/tests/fixtures/golden/mixed_task_kinds|<run>|g" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("run_instance", None); d.pop("producer", None); print(json.dumps(d, indent=4))' \
  > tests/fixtures/golden/mixed_task_kinds/expected_output.json
git diff tests/fixtures/golden/mixed_task_kinds/expected_output.json
```

The absolute path and the `<run>` rewrite are both load-bearing —
`tests/test_golden.py::_run_analyze` does exactly this, and a recipe
that skips either writes a snapshot the test can never match. So is
dropping `run_instance` and `producer` — both name the machine or the
build rather than the analysis. Then read the diff and confirm the change you
intended is the *only* one.

## A run at scale, byte-reproducible

```bash
bga gen-synthetic /tmp/scale --seed 1     # 1,202 elements, deterministic
bga analyze /tmp/scale --diagnostics
```

The seed makes it reproducible across machines, which is what lets one
round's figure be compared with another's. Round 2 found four defects
at this scale that were invisible at eleven elements.

## What the exported report weighs

```bash
bga view /tmp/scale --export /tmp/report.html
wc -c /tmp/report.html
```

Two numbers matter and they are different: the **page** (the
hand-written modules plus the stylesheet) and the **data** (the
embedded JSON). `tests/unit/test_the_report_you_can_attach.py` splits
them by stripping the `<script type="application/json">` blocks. The
backstop on the golden export is a measurement, so when it moves, say
which half moved — a composition guard exists precisely so the ceiling
cannot be raised without one.

## Re-timing the tiers

```bash
python3 -m pytest tests/ --durations=0 -q
```

Sum setup+call+teardown per file; a file above `LARGE_FLOOR_S` is
large, above `MEDIUM_FLOOR_S` is medium, and everything else is small
by default. The floors and both lists are in
[`tests/tiers.py`](../../../tests/tiers.py). **A file moves tier when
its measurement moves, not when it feels slower** — re-measure before
editing either list.

Timing the suite itself:

```bash
time make test-small
time make test
```

## When you quote a number

Name the command and the fixture that produced it, in the sentence. "a
33% spread across five captures of the same freedesktop-sdk commit" can
be re-checked in three years; "roughly 5% run-to-run noise" cannot, and
this repository has already been wrong that way — the same list at n=3
supported a 5.8% figure that four documents quoted.

## Before you trust the number: what is it a number *of*?

The instrument is the thing this repository gets wrong most often. A
round-68 sweep of the backlog, the guards and the design documents
found about thirty sightings across about twenty-six items of one
defect — **an instrument reading a proxy rather than the thing it
names**. The fixing guide's §5 states it as a rule; this is where it
gets asked, because the mistake is made while writing the measurement
and is invisible when reading it back.

Three questions, in order:

1. **What quantity does this actually read?** Not what it is called —
   what the code touches. `UX-204`'s page-size guard summed every file
   in `bga/viewer/`, including two an export never carries.
2. **Is that the quantity the name claims?** `UX-296` read
   `ru_maxrss` in a subprocess, which returns the *parent's* high-water
   mark: a 10 MB child reported 411 MB.
3. **At the magnitudes it will see, can it tell the answers apart?**
   A ratio of two hundredth-of-a-second numbers cannot. Measured on two
   runs of this suite at one commit, a file under 0.1s ran **×4.21** its
   own time with nothing changed (`UX-423`).

The four shapes, so you can recognise yours:

| shape | the tell | worked example |
|---|---|---|
| a text scan that cannot tell code from data | a longer regex keeps almost working | `UX-403` |
| a ratio at the noise floor | the operands moved by different factors | `UX-420`, `UX-422` |
| a comparison across machines | "it passed on mine" | `UX-418` |
| the wrong artifact or population | the number is real, its subject is not | `UX-359` |

**A guard you only read is a guard you have not checked.** Every one of
those was found by running something — a mutation, a second machine, a
census — and none by re-reading the code. See the `falsify` skill.
