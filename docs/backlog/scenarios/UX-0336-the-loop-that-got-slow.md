# UX-336: the loop that got slow, measured and re-tooled

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-238 (the tiers this extends), the verify/falsify/measure skills | **Serves:** the maintainers — every future round's throughput | **Topic:** guards

## Motivation

The user's observation: the implementing session slows down as the
code and suite grow — and the numbers agree. The suite is 4,000+
tests at ~6 minutes single-process; each task's ritual (guards,
mutation records, row moves, log writing) has fixed costs that
were designed at half this size; and the two largest viewer
modules are long enough that every edit pays a long read. Round 46
measured the levers — and the trial already ran: `pytest-xdist -n auto` on this
4-core container takes the full suite from **~375 s to 148.7 s
(2.5×), 4,014 passed, zero failures, zero races** — every server
already binds ephemeral ports, so the adoption cost measured
*zero* (one caveat: the 94-skip census should be diffed against a
single-process run once). Meanwhile the "fast" tier is not:
small+medium is 3,849 tests at **335 s wall** — five and a half
minutes is nobody's inner loop. The browser walks are already
frugal (three files, one shared Chromium each, ~20 % of
single-process time); the slow tail is the scale files
(`test_the_page_has_geometry` 61.7 s, the spine pair 62.7 s
together, memory-shape 24.6 s).

## Required Fix

Five levers, each cheap and additive:

1. **The suite runs in parallel.** `pytest-xdist` joins the dev
   extras with the measured result above; the one adoption step
   left is diffing the skip census against a single-process run.
   The tiers stay; `-n auto` becomes how every tier runs — the
   full suite lands at ~2.5 minutes.
2. **A change-scoped inner loop.** `make test-touching` maps the
   working diff to the test files that import or name the touched
   modules (grep-derived, no new machinery) — the inner loop runs
   seconds of tests, the full suite runs once before commit, as
   the verify skill already prescribes.
3. **The fast tier becomes fast again.** small+medium at 335 s is
   a mis-tiering, not a law: re-tier by the fresh measurement (the
   UX-238 method, re-run), with the scale files and browser walks
   in the once-per-close tier — under xdist the inner tier should
   sit near 30 s.
4. **The close ritual is scaffolded.** A `close-task` helper
   generates the Outcome skeleton, the mutation-record table, and
   the row move — the mechanical tail of every task stops being
   hand-typed (the verify skill documents what it generates).
5. **The two largest viewer modules split along chapter seams** —
   page-cost neutral (the export inlines either way), edit-cost
   real: smaller files, fewer collisions, shorter reads. The
   module-map guard (UX-294) keeps the map true.

## Out of Scope

- Deleting or weakening any guard — the loop gets faster around
  the discipline, never through it.
- CI restructuring beyond adopting the same parallelism — CI is
  not the slow loop; the local iteration is.

## Acceptance Test

Full suite under `-n auto` green with wall time recorded here
(target: the measured trial's number, held by a soft ceiling in
the docs not a guard); `make test-touching` on a one-module diff
selects and passes its file set in under 30 s (measured);
the browser tier runs Chromium once per session (instance count
asserted in the harness); the close-task helper's output matches
the verify skill's checklist (skill text cites the helper).

## Outcome (round 47, 2026-08-27) — 🟢 Done

### The numbers, re-measured here

The audit measured its trial on its own container. Every figure below
is from **this** one, same tree, same session, so the ratios are
comparable to each other rather than to the trial:

```text
                          single process    -n auto      ratio
full suite                     642 s         194 s        3.3x
  passed / skipped        4,131 / 18     4,131 / 18
  skip census             identical between the two, reason for reason
```

The census caveat the item left open is discharged: the two runs'
`SKIPPED` lines were diffed and are byte-identical — 18 skips, four
reasons, same counts. Every server the suite starts already binds an
ephemeral port and every fixture already writes under `tmp_path`, which
is why the adoption cost really was zero.

### The re-tier was still needed, and the measurement said so

`-n auto` alone took the "fast" tier from 335 s (the item's figure) to
119 s here, and the small tier to 33 s. That was already near the
item's ~30 s target — so the honest thing was to check whether the
re-tier was still justified rather than assume it. It was:

```text
small tier, per-file, measured 2026-08-27:
  81.7 s of test time over 103 files
  14 files at or above the medium floor (1.0 s)
   1 file  above the large  floor (15.0 s):
       test_apparatus_in_its_place.py   17.4 s
       test_emphasis_is_a_budget.py     12.4 s
       …twelve more between 1.0 s and 5.6 s
```

Exactly round 39's mechanism, three rounds on: a file joins `small` by
default, each crossing is invisible alone, and only the aggregate can
see them. Moved by the `UX-238` rule — the measurement, not the taste:

```text
small tier before   81.7 s test time   33 s wall at -n auto   103 files
small tier after    35.5 s test time   11 s wall at -n auto    89 files
                                       25 s wall single-process
```

**11 s is the inner loop**, against the 21 s the guides had been
quoting and the 33 s parallelism alone would have left.

### The change-scoped loop

`make test-touching` maps the working diff to the test files that name
it. Measured:

```text
$ (edit bga/store_aggregate.py)
$ make test-touching
7 test file(s) name the 1 changed file(s); running them.
123 passed in 3.72s
WALL: 4 s
```

against the acceptance test's 30 s bound. The wider case is recorded
too, because a selector that only ever looks good on its best input is
not measured: editing `bga/viewer/app.js` selects 37 files and takes
**40 s** — the selector is only as narrow as the coupling, and the
viewer is coupled.

Two design notes worth having in writing:

* **grep, not the import graph.** Half this suite's guards read a
  document or a fixture and import nothing from it — `docs/guides/cli.md`
  has ten such guards — and an import graph would miss every one.
* **the one-word stem is not a token.** `store_aggregate` selects 7
  files; `findings` selected **57**, because it is also an English word
  this project uses constantly. A stem is only used when it carries a
  `_`, and a clause holds that.

It is a *selector, not a gate*: `make test` before the commit is
unchanged, and the verify skill says so in the same breath.

### The close ritual

`tools/dev_close_task.py` does the four mechanical edits — flip both
status markers, drop the row from the open table, append it to
`closed.md`, adjust the two index counts — and prints the Outcome
skeleton. What it deliberately does **not** do is fill anything in:
every measurement in the skeleton is a `<paste …>` placeholder, and
`--move` refuses without a written `--note` and refuses outright when
the task file has no Outcome section. A scaffold that pre-filled
measurements would be inviting the one failure this whole checklist
exists to prevent.

### CI runs the tier both ways

`make test` is parallel everywhere now, which creates one new blind
spot: an ordering assumption that xdist happens to hide. So CI gained a
second step running the small tier with `PYTEST_XDIST=` — 25 s
single-process after the re-tier, which is cheap insurance against a
test that only passes because two workers separated it.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| B1 | drop `$(PYTEST_XDIST)` from `test-small`'s recipe | the every-target-carries-the-flag clause, naming the target |
| B2 | remove `pytest-xdist` from the dev extras | the declared-dependency clause |
| B3 | let the one-word stem back into `tokens_for` | 1: the stem clause. **Not** the one-module clause — `store_aggregate` carries a `_` either way, so that mutation cannot reach it. The table said two before the run said one |
| B4 | make `--move` accept a task file with no Outcome | 1: the refuses-without-an-Outcome clause — and it **performed the move, on the real backlog**, which is the finding below |

**What B4 found, which is worth more than the mutation.** With the
refusal removed, the clause did not merely fail — it moved `UX-337`'s
row, flipped its marker and edited both index counts in the working
tree. A guard that mutates the repository when the code under test
misbehaves is a worse instrument than the thing it is testing. So
`dev_close_task.py` grew a `--scenarios DIR` override and the clause now
runs against a `tmp_path` copy, asserting the index is byte-identical
after the refusal. B4 was then re-run against the fixed pair: still red,
and `git status` clean afterwards.

### Deviation from the Required Fix

- **Lever 5 is not in this change.** Splitting `app.js` and `views.js`
  along their chapter seams is filed as
  [`UX-337`](UX-0337-the-two-viewer-modules-split-along-their-seams.md)
  with what this round established about it: the export's inliner
  concatenates modules in dependency order, so the split has to be
  **acyclic**, and the tidy "keep `views.js` as an index" shape does not
  work because `export * from` and bare `export { a, b };` are invisible
  to `_module_order` and survive `_inline_module` verbatim. `UX-199` is
  on file because this exact inlining once shipped an export that
  rendered empty. That is a dependency analysis, not a tail — and the
  four levers that make the loop fast do not wait on it.
- The item's target for the inner tier was "near 30 s under xdist". It
  landed at **11 s**, because the re-tier and the parallelism compound.
- The wall-clock numbers are recorded in the docs and **not** guarded.
  They are a property of the machine; a guard on them would go red on a
  slower laptop for no defect. What `tests/unit/test_the_loop_stays_fast.py`
  holds is that the mechanism is still wired up and the selector still
  selects.
