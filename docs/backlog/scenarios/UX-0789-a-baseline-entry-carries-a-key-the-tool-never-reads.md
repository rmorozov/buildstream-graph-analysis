# UX-789: a baseline entry carries a key the tool never reads

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-694 (the baseline), UX-712, UX-703 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the `--check` output that promises to name every forced batch forever | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tests/quality_baseline.json`'s entries for `tools/dev_sizes.py` and
`tools/dev_mutation.py` (both ruff S603) carry a top-level
`"forced_by": "UX-712"` / `"UX-703"`; `dev_baseline.py`'s
`load_forced` reads `"forced"` only:

```console
$ python3 tools/dev_baseline.py --check
clean: 295 finding(s) match ...; 1 still forced by UX-744; 2 still forced by UX-762; 1 still forced by UX-781
```

No "still forced by UX-712", no UX-703. `UX-712`'s Outcome says the
entry is S602 and was written with `--force --reason`; it is S603 and
was hand-written. The docstring's promise — every forced batch stays
named in `--check` — holds for entries the tool wrote and not for
these two.

## Required Fix

Re-force both entries through `tools/dev_baseline.py --write --force
--reason UX-NNN`, drop the dead key, and have `--check` refuse an
entry with an unknown top-level key so a third hand-written one
cannot land.

## Out of Scope

- The S603 findings themselves — a dev tool's `subprocess.run` with a
  list argument is the accepted shape.

## Acceptance Test

`tests/unit/test_the_baseline_only_shrinks.py` (or the file that
holds `--check`'s clauses) gains: an entry with `"forced_by"` → exit
2 naming the key. Mutation: accept any key — red.

## Outcome

_Not started._
