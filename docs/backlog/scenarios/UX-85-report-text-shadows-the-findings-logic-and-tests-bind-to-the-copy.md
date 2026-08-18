# UX-85: report/text.py shadows the findings logic, and the guard tests bind to the dead copy

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-75 (done)

## Motivation

UX-75's core claim is that what is worth saying is *decided once* in
`bga/findings.py`, with text rendering it and JSON publishing it. The
renderer still carries a full private duplicate of that judgement layer:
`bga/report/text.py:19-29` imports the canonical helpers, then
`:183`, `:189`, `:192`, `:216` **redefine** `_OPPORTUNITY_FLOOR_PCT`,
`_CHAIN_BOUND_RATIO`, `_heaviest_on_path` and
`_path_elements_by_duration` with duplicate bodies that shadow the
imports. Production traffic goes through `findings.py` — but
`tests/unit/test_correlate.py:339` and
`tests/unit/test_realizable_saving.py:100,120` import
`bga.report.text._heaviest_on_path`, so the tests guarding UX-71's
"analyze and correlate cannot name different elements first" invariant
exercise the **shadow copy**. The two implementations can drift apart
with the guard tests staying green — which is precisely the failure mode
UX-75 shipped to eliminate, and precisely how UX-76's regression
happened the first time.

## Required Fix

Delete the shadow definitions from `bga/report/text.py`; the module
already imports the canonical ones. Re-point the two test files at
`bga/findings.py`. Add a lint-level guard (a test asserting
`bga.report.text._heaviest_on_path is bga.findings._heaviest_on_path`,
or a ruff no-redefinition check scoped to the module) so a future
convenience copy cannot reappear silently.

## Out of Scope

- Any behavior change; text output must be byte-identical.

## Acceptance Test

`grep -n "_CHAIN_BOUND_RATIO\s*=" bga/report/text.py` returns only the
import alias; the full suite passes; golden text fixtures are
byte-identical before/after; the identity-guard test fails if a local
redefinition is reintroduced (verified by mutation: add one, watch it
fail, remove it).
