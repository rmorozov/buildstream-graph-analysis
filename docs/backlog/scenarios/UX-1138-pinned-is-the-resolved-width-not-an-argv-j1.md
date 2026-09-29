# UX-1138: every autotools element reads "pinned to -j1", because its install step says so

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-894 | **Found by:** Ruslan's own `bga view` (2026-09-29): the capacity finding listed every element he built | **Serves:** R2, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_pinned_is_the_resolved_width.py`

## Motivation

`pinned_to_one_job` is decided in the capture from `-j(\d+)` over the
argv of `make`/`ninja`, highest wins. BuildStream's autotools default
install step is `make -j1 DESTDIR=... install`, while the build step's
width travels in `MAKEFLAGS` and never reaches argv - so every
autotools element reads pinned once any element asks for more. The
fdsdk capture (`captures/fdsdk-latest`, `native-report.json`):

```text
element                 requested  peak  resolved width
components/openssl.bst  1          8     4
components/python3.bst  1          12    4
components/bison.bst    1          8     4
components/libxml2.bst  1          8     4
components/gperf.bst    1          8     4
pinned: 5 of 9 elements with a request
```

The capacity finding's `elements` is that pinned list, so a project of
autotools elements got its whole build list.

## Decomposition

Input classes: an argv `-j1` at a resolved width above one (false pin), a resolved width of one (`notparallel`, `macro_micro`'s `core.bst`), no graph. The journey extends reading the capacity recommendation.

## Required Fix

Where `graph.json` resolves a width, pinned is that width being one
while another element's is above one; the argv reading stands only
where no width is resolved. `analyze` rescored after the capacity
summary had read the pins, so the rescoring moves ahead of it, and
`correlate` rescoring too.

## Out of Scope

Reading `MAKEFLAGS` in the capture; the wording of the pinned sentence.

## Acceptance Test

`tests/unit/test_pinned_is_the_resolved_width.py`: a false argv pin on
`macro_micro`'s `codegen.bst` (width 4) is dropped, `core.bst`
(notparallel) stays pinned, and `bga analyze --plane2` names only
`core.bst` in the capacity finding. The fdsdk report, rescored, reads 0
pinned.

## Outcome

## Outcome (round 153, 2026-09-29) — 🟢 Done

**Premise:** held — all five fdsdk pins sit at a resolved width of 4.

### After

```text
$ python3 -c "... apply_resolved_widths(native-report.json, resolved_widths(run/graph.json))"   # fdsdk
0 pinned (was 5)
$ bga analyze tests/fixtures/macro_micro/run --format json   # capacity-recommendation elements
['core.bst']
$ python3 tools/dev_refresh_analysis.py
0 of 2 committed analysis document(s) disagree with the analyzer
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_pinned_is_the_resolved_width.py -q
3 passed
```

`apply_resolved_widths` (`bga/plane2.py`) now owns `pinned_to_one_job`
wherever a width is resolved; `analyze` applies it before
`summarize_plane2_capacity` and `correlate` applies it on load.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | keep the argv pin (filter only the overlap finding) | the width-4 drop and the analyze clause, 2 failed |
| A2 | never add a pin from a width of one | all three, 3 failed |
| A3 | rescore after the capacity summary, as before | the analyze clause, 1 failed |

Deviation: the capture's own argv rule is unchanged; a report with no
`graph.json` beside it still reads the argv pin. The jobserver shim's
`decision == "pinned"` (`cli.py`'s max-jobs advice) is its own signal
and is not rescored. The size ledger moves `bga/cli.py` 3487 -> 3491
lines and `bga/plane2.py` 504 -> 510 lines, longest function 35 -> 39.
