# UX-790: the mutation run's classifier has no fast guard

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-703 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the weekly run whose survivor count is the only number anyone reads | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/dev_mutation.py`'s `_CAUGHT = {"killed"}` decides what counts
as caught; the comment above it says `"timeout"` is excluded on
purpose. `run_module`, `guards_for`, `_mutmut_config` and `_CAUGHT`
have no test:

```console
$ grep -rn "guards_for\|run_module\|_mutmut_config\|_CAUGHT" tests/
(nothing)
$ sed -i 's/_CAUGHT = {"killed"}/_CAUGHT = {"killed", "timeout"}/' tools/dev_mutation.py
$ python -m pytest tests/ -k mutation -q
269 passed
```

The four guards `UX-703` added cover the ledger row and the module
filter; the classification that makes the row's number is the part
with none. A real `mutmut` run is the weekly cost the task declined
to pay in the loop, rightly — but the classifier does not need one.

## Required Fix

Split the classification out of the subprocess in
`tools/dev_mutation.py`: `classify(results_text) -> counts by
verdict`, fed by a pasted `mutmut results --all true` sample, with
`_CAUGHT` applied there. Guard it on the sample.

## Out of Scope

- Running mutmut in the guard — the sample is the fixture.

## Acceptance Test

`tests/unit/test_the_weekly_mutation_run_names_its_survivors.py` reds under
the mutation `_CAUGHT |= {"timeout"}` — the survivor count on the sample
drops.

## Outcome

_Not started._
