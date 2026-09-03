# UX-559: `bga view --serve` leaks a scratch directory per served run, forever

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-299 (which added the served trace) | **Found by:** `UX-546`'s track, measuring under load | **Serves:** anyone who leaves the viewer running | **Topic:** viewer

## Motivation

`tools/bga_view.py:1522`:

```python
if cls.trace_scratch is None:
    cls.trace_scratch = tempfile.mkdtemp(prefix="bga-serve-")
```

Nothing removes it. `grep -n trace_scratch tools/bga_view.py` gives
four hits — the guard, the `mkdtemp`, one `os.path.join`, and the
`None` initialiser. The one `shutil.rmtree` in the module
(`:631-632`) is a different `scratch`, in `finally` around a different
function.

So one directory per served run, per process, kept until something
else deletes `/tmp`. `UX-546`'s track counted **2,799 of them, 28 MB**,
on a box that had only ever run the test suite. On this working copy
after one session:

```text
$ ls -d /tmp/bga-serve-* | wc -l
40
```

The size is small and the count is not: 2,799 entries in `/tmp` is a
directory a `readdir` walks, and the same track hit `/tmp` at 14 GB
free with a live `bst build all.bst` returning **255** until
`rm -rf /tmp/pytest-of-root` freed 4.4 GB. The leak is not what filled
the disk, but it is the same shape and nothing bounds it.

It is a **product** defect, not a test one: `--serve` is what a user
runs to read the page, and a long-lived viewer process re-serving a
trace leaks per run.

## Required Fix

The scratch is class state on the handler, so its life is the server's
life: remove it when the server stops. `finally` around the serve loop
is the shape the module already uses at `:631`. `atexit` is the weaker
alternative — it does not fire on `SIGKILL`, but neither does anything
else, and today nothing fires at all.

Whichever, a guard must assert that serving twice and stopping leaves
no `bga-serve-*` behind. Count before and after; do not assert on the
name.

## Out of Scope

- `/tmp/pytest-of-root` and the suite's own leavings. Different owner
  (pytest), different lifetime, and `UX-300` already covers what a
  snapshot does to a store.
- Making the served trace not need a scratch at all. That is a design
  change to `UX-299`'s handoff; this row is that the directory it
  creates is never removed.

## Acceptance Test

```bash
before=$(ls -d /tmp/bga-serve-* 2>/dev/null | wc -l)
# serve a run twice, stop the server
after=$(ls -d /tmp/bga-serve-* 2>/dev/null | wc -l)
[ "$before" = "$after" ]
```
