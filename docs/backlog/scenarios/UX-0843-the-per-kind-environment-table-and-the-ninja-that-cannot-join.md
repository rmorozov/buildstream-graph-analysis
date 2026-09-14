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
