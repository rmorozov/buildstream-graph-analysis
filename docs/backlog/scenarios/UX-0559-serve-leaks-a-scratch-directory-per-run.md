# UX-559: `bga view --serve` leaks a scratch directory per served run, forever

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-299 (which added the served trace) | **Found by:** `UX-546`'s track, measuring under load | **Serves:** anyone who leaves the viewer running | **Topic:** viewer | **Area:** tools

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

## Outcome (round 81, 2026-09-03) — 🟢 Done

**Premise:** held — one scratch directory per served run, `before=102 after=104 leaked=2`.

### The gap, measured

Two servers, each asked for its timeline, each closed — counting
`bga-serve-*` in `tempfile.gettempdir()` around them:

```text
  served 785 bytes; scratch dirs now: 103
  served 785 bytes; scratch dirs now: 104
before=102 after=104  leaked=2
```

One directory per served run, exactly as filed. `before=102` is this
working copy's own backlog of them, from the suite alone.

### After

The same script, unchanged:

```text
  served 785 bytes; scratch dirs now: 105
  served 785 bytes; scratch dirs now: 105
before=104 after=104  leaked=0
```

The count rises while a server holds its scratch and returns to
baseline when it closes. The Acceptance Test as written:

```text
before=104 after=104
PASS: serving twice and stopping left nothing behind
```

`server_close()` is where the removal went, not a `finally` in `main`.
`serve()`'s docstring already says "the caller closes it", so the one
call every route out already makes — the serve loop's `finally`, the
`--perfetto` refusal at `:1875` that never enters the loop, and every
test holding a server — is the one that cleans up. A `finally` around
the serve loop alone would have left the other two leaking.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| B1 | `_Server` → plain `ThreadingHTTPServer`, i.e. the filed defect | both count clauses, "left 2 scratch director(y/ies) behind", 2 red / 1 green |
| B2 | `rmtree` deleted, the class-state reset kept | the same two — the bookkeeping alone does not remove a directory, 2 red / 1 green |
| B3 | `trace_run` forced to `None`, so nothing renders | both, on `HTTP Error 404` — a server that serves no trace cannot pass the guard vacuously, 2 red / 1 green |

No guard of this item failed to discriminate. B3 is the one that
matters: `test_the_scratch_exists_while_the_server_does` reads the
count *during* the serve, so "none afterwards" cannot be satisfied by
never making one.

### Deviation from the Required Fix

None. `atexit` was declined — it is the weaker of the two the task file
offered, and `server_close` fires on the `--perfetto` route that exits
before the serve loop, which `atexit` would only reach at interpreter
shutdown.

The guard points `tempfile.tempdir` at its own directory so the reading
is the test's and not the machine's; under `-n auto` another worker
serving a run would otherwise land in the same count.

```text
$ make test-touching
97 file(s) selected · 1765 passed, 44 skipped in 129.53s (0:02:09)
$ make lint
All checks passed!
```
