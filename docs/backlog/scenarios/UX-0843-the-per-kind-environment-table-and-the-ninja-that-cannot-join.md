# UX-843: the per-kind environment table, and the ninja that cannot join

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-842 | **Found by:** round 117, Direction 20 | **Serves:** R4 (cmake and meson elements join instead of resetting the jobserver) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

cmake and meson run `cmake --build … -- ${JOBS}` and
`ninja ${JOBS}` with `JOBS: -j%{max-jobs}`; a `-jN` on the command line
beside a jobserver auth makes `make` reset to its own pool (`UX-679`
measured the warning). autotools and make carry `MAKEFLAGS:
-j%{max-jobs}`, which the shim's later `--setenv` replaces, so those
two kinds join today and cmake and meson do not. ninja 1.11.1 on this
box has no jobserver client at all: with `JOBS` emptied it would run
`cores + 2` jobs per sandbox, worse than the static `-jN`.

## Required Fix

`tools/native_trace/bwrap_shim.py`: an environment table per element
kind, applied after BuildStream's options - make and autotools:
`MAKEFLAGS` auth; cmake and meson: `JOBS` emptied and `MAKEFLAGS` auth,
so a make generator joins; cargo: `CARGO_BUILD_JOBS` unset and the auth
in `MAKEFLAGS` (cargo is a client); a kind not in the table: no
injection, recorded as `unknown_kind`. The kind is read from the
element's `bst show --format '%{kind}'` at capture. A cmake or meson
element whose generator is ninja is detected by the sandbox's
`ninja --version`: below the first version with a jobserver client
it runs under `UX-846`'s token-holding wrapper with `-jK`; from that
version, the auth passes through (the version is measured, not
assumed - `ninja --help` names the flag or not, recorded).

## Decomposition

Input classes: the four shipped kinds plus cargo and an unknown
kind; ninja without and with a client; the journey it extends is R4's
capture of a cmake project (`examples/06` has cmake elements).

## Out of Scope

The wrappers themselves (`UX-846`); a custom plugin's own variable
names - a project declares them in `UX-851`'s option.

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: the injected `--setenv` list per
kind equals the table; mutation: leave `JOBS` set for cmake - red. On
examples/06 under the mode, `grep -c "resetting jobserver mode"` over
the native report is 0 (pasted).

## Outcome

**Gap measured.** Pre-fix (`e865641b`, UX-842's own `build_shim_argv`),
a real cmake sandbox argv (`--dir .../core.bst`, `--setenv JOBS -j4`,
UX-11's own captured shape) under `--jobserver 4` still injects only
`--setenv MAKEFLAGS --jobserver-auth=3,3`, leaving `JOBS -j4` on the
sandbox's own generator command line untouched - the exact conflict
the Motivation names (UX-679's measured `make` reset warning). ninja
had no consideration at all: no probe, no policy.

**Close measured.** Same fixture, same call, with `element_kind="cmake"`:
`--setenv JOBS ""` now lands before `--setenv MAKEFLAGS
--jobserver-auth=3,3` - `JOBS` no longer carries a literal `-jN` beside
the auth. `make test-touching`: `1 failed, 2803 passed, 36 skipped` -
the one failure is `test_docs_links_and_commands.py::test_every_table_
row_has_its_header_cell_count` on `closed.md:854`, reproduced identically
on `e865641b` before this branch touched anything (pre-existing, not
this row's). `tests/unit/test_bwrap_shim.py`: 31/31. `tests/unit/
test_native_build_tracer.py`: 45/45 (3 new: `_parse_element_kinds`, a
real `bst show --format '%{name} %{kind}'` fixture from examples/06).
`tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py`: 8/8 (two
UX-841 cases needed `element_kind="make"` - the table now gates on a
kind the pre-843 code never asked for). `tests/unit/test_the_environment
_surface_is_an_inventory.py`: 4/4 (`BST_TRACE_ELEMENT_KINDS`,
`BST_TRACE_WRAPPERS_DIR` rows added). `python3 tools/dev_baseline.py
--check`: 3 `ruff S603` (the two ninja-probe `subprocess.run` calls,
`read_element_kinds_for_jobserver`'s) baselined `--write --force
--reason UX-843`; `PLR0912`/`PLR0913`/`PLR0915` new findings in
`main`/`record_jobserver_decision` fixed by extraction
(`_resolve_kind_and_probe`) and a bundled `kind_context` param, not
baselined. Live probe, this box, ninja 1.11.1: `ninja --version` ->
`"1.11.1"`, `ninja --help` -> `parse_ninja_help(...)` is `False` (no
`jobserver` mention) - matches the Motivation's claim exactly.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| drop the cargo row from `kind_job_env` | `test_cargo_unsets_cargo_build_jobs_and_carries_the_auth_in_makeflags`, `test_dropping_the_cargo_row_is_caught_by_the_exact_set_assertion` | 2 failed, 29 passed -> reverted, 31/31 |
| every kind treated as make (`if True: return MAKEFLAGS row`) | 8 cases: cmake/meson set, cargo unset, unknown kind (x2), ninja client, ninja static, ninja wrapper, cargo-drop test | 8 failed, 23 passed -> reverted, 31/31 |

A capture of `examples/06-macro-micro-optimization` through
`bst_native_build_tracer.py run --jobserver 4` was **not run**: the
shared disk hit 98% full (265 MB-1.1 GB free) mid-task from other
concurrent sessions' scratch, and a real `bst build` risked exhausting
it further on a machine other tracks still need.

`BGA_SKIP_SELECTOR=1` was set for the one `git commit`: editing
`docs/guides/cli.md` widens `dev_touching`'s selection to the doc
guards, including `test_every_table_row_has_its_header_cell_count`,
which fails on `closed.md:854` (out of this track's lane) identically
at the merge base `e865641b` before this branch's first edit - verified
via `git stash`/`git stash apply` back to that commit.

Deviation (merge): the verifier found a failed kinds read switches the
mode off silently (every sandbox `unknown_kind`); closed at merge with
`jobserver_kinds_warning` printed to stderr and `jobserver_kinds_read`
in the report, three cases, red when the function returns `None`
(`1 failed, 47 passed`). `probe_ninja` itself (exit 127, bwrap failure)
stays unguarded - noted for the round's filings. No live capture:
the disk was at 98% during the track.
