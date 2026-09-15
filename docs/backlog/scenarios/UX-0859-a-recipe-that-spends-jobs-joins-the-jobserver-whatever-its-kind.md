# UX-859: a recipe that spends `JOBS` joins the jobserver, whatever its kind

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843, UX-846 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R2 (a manual element calling `cmake --build ${JOBS}` by hand builds under the mode like a cmake one) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`kind_job_env` (`tools/native_trace/bwrap_shim.py`) knows make,
autotools, cmake, meson and cargo; every other kind falls through as
`unknown_kind` with no `MAKEFLAGS` and `JOBS` left as BuildStream composed
it. The user's project carries many manual-kind recipes that call
`cmake --build <dir> ${JOBS}` by hand; each runs at its own `-j8`
outside the pool, whatever the mode. The env already tells the shim
what the recipe will do: a `JOBS` variable set by BuildStream is the
recipe's promise to spend it.

## Required Fix

`tools/native_trace/bwrap_shim.py`: a kind outside the table whose
sandbox env carries `JOBS` (the shim already parses `--setenv JOBS`)
gets the cmake treatment - `JOBS` emptied, `MAKEFLAGS` injected, policy
`jobs_env` - and the ninja probe decides client, wrapper or make as it
does for cmake; a kind with no `JOBS` stays `unknown_kind`.
`jobserver_kinds_warning` names the policy; `docs/guides/cli.md`'s
jobserver paragraph says which recipes join and why.

## Decomposition

Input classes: a kind in the table, a kind outside it with `JOBS`,
one without; ninja client, ninja wrapper, no ninja; the journey it
extends is `UX-843`'s per-kind join on the user's manual recipes.

## Out of Scope

A recipe that hard-codes `-j8` in its own commands rather than
spending `JOBS`; rewriting argv.

## Acceptance Test

`tests/unit/test_bwrap_shim.py` gains: a manual kind with `JOBS=-j8`
in its env reads policy `jobs_env` with `MAKEFLAGS` set and `JOBS`
emptied; a manual kind without `JOBS` stays `unknown_kind`; mutation:
drop the `JOBS` presence check - red.
