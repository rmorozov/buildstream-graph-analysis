# UX-588: the Python floor is in the CI matrix and in no guard

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-579 (whose new file tripped it) | **Found by:** round 83's own CI, blocking PR #200 | **Serves:** every track that writes Python on a newer interpreter than the floor | **Topic:** guards

## Motivation

`pyproject.toml:11` declares `requires-python = ">=3.9"`. Nothing local
reads it. A track working on 3.11 wrote one annotation:

```python
def _refusal(tokens: list[str]) -> str | None:
```

`list[str]` is PEP 585 and lands in 3.9; `str | None` is PEP 604 and
lands in **3.10**. The track ran `make test-touching`, `make lint` and
`make check-clean`, all green, and so did this session's full
`make test` — every one of them on 3.11. CI said:

```text
tests/unit/test_the_documented_bga_lines_parse.py:93: in <module>
    def _refusal(tokens: list[str]) -> str | None:
E   TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
========== 3639 passed, 43 skipped, 4 errors in 33.44s ==========
make: *** [Makefile:64: test-small] Error 1
```

Only `test (3.9)` failed; 3.10, 3.11 and 3.12 all passed the same
commit. The floor is real and it is enforced once a push has travelled
to a runner — seven minutes, and a red PR — rather than in the four
seconds a contributor already spends.

Two further costs are worth recording because they nearly sent this
round the wrong way. The failure is a **collection error**, so no
junit was written; the `UX-554` naming step then read a *stale* junit
from an earlier step and named two `test_the_rail_takes_a_step.py`
tests that had nothing to do with it. Reading those names, this
session spent several measurements chasing a viewer regression that
does not exist. A namer that reads a file the run did not write names
the previous run's failures.

## Required Fix

A guard that reads the floor from `pyproject.toml` and holds the tree
to it. PEP 604 in an annotation is a *runtime* `TypeError` on 3.9, not
a `SyntaxError`, so `ast.parse(..., feature_version=(3, 9))` does not
see it: the annotations have to be walked. A module carrying
`from __future__ import annotations` is exempt, because there its
annotations are strings and never evaluated.

Separately: `dev_junit_tail.py` should say when the junit it read is
older than the run, rather than naming its contents as this run's
failures.

## Out of Scope

Raising the floor to 3.10. That is a support decision with users
attached, not a fix for a guard that is missing; if it is ever taken,
this guard's PEP 604 clause skips itself and the floor clause records
the new number.

`dev_junit_tail.py`'s staleness — filed separately rather than fixed
here, so this row stays one claim.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_the_python_floor_is_a_guard.py -q
```

green, and red when the retired annotation is put back.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held.

**The gap, measured.** Run 33751159258, head `2b68006`: `test (3.9)`
failed in 33s with the four collection errors above, while `test
(3.10)`, `test (3.11)` and `test (3.12)` all succeeded on the same
commit. This session's own `make test` on 3.11 read
`6403 passed, 29 skipped, 1 warning in 248.63s` — green, on the tree
that CI refused.

**The close.** `tests/unit/test_the_python_floor_is_a_guard.py`: the
floor comes from `pyproject.toml`, the scan from `git ls-files`, and
the check walks every annotation of every tracked module under `bga/`,
`tools/` and `tests/` for a `BinOp` whose op is `BitOr`.

```text
$ python3 -m pytest tests/unit/test_the_python_floor_is_a_guard.py -q
3 passed in 1.88s
```

The one offending annotation is now `Optional[str]`, and no other
exists in shipped code — the scan over 3 directories finds zero.

**Mutations.**

| # | mutation | result |
|---|---|---|
| M1 | the retired `-> str \| None` put back on `_refusal` | red |
| M2 | `requires-python` read as `>=3.10` | red on the floor clause; the PEP 604 clause **skips**, which is the point |
| M3 | `SCANNED` pointed at a directory that does not exist | red on the vacuity floor |

M1 is the defect that cost the CI cycle. M2 shows the skip is the
declared floor's decision and not a constant in the guard. M3 is there
because a scan that reads nothing passes everything — the shape
`UX-576` was bitten by twice in this same round.

**A reading I got wrong first.** The `UX-554` naming step named two
`test_the_rail_takes_a_step.py` tests. There is no junit for a
collection error, so it had read a stale one. I took those names as
the finding and spent four measurements — an interleaved A/B on the
docs guard, a section census of the exported page, a `compute_next_steps`
call on the fixture, a full local suite — looking for a viewer
regression that was never there. The failing check's own log, read at
70 lines instead of 12, said it in one line. Filed for the namer:
it should say when the file it read is older than the run.

**Deviation from the Required Fix.** The `dev_junit_tail.py` staleness
half is filed, not fixed here — one row, one claim.

**Suite.** With the batch, at the round's gate.
