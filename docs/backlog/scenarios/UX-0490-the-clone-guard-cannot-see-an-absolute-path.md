# UX-490: the guard against one-machine data cannot see an absolute path

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-276` built the scan; `UX-485` walked into the hole | **Found by:** round 73, writing `UX-485`'s end-to-end clauses | **Serves:** the round whose new guard rests on a capture in `/tmp` and passes here, green, for one session | **Topic:** guards

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

_Not started._
