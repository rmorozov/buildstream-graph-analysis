# UX-805: the doctor's chain probe drops the user's cache config with its HOME

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-755 (the absolute-valued reserve, for the tests), UX-149 (the chain probe) | **Found by:** round 111, the gate on a box 13.5 GB from full | **Serves:** R8 reading `bga doctor` on a host whose free space is under 5 % of the volume | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

```console
$ make test        # avail 13.54 GB of a 270.55 GB volume (statvfs f_bavail)
FAILED tests/unit/test_doctor.py::TestTheWholeChainProbe::test_the_chain_reports_every_link_in_order
E   AssertionError: ['chain-shim-exec', 'chain-build']
    [main:base.bst] FAILURE Staging local files into CAS
    Cache too full
$ XDG_CONFIG_HOME=tests/fixtures/macro_micro/xdg_config_home \
    PYTEST_XDIST= python3 -m pytest tests/unit/test_doctor.py -q -k TheWholeChainProbe
6 passed in 4.23s
```

`check_capture_chain` (`tools/bga_doctor.py:727`) runs the probe under
a throwaway `HOME` so the cache is cold; `_isolated_home` sets `HOME`
and `PYTHONPATH` and nothing else, so `bst` reads no
`~/.config/buildstream.conf` and falls back to `reserved-disk-space:
5%` of the volume's *total* (`userconfig.yaml:42`) — 13.53 GB here,
against 13.54 GB free, and the reserve alone refuses the first blob.
`UX-755`'s mechanism, reached in production code: the user's own
captures run under a config with absolute values (`quota: 3G`,
`reserved-disk-space: 500M`) and work; the probe that is meant to
prove their chain ignores that config and reports the chain broken.
The gate at `41a0d3c2` was green with 0.2 GB more free.

## Required Fix

`_isolated_home` in `tools/bga_doctor.py` carries the user's
BuildStream config into the throwaway `HOME`: when `XDG_CONFIG_HOME` is
set it is left alone (`bst` reads it whatever `HOME` is); otherwise
`~/.config/buildstream.conf` and `buildstream2.conf`, whichever exist,
are copied into `<home>/.config/`. When no config exists at all and
`chain-build` fails with `Cache too full`, the finding's hint names the
reserve arithmetic and the absolute value that sidesteps it, the way
`tests/fixtures/macro_micro/xdg_config_home/buildstream.conf` explains
it. A unit test in `tests/unit/test_doctor.py` builds a fake `HOME`
with both files and asserts the copy; a second asserts `XDG_CONFIG_HOME`
is kept untouched.

## Decomposition

Input classes: a host with `XDG_CONFIG_HOME` set (left alone), a host
with `~/.config/buildstream.conf` and no `XDG_CONFIG_HOME` (copied), a
host with neither and a reserve the volume cannot meet (the hint). The
journey is `bga doctor`'s whole-chain probe, `chain-build` its step.

## Out of Scope

- Sizing the reserve for the user — declined: the config is theirs, the probe only carries it.
- The tests' own isolation (`_bst_env.py`) — `UX-760` did it; this is the production copy of the same rule.

## Acceptance Test

`tests/unit/test_doctor.py -k TheWholeChainProbe` green on this box with
`XDG_CONFIG_HOME` unset (the ambient config carried); mutation: the copy
removed — the two config tests red, and the chain test red on this box
with `Cache too full` in its stderr.
