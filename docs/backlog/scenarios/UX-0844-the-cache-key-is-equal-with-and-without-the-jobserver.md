# UX-844: the cache key is equal with and without the jobserver

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843 | **Found by:** round 117, Direction 20 | **Serves:** R4 (artifacts built either way are shared) | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

BuildStream folds the composed environment minus `environment-nocache`
into the key (`element.py:2319-2339`, 2.8.0); the shim's injection is
spliced into `bwrap`'s argv after composition and never passes through
it; the shipped plugins nocache `JOBS` and `MAKEFLAGS` besides. So the
key is safe by construction - and no measurement in the tree says so:
`UX-679` compared `%{env}`, never `%{full-key}`, and a custom plugin
that keys its `JOBS` would split the cache silently between the two
modes.

## Required Fix

A guard in CI's examples job (`.github/workflows`, the `bst-examples`
job): `bst show --format '%{name} %{full-key}'` over examples/06 with
the mode off and on, diffed - equal; then a build under the mode
followed by `bst build` without it reports every element cached (the
pasted `bst build` summary). The tracer's report records the key set's
hash so a later capture can be compared. `docs/guides/cli.md` states
the rule in one sentence beside `--jobserver`.

## Out of Scope

A key-safe custom plugin - the project's own `environment-nocache`
is the fix, named in the guide.

## Acceptance Test

`tests/unit/test_the_key_is_equal_either_way.py` runs the two `bst
show` commands on the fixture project (skips without `bst`); mutation:
a fixture plugin that keys `JOBS` - red, naming the element.
