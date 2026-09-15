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

## Outcome

**Gap measured.** Pre-fix (`HEAD` at this track's start), `kind_job_env
("manual", "--jobserver-auth=3,3")` (no `jobs_present` param existed):
`([], [], 'unknown_kind')` - no injection, whatever the sandbox's own
`JOBS` said.

**Close measured.** Same call, post-fix: `jobs_present=True` ->
`([('JOBS', ''), ('MAKEFLAGS', '--jobserver-auth=3,3')], [], 'jobs_env')`;
`jobs_present=False` -> `([], [], 'unknown_kind')` unchanged. `kind_job_env`
gained the `jobs_present` kwarg (default `None`, every prior caller
stands) and a shared `_ninja_aware_env` helper, reused by the cmake/meson
branch (`cmake_meson` base policy) and the new table-less branch
(`jobs_env` base policy). Both `kind_job_env` call sites (`_jobserver_
injection`, `record_jobserver_decision`) pass `jobs_present=_setenv_value
(opts, "JOBS") is not None`, read from the same argv scan already in the
file. `jobserver_kinds_warning`'s message and `compute_jobserver_per_
element`'s docstring now name `jobs_env`; `bga/schemas.py` carries no
per-kind policy enum (checked), so it was not touched. `docs/guides/
cli.md`'s `--jobserver` paragraph gained one sentence.

`python3 -m pytest tests/unit/test_bwrap_shim.py -q`: `51 passed in
0.73s` (31 UX-843 baseline + 4 table/unknown-kind + 1 cmake-unaffected +
5 widened-gate: real probe through a fake bwrap on `_resolve_kind_and_
probe`'s own subprocess path, driving `ninja_client`/`ninja_wrapper`/
`ninja_static`/`jobs_env`-with-no-ninja/no-probe-without-`JOBS`).
`make test-touching`'s 144-file selection (`-n auto`, shared machine):
`3166 passed, 42 skipped in 651.97s`.

**Mutation table.**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `kind_job_env`'s `if jobs_present:` branch | `if jobs_present:` -> `if False:` | `test_a_table_less_kind_that_spends_jobs_gets_the_jobs_env_policy` | 1 failed, 45 passed -> reverted, 46/46 |
| `_jobserver_injection`'s wiring (argv-driven, not `kind_job_env` alone) | `jobs_present=_setenv_value(...)` -> `jobs_present=False` | same test, same reason | 1 failed, 45 passed -> reverted, 46/46 |
| `_resolve_kind_and_probe`'s widened gate | gate reverted to kind-set-only (`if element_kind not in _NINJA_CAPABLE_KINDS or not active`) | the 4 `JOBS`-carrying widened-gate tests (`ninja_client`/`ninja_wrapper`/`ninja_static`/no-ninja); the 5th (no-`JOBS`) stayed green, correctly | 4 failed, 47 passed -> reverted, 51/51 |

Deviation (verifier): the ninja-probe gate, first left kind-set-only
(a `jobs_present` kind's `ninja_probe` always `None`), is now widened -
`_resolve_kind_and_probe` runs the probe when the kind is cmake/meson
*or* the sandbox env carries `JOBS`, one extra `ninja --help` per
capture (UX-855's cache). A manual `-G Ninja` recipe now runs: at the
pool's auth (joined) when ninja names a jobserver client; token-held
through UX-846's wrapper when it does not and a wrapper dir exists;
unchanged at BuildStream's own static `-jN` (no injection, avoiding the
cores+2 regression UX-843 found) when neither; joined via MAKEFLAGS,
`JOBS` emptied, when the probe finds no ninja in the sandbox at all
(the "make treatment", same as before this correction).
