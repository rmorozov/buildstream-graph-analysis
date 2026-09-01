# UX-486: a committed analysis fixture drifts from the analyzer, and one clause out of many noticed

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 73, closing `UX-469` | **Serves:** the round whose guards pass against an analysis the current code would never emit | **Topic:** guards

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

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, from the instrument that now reports it

```text
python3 tools/dev_refresh_analysis.py

  ok    tests/fixtures/golden/mixed_task_kinds
  DRIFT tests/fixtures/with_timeline
          findings: committed ['wait-category', 'time-concentration',
              'mesh-graph', 'joint-saving', 'optimization-horizon',
              'latent-heavies', 'cache-hit-ratio', 'confidence',
              'efficiency-score']
            analyzer  ['wait-category', 'time-concentration', 'chain-graph',
              'blast-radius-reach', 'blast-radius-structural', 'graph-width',
              'joint-saving', 'optimization-horizon', 'latent-heavies',
              'cache-hit-ratio', 'confidence', 'efficiency-score']
          document_shape: differs
          headline: differs
          provenance: differs
          readers: differs
1 of 2 committed analysis document(s) disagree with the analyzer
```

The golden reads `ok` **on the first run of the new tool**, which is
the check that matters: the rule was reconstructed from three scattered
copies and it reproduces a snapshot nobody touched, byte for byte.

### After

```text
python3 tools/dev_refresh_analysis.py --write tests/fixtures/with_timeline
python3 tools/dev_refresh_analysis.py

  ok    tests/fixtures/golden/mixed_task_kinds
  ok    tests/fixtures/with_timeline
0 of 2 committed analysis document(s) disagree with the analyzer
```

### The rule, once

`tools/dev_refresh_analysis.py` owns what a committed analysis holds:
`run_instance` (`UX-95`, the capture and the machine), `producer`
(`UX-249`, which build of bga), and the fixture's own path — rewritten
to a token because `UX-218`'s next-step commands name the run
directory, and the commands are still compared. It was in three places
before — a shell pipeline in `tests/test_golden.py`'s docstring, a
Python helper below it, and a third copy in the `measure` skill — and
the fixture that had none of them is the one that drifted.

`tests/test_golden.py` calls the tool now rather than carrying its own
copy, so the two committed analyses are compared under one rule; the
`measure` skill's recipe is the command.

### Deviation from the Required Fix

- **The refreshed file is re-indented**, 2 spaces to 4, which is most
  of a 2,956-line diff. Not cosmetic drift for its own sake: it is what
  makes the two committed analyses the same shape, written by the same
  writer, so the next refresh of either is a content diff. Said here
  because a reviewer seeing 1,541 insertions should know 1,415 of them
  are the same lines re-indented.
- The item asked for "a guard that compares the file's finding ids with
  the analyzer's". The guard compares the **whole document** and
  *reports* the finding ids first, because the ids are the shape a
  reader can check at a glance and everything else is what a golden
  test is for.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| R1 | `MACHINE_KEYS = ()`, so the machine's own keys stay in | 3 of 8 — both fixtures' drift clauses and the golden snapshot |
| R2 | the fixture's path is not rewritten to its token | 3 of 8 — the same three |
| R3 | `differences` stops comparing finding ids | 1 of 8 — `test_a_missing_finding_is_named_rather_than_counted` |

Each was proved to have landed with a `grep -c` before the run, and
reverted from a copy after it.

### Two clauses this moved, and one row it found

- `test_an_artifact_says_what_wrote_it.py` asserted the producer stamp
  is dropped by **grepping `tests/test_golden.py` for the line that
  pops it**. The pop moved, so the clause is re-pointed at
  `MACHINE_KEYS` — read from the module rather than scanned out of a
  file, which is one fewer text scan reading a proxy for a rule.
- `test_a_guard_reads_only_what_a_clone_has.py` refused the new guard
  while `dev_refresh_analysis.py` was still untracked. Working exactly
  as designed, and worth recording as a sighting rather than a nuisance.
- `test_the_journey_has_an_answer_key.py::test_the_first_thing_to_fix_is_core`
  went red once during this work, on a real build under `-n auto`
  load — `assert 'lib-c.bst' == 'core.bst'` — and passed three times
  after, once with the diff stashed. It asserts an exact first place
  with no margin over a live build. Filed as `UX-489`; not touched here.

### The runs

```text
python3 -m pytest tests/unit/test_a_committed_analysis_matches_the_analyzer.py \
                 tests/test_golden.py -q          8 passed in 1.73s
make test-touching                                595 passed in 62.79s
make test                                         5,675 passed, 27 skipped
                                                  in 322.39s (0:05:22)
make lint                                         ruff + PyMarkdown, clean
```
