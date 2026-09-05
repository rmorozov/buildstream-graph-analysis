# UX-490: the guard against one-machine data cannot see an absolute path

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-276` built the scan; `UX-485` walked into the hole | **Found by:** round 73, writing `UX-485`'s end-to-end clauses | **Serves:** the round whose new guard rests on a capture in `/tmp` and passes here, green, for one session | **Topic:** guards | **Area:** tools

## Motivation

`tests/unit/test_a_guard_reads_only_what_a_clone_has.py` exists so a
test cannot rest on data only one machine has — `UX-213`'s defect in
the form its own fix did not cover. It finds path literals by prefix:

```python
ROOTS = ("bga/", "tools/", "tests/", "docs/", "examples/", "schemas/")
```

and its own comment says what that leaves out:

> Anything else in a string literal is a URL, **a temp path**, an
> element name or prose.

So an **absolute** path outside the clone is exempt by construction.
`UX-485`'s first draft rested four clauses entirely on

```python
TWO_QUEUE = pathlib.Path("/tmp/ux469/.bga/runs/20260901T161438Z")
```

and this guard said nothing. Nothing else did either: the suite was
green here and would have skipped on every other machine — and after
this container is reclaimed, on this one too. What caught it was a
*different* instrument, and only by accident: the skip census counted
one more unreadable reason, because the skip's message was an f-string.

A temp path is exempt for a real reason — a test that *builds* under
`tmp_path` names paths that must not be tracked, and `WRITTEN_NOT_READ`
already recognises those. The gap is the path a test **reads** that no
machine but one has.

## Required Fix

- The scan sees absolute paths outside the clone, not only
  repo-relative ones.
- The trigger stays `UX-276`'s: "exists here and is untracked". An
  absolute path that exists nowhere cannot produce the
  green-here-red-there failure and must not be reported — the fixture
  a test creates and then reads is the common case.
- The existing escapes stay: a committed fixture named beside it, a
  `skipif` keyed on the path's existence, or a `tmp_path`-derived
  path.
- A mutation that reintroduces `UX-485`'s first draft reddens it.

## Out of Scope

- The `/tmp` paths this repository writes on purpose:
  `/tmp/.bst-native-trace` is the bind **destination inside the
  sandbox** and cannot move (`tools/bst_native_build_tracer.py`), and
  the host side already lives under `<project>/.bga/tmp` (`UX-155`).
- The skip census (`tests/unit/test_every_skip_reason_is_declared.py`),
  which caught this one by luck rather than by design and is not the
  instrument for it — `UX-485` records how it happened.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_a_guard_reads_only_what_a_clone_has.py -q
```

green on the tree, and red on a tree where one test file's only data is
an absolute path outside the clone that exists on this machine — the
mutation pasted with the count it produced.

## Outcome

**Round 75, 2026-09-02.** Run as a parallel `implementer` track
(`UX-504`'s first real use); merged here.

**The gap, measured.** `UX-485`'s first draft, replayed against the
guard as `HEAD` had it: **11 passed, 3 skipped in 4.67s** — green, on a
file whose only data is `pathlib.Path("/tmp/ux469/.bga/runs/20260901T161438Z")`.
Against the guard as it now is:

```text
E   AssertionError: test(s) whose only data is a path git does not track.
E   It exists on this machine and will not exist in a clone:
E       tests/unit/test_ux485_first_draft_mutation.py ->
E       ['/tmp/ux469/.bga/runs/20260901T161438Z']
1 failed, 19 passed, 3 skipped in 7.59s
```

**The close.** `PATH_CALLS` + `_absolute_paths` read an absolute string
constant as a citation only in the argument position of
`Path`/`open`/`os.path.*`/`read_text`/… — position, the mirror of
`UX-462`'s `_compared_not_opened`, rather than "any absolute literal".
Measured on the tree: **144 distinct absolute literals in `tests/`, of
which the walk reads one** (`/proc`). The other 143 are values — argv
entries, synthesised trace fields, an expected `bwrap` command line.
`KERNEL_ROOTS = ("/proc", "/sys", "/dev")` is the one stated exemption:
the kernel supplies those on every Linux machine. `UX-276`'s trigger is
unchanged — `REPO / name` is `name` when `name` is absolute, so one
existence test serves both scans.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | `"Path"` dropped from `PATH_CALLS` | `..._the_draft_that_walked_into_the_hole_is_read` | 4 failed, 16 passed, 3 skipped |
| 2 | `_untracked_but_present` exempts every `/`-rooted name | `..._here_and_untracked_is_reported` | 2 failed, 18 passed, 3 skipped |
| 3 | `(REPO / name).exists()` → `True` | `..._exists_nowhere_is_not_reported` | 2 failed, 19 passed, 2 skipped |
| 4 | position ignored, every absolute constant read | `..._in_an_argv_is_a_value_not_a_read` | 3 failed, 18 passed, 2 skipped |
| 5 | `KERNEL_ROOTS = ()` | `..._is_not_one_machines_data` | 2 failed, 18 passed, 3 skipped |
| 6 | `WRITTEN_NOT_READ` filter dropped | `..._beside_the_fixture_is_not_a_citation` | 1 failed, 19 passed, 3 skipped |
| 7 | committed-fixture escape dropped | `..._is_still_the_escape` | 1 failed, 19 passed, 3 skipped |
| 8 | `_guards_absence` escape dropped | `..._a_skipif_on_its_existence_...` | 1 failed, 19 passed, 3 skipped |
| 9 | union narrowed to `_absolute_paths` alone | `..._the_relative_scan_still_reads_what_it_read` | 6 failed, 15 passed, 2 skipped |

1, 2, 4, 5 and 9 redden more than the guard they aim at — the new
clauses share `_absolute_paths`. Each is nonetheless the *named*
failure of a mutation aimed at its own claim.

**The weak guard, named.** `..._is_not_one_machines_data` rests on a
three-entry exemption list justified by a sentence rather than a
measurement. A test reading `/etc/hostname` or `$HOME/captures/…` is
reported; one reading `/sys/fs/cgroup/…` is not.

**Deviation from the Required Fix:** none. Input classes all covered:
relative-tracked · relative-untracked · absolute-untracked-that-exists ·
absolute-absent · `tmp_path`-derived · committed fixture · `skipif`.

**Tier.** The file moved **4.96s → 6.69s** single-process, 11 → 20
items. It already has rows in `tiers.py` (`# 3.5s`) and
`ci_reference.json` (9.87); the tier comment is now further out of
date, which `UX-496` is the row for.
