# UX-773: a killed worker leaks a browser and its profile

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the session whose next `make test` reds on disk, on a tree nobody touched | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`tests/browser.py` keeps one Chrome per worker per session in
`_SHARED` and removes it in an `atexit` handler (`:49`). `atexit` is
the **only** mechanism: a worker that dies by signal leaves the
process reparented to pid 1 and the profile directory on disk.

```console
$ ls -d /tmp/bga-geometry-* | wc -l
71
$ PYTHONPATH=. python3 -c "
import tests.browser as b, os, signal
with b.Browser(b.find_chrome()) as br:
    print(br.profile); os.kill(os.getpid(), signal.SIGKILL)"
/tmp/bga-geometry-rvjdhgnx
Killed
$ ls -d /tmp/bga-geometry-* | wc -l
72
$ ps -eo pid,ppid,args | grep -F bga-geometry-rvjdhgnx | head -1
  570     1 …/chrome --headless=new … --user-data-dir=/tmp/bga-geometry-rvjdhgnx
$ du -sk /tmp/bga-geometry-rvjdhgnx
3276    /tmp/bga-geometry-rvjdhgnx
```

Reparented, still running, 3.2 MB held. The 71 above are this
session's: `-n auto` opens one per worker, so an interrupted run
leaks a worker's worth, and round 107 interrupted several.

This is not hypothetical arithmetic. Round 107 read `make test` as
structurally unpassable — 2.77 GB of spend against 1.45 GB of margin —
and filed `UX-760` as the blocker. The spend was real and the
conclusion was wrong: the margin was thin because the leavings had
eaten it. Clearing them passed the gate on the same tree. A test
harness that consumes the disk its own gate is priced against makes
every later disk reading a measurement of session history.

`UX-559` is the precedent and it points the other way: `--serve`'s
scratch leaked, `atexit` was offered as the weaker of two mechanisms
and **declined**, because it does not fire on a signal. The same
argument was available here and the weaker mechanism is what shipped.

## Required Fix

Two halves, and the second is the one that holds.

1. The profile is created under a directory the process can find
   again — one root per binary, named for the pid — so a later run can
   see what an earlier one left. `tempfile.mkdtemp` names nothing.
2. On entry, sweep the roots whose pid is gone: kill the process
   group if it still answers, remove the directory. A session that
   starts cleans up after the one that was killed, which is the only
   point at which anything is running to do it.

`atexit` stays for the ordinary exit; it is not the guarantee.

A guard must red on the leak and not on the mechanism: launch a
`Browser` in a subprocess, `SIGKILL` it, then assert that a *second*
`Browser` entry leaves no directory and no process from the first.
Count before and after against a `tempfile.tempdir` the guard owns —
`UX-559`'s guard does this and is the shape to copy, because under
`-n auto` another worker's browser lands in the same count otherwise.

## Out of Scope

- `UX-760`'s reserve arithmetic. That row is real on its own terms;
  this one is why its urgency was misread.
- `/tmp/pytest-of-root` and pytest's own leavings — `UX-559` drew
  that boundary and it still holds.
- Making the geometry guards not need a browser. `UX-257` decided
  the instrument and a real page is what it measures; a page
  measured without one is a different instrument, not this fix.

## Acceptance Test

```console
$ ls -d $TMPDIR/bga-geometry-* | wc -l     # after a SIGKILLed launch
0
$ pgrep -f bga-geometry | wc -l
0
```
plus a mutation: remove the sweep and the guard reds.

## Outcome

_Not started._
