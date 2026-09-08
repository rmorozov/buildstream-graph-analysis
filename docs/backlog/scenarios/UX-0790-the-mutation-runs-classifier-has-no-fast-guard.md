# UX-790: the mutation run's classifier has no fast guard

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-703 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the weekly run whose survivor count is the only number anyone reads | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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

**The gap, measured.** `grep -rn "guards_for\|run_module\|_mutmut_config\|_CAUGHT"
tests/` before this change: nothing. `run_module`'s classification lived
inline in the subprocess call, untestable without a real `mutmut` run.

**The close, measured.** `classify(results_text) -> dict` in
`tools/dev_mutation.py`, fed by `mutmut results --all true`'s text;
`_CAUGHT` applied inside it to split raw verdict counts into `"caught"`
and `"survivors"` totals. `run_module` calls it (`counts` now in its
returned dict), keeping the per-mutant `_verdict_lines` helper (shared
with `classify`) for the ledger row's function-level grouping. Real
capture: `python3 tools/dev_mutation.py --module
tools/dev_page_census.py --max-children 4` (mutmut 3.7.0, already
installed) — 50 mutants, 4 killed, 46 survivors, matching `UX-703`'s
Outcome exactly; the raw `mutmut results --all true` text is
`CENSUS_RESULTS` in
`tests/unit/test_the_weekly_mutation_run_names_its_survivors.py`.
`classify(CENSUS_RESULTS) == {"survived": 9, "killed": 4, "no tests":
37, "caught": 4, "survivors": 46}`.

Retro-verify found `CENSUS_RESULTS` names only three of the verdicts
`mutmut/__main__.py`'s `status_by_exit_code` (mutmut 3.7) can print.
`ALL_VERDICTS` (synthetic, one line per verdict — `killed`, `survived`,
`no tests`, `timeout`, `suspicious`, `skipped`, `segfault`, `not
checked`, `check was interrupted by user`, `caught by type check` —
plus a colon-less line) closes it:
`test_classify_names_every_verdict_mutmut_3_7_can_print` asserts each
verdict counts under its own name, the colon-less line drops without
crashing, and `"caught"`/`"survivors"` split 1/9.

**Mutations**
(`tests/unit/test_the_weekly_mutation_run_names_its_survivors.py`):

| mutation | reddened | count |
|---|---|---|
| `_CAUGHT \|= {"timeout"}` | `test_classify_applies_caught_to_the_verdict_it_names` | 1 failed, 5 passed |
| `classify` counts every line as `"survived"` | `test_classify_matches_ux_703s_captured_census_run`, `test_classify_applies_caught_to_the_verdict_it_names` | 2 failed, 4 passed |
| `_CAUGHT \|= {"suspicious"}` | `test_classify_names_every_verdict_mutmut_3_7_can_print` | 1 failed, 6 passed |

All three reverted from the pre-mutation copy; full file green after
each (`6 passed` / `7 passed` post-`ALL_VERDICTS`).

**Deviation.** An `implementer` on `sonnet` captured a real `mutmut` run as the fixture (4 killed / 46 survivors, `UX-703`'s numbers); its verifier found the capture carried three of the ten verdicts mutmut 3.7 prints, so a synthetic all-verdicts fixture and its clause landed before the merge. `render_row`'s output was byte-identical across the refactor, measured by the verifier.
