# UX-1387: the examples stage on Ubuntu 24.04 and 26.04 both

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1386 | **Found by:** Ruslan in the project thread, 2026-11-17 10:19 UTC ("let's return back ubuntu 24.04 support as well, I propose supporting both") | **Serves:** R8 | **Topic:** guards | **Area:** tools | **Shape:** bounded | **Reading:** runner:bst-tests

**Guard:** `tests/unit/test_the_toolchain_axis_is_pinned.py`, `tests/unit/test_the_sysroot_declares_both_axes.py`

## Motivation

UX-1386 moved the declared host rows to 26.04, so a 24.04 host that
stages the sysroot warns and reds the staged half of the suite, and no
CI job runs on 24.04 any more.

## Required Fix

`sysroot_manifest.HOST_RELEASES` declares glibc and coreutils per
Ubuntu release, chosen by the staging host's `/etc/os-release`, the
newest declared when the host is not one of them; `bst-tests` runs on
`ubuntu-24.04` and `ubuntu-26.04`.

## Out of Scope

A 24.04 cell for the `test` matrix: `bst-tests` already runs the whole
`make test` on each image.

## Acceptance Test

Both `bst-tests` cells green, each staging step with no
`sysroot_manifest:` divergence line; each release's runtime rows are
written out in a guard, and the release pick reddens when it ignores
the host.

## Outcome (round 176, 2026-11-17) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ python3 -c "from tools import sysroot_manifest as m; print([(r['name'], r['version']) for r in m.components() if r['origin'] == 'host'])"
[('glibc', '2.43'), ('coreutils', '0.10.0'), ('dash', None)]      # at 0c26d035, on this 24.04 container
```

Every host row read 26.04's, so a 24.04 staging would warn on 5 probes.

### After

```text
$ python3 -c "from tools import sysroot_manifest as m; print(m.host_release(), [(r['name'], r['version']) for r in m.components() if r['origin'] == 'host'])"
24.04 [('glibc', '2.39'), ('coreutils', '9.4'), ('dash', None)]
$ python3 -m pytest -q tests/unit/test_the_toolchain_axis_is_pinned.py tests/unit/test_the_sysroot_declares_both_axes.py
28 passed, 17 skipped
```

`bst-tests` is a two-cell matrix, `ubuntu-24.04` and `ubuntu-26.04`; the
pull request's run is the reading on each.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| B1 | `HOST_RELEASES["24.04"]` given 26.04's versions | `test_each_releases_runtime_rows_are_written_out[24.04]`, 1 |
| B2 | `host_release` returns the newest release whatever the host | `test_the_host_rows_follow_the_staging_hosts_release`, 3 |

### Deviation from the Required Fix

None. `dev_sizes --adopt --force` moved `sysroot_manifest.py`'s
`file_lines` 313 -> 336 (`HOST_RELEASES` and `host_release`).
