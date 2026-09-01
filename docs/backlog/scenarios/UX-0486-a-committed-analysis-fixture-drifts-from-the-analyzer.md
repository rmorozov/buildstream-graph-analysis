# UX-486: a committed analysis fixture drifts from the analyzer, and one clause out of many noticed

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 73, closing `UX-469` | **Serves:** the round whose guards pass against an analysis the current code would never emit | **Topic:** guards

## Motivation

`tests/fixtures/with_timeline/analyze.json` is a committed
`analyze/v4` document, and several guards read it as the analyzer's
output. It is not: it is one old run of the analyzer, frozen.

Measured by re-running `bga analyze` over the fixture's own `run/`
this round, and comparing findings by id:

```text
ids in the committed file
  wait-category, time-concentration, mesh-graph, joint-saving,
  optimization-horizon, latent-heavies, cache-hit-ratio, confidence,
  efficiency-score

ids the analyzer emits today
  wait-category, time-concentration, chain-graph, blast-radius-reach,
  blast-radius-structural, graph-width, joint-saving,
  optimization-horizon, latent-heavies, cache-hit-ratio, confidence,
  efficiency-score
```

Four findings this round added (`UX-479`, `UX-475`, `UX-478`) reach
this fixture and are not in it, and one it does carry — `mesh-graph` —
is a verdict `UX-475` re-decided: on this run the analyzer now says
`chain-graph`. Every guard reading the file is reading a report
`bga` no longer produces.

Nothing said so. The clause that finally spoke was
`test_a_finding_reaches_the_timeline.py::test_a_finding_the_table_answers_carries_its_query`,
and only because `UX-469` changed the *query* a finding carries — a
field it compares against live code. Nothing compares the file's
**shape** with what the analyzer emits, so four new findings arrived
in silence.

Whole-file regeneration is why: the analyzer writes `producer` and
`run_instance`, which name the machine and the run, and an absolute
path inside `copy_text`'s `Next:` line. So a contributor who
regenerates commits their own hostname, and the obvious fix is the one
nobody does.

## Required Fix

- **A rule for what a committed analysis fixture holds**, written
  where a contributor regenerating one will read it: which keys are
  the fixture and which are the machine, and the `<fixture>` path
  rewrite `tests/test_golden.py::_run_analyze` already performs for
  the golden snapshot.
- **The regeneration as a command**, beside `tools/dev_close_task.py`
  — the golden snapshot has a recipe in the `measure` skill and this
  fixture has none, which is the whole reason it drifted.
- **A guard that compares the file's finding ids with the analyzer's**
  on the same run, so an item that adds a finding is told in the same
  commit rather than four items later.

## Out of Scope

- `wait-category`'s `trace_query`, which `UX-469` corrected in place
  rather than regenerating the file around it — that is the one field
  a clause could already see.
- `tests/fixtures/golden/mixed_task_kinds/expected_output.json`, which
  has a recipe, a guard that runs it and a rewrite for the path. It is
  the shape this row wants for the other fixture, not a thing to fix.

## Acceptance Test

```bash
python3 -m pytest tests/unit/<the new guard>.py -q
```

red on the fixture as committed today, green after a regeneration
that carries no hostname and no absolute path, with the finding-id
comparison pasted before and after.

## Outcome

_Not started._
