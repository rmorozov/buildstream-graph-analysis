# UX-1313: the dangling-help scan reads a scratch file another guard deletes mid-run

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** PR #315's `test (3.12)` on `195d2628` (2026-10-03) | **Serves:** R5 | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_help_is_short.py`

## Motivation

`test_no_help_string_in_source_ends_on_a_dangling_space` globs `tools/*.py`
and opens each path. `test_a_docs_only_diff_runs_its_guards.py:157` writes
`tools/_ux991_witness_scratch.py` and unlinks it; under xdist the glob can
list it and the open lose it:

```text
FAILURE tests.unit.test_help_is_short::test_no_help_string_in_source_ends_on_a_dangling_space
        FileNotFoundError: [Errno 2] No such file or directory: 'tools/_ux991_witness_scratch.py'
read from junit.xml: 12540 test(s) recorded, 1 failure(s)
```

## Required Fix

The scan reads tracked files only (`git ls-files`), so no scratch file
another guard writes is in its population.

## Out of Scope

Moving the UX-991 witness out of `tools/`: it must sit there for its
`sys.path[0]` claim.

## Acceptance Test

A dangling symlink in `tools/` (a file listed and gone) reddens the old
scan and not the new one; a real dangling `help=` in a tracked file still
reddens the new one. Read in this container.

## Outcome

## Outcome (round 168, 2026-10-03) — 🟢 Done

```text
$ ln -s /nonexistent tools/_zz_scratch.py
new scan: 1 passed     old scan: 1 failed   (FileNotFoundError)
$ append `help="dangling ",` to tools/bga_doctor.py (tracked)
new scan: 1 failed
$ python3 -m pytest -q tests/unit/test_help_is_short.py
106 passed
```

The scan's population is `git ls-files bga/cli.py ':(glob)tools/*.py'
':(glob)tools/native_trace/*.py'`, asserted non-trivial (> 50 files) so an
empty listing cannot pass it.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| M1 | the scan back on `glob.glob`, with a dangling symlink in `tools/` | 1 of 1 (`FileNotFoundError`) |
| M2 | a dangling `help="... ",` appended to tracked `tools/bga_doctor.py` | 1 of 1 |
