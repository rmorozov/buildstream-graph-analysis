# UX-324: a capture that cannot start says so, and leaves nothing

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-125 (doctor's check this reuses), UX-157 (the leaves-nothing rule) | **Serves:** R1 — the first-run experience | **Topic:** capture

## Motivation

Round 45's stranger walk, friction 1: on a machine without `bst`,
`bga snapshot -- bst build all.bst` — the README's own first
command — runs the census happily and then dies in a **30-line
Python traceback** (`FileNotFoundError: ... 'bst'`), while `bga
doctor` on the same machine opens with `[FAIL] bst-present` and a
one-line remedy. Worse, the crash leaves a **debris snapshot**
(`build.log`, `plane2.log`, `capture-context.txt`, no run) —
contradicting the guide's "interrupting before the build starts
leaves nothing behind" — and the debris then poisons later
messages: `--list` describes it as "the build produced no
elements" (the build never started), and `@<stamp-prefix>`
resolution denies it exists while `--list` shows it.

## Required Fix

`snapshot` checks its build command's executable before creating
anything (the doctor check, reused not duplicated) and refuses
with the sentence and the `bga doctor` pointer; nothing is written
on that path. The debris description distinguishes "never started"
from "produced no elements" (the capture context knows which), and
prefix resolution's "Have:" list agrees with `--list` about what
exists.

## Out of Scope

- Debris from mid-build failures (UX-157's salvage rules stand —
  this is only the never-started path).

## Acceptance Test

With a PATH lacking `bst`: snapshot exits with a one-sentence
refusal naming `bga doctor`, exit code documented, and `.bga/runs`
byte-identical before and after (asserted); the traceback is gone
(mutation: bypass the check → the no-debris clause reds). A
never-started debris fixture lists with the honest sentence and
resolves by prefix.

## Outcome (round 47, 2026-08-27) — 🟢 Done

### The friction, reproduced before it was fixed

A fixture project, a `PATH` of `/usr/bin:/bin`, and the README's first
command:

```text
$ bga snapshot -- bst build all.bst
Traceback (most recent call last):
  ... 32 lines ...
  File ".../tools/bst_run_wrapped.py", line 313, in run_wrapped
    proc = subprocess.Popen(
FileNotFoundError: [Errno 2] No such file or directory: 'bst'
EXIT=1

$ find .bga -type f
.bga/.gitignore
.bga/config
.bga/runs/20260827T081619Z/build.log
.bga/runs/20260827T081619Z/capture-context.txt
.bga/runs/20260827T081619Z/plane2.log      # 0 bytes
```

and, on the same machine, `bga doctor`'s first line:

```text
  [FAIL] bst-present: bst is not on PATH
           -> pip install 'bga[bst]' (in a virtualenv - …)
```

The tool knew. Nothing asked it.

### After

```text
$ bga snapshot -- bst build all.bst
Error: bst is not on PATH, so this build cannot start. Nothing was captured and nothing was written.
  -> pip install 'bga[bst]' (in a virtualenv - a distro-patched setuptools breaks pluginbase, which is how three separate environments for this project failed to install)
  `bga doctor` checks this and everything else a capture on this machine needs.
EXIT=2

$ ls -A .
elements  project.conf
```

The check is `bga_doctor.check_bst()`, called rather than copied — it
knows about the `bst` installed beside this `bga` but not on `PATH`
(`UX-150`), and a second `shutil.which` would have had to learn that
again. Only a `FAIL` refuses; an unsupported-version `WARN` is the
doctor's to report and not a reason to decline a build.

**Where it is called matters as much as what it checks.** It runs in
`main`, before `_sticky_config`, because the sticky config, the store's
`.gitignore` and the snapshot directory are all writes on the way to
`take_snapshot`. "Leaves nothing behind" has to mean nothing, and the
guard asserts it by comparing the whole `.bga` tree byte for byte across
the refusal rather than by looking for a directory.

Exit code **2**, which is what `bga snapshot`'s other two refusals — no
project here, nothing to run — already return. Documented in
`docs/guides/cli.md` twice: in the `snapshot` section and in the exit
code table, where `130`'s "interrupting before the build starts leaves
nothing behind" sentence now has its sibling.

### The debris that already exists

Fixing the crash does not un-write the snapshots it left on people's
disks, and the store described them wrongly:

```text
before:  20260827T081619Z   420B  (no run directory - the build produced no elements)
after:   20260827T081619Z   420B  (the build never started - nothing was captured)
```

"Produced no elements" is a claim about a build that *ran*. It sends the
reader to look at their project when the problem is their machine.

The filing said "the capture context knows which"; it does not — it is
written before the build and says only what was attempted. The wrapper
**log** knows, and exactly: `run_wrapped` writes an `Executing command:`
line and a `bga-clocks start` line before `Popen`, and after it either
the build's own output or (on an interrupt) `Stopping the build after
…`. A log whose last line is the clock line is a build that was never
launched, and nothing else in that function produces one. Only the last
4 KB is read, because a real wrapped log is hundreds of megabytes and
this runs once per row.

`store/v1` gains `started`, and it is **tri-state on purpose**: `None`
for a snapshot with no wrapped log at all, which reads exactly like a
build that never ran. Calling that one "never started" would have been
the same overreach in the other direction, and the guard holds both
sides — an unknown snapshot keeps the older sentence.

### The two commands that disagreed about what exists

```text
before:  $ bga snapshot --list
           20260827T081619Z  420B  (…)
           20260827T090000Z  10.7K @last
         $ bga analyze @20260827T0816
         Error: no snapshot in … starts with '20260827T0816'.
         Have: 20260827T090000Z

after:   Error: '20260827T0816' names 1 snapshot(s) in … with no run directory
         (20260827T081619Z). `bga snapshot --list` shows them and says why; an
         alias resolves only to a capture that produced a run.
         Resolvable: 20260827T090000Z
```

The candidate list stays `list_runs` — an alias resolving to a capture
with no run directory is `UX-126`'s original bug and is not being
reopened. What changed is that the *refusal* now reads both lists, so
the difference between them is what the reader is shown rather than what
they have to infer. The same applies when there is no healthy run at
all: that message counted the debris and now names it.

A prefix matching nothing on either list still says "no snapshot in …
starts with", and the guard holds that too — the new branch must not
swallow a typo.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| X1 | `why_the_build_cannot_start` returns `None` unconditionally — the bypass the filing names | 3: the refusal, the no-debris clause, and the non-`bst` case |
| X2 | `build_ever_started` returns `True` unconditionally | 3: the never-started listing, the never-started log shape, the no-log case |
| X3 | `build_ever_started` returns `False` unconditionally | 5: both started-log shapes, the no-log case, and *both* clauses that keep the older sentence — the other direction |
| X4 | the prefix refusal's debris branch removed | 1: the prefix-names-debris clause. The typo clause stayed green, which is what it is for |
| X5 | the no-healthy-run refusal counts the debris instead of naming it | 1: the no-healthy-run clause — a separate branch from X4's, and it needed its own mutation to prove it |

### Deviation from the Required Fix

- The filing said the capture **context** distinguishes never-started
  from produced-nothing. It does not, and could not: it is written
  before the build. The wrapper log does, and exactly. Recorded because
  the difference is the reason the fix reads a log tail rather than a
  key.
- `started` is tri-state rather than the boolean the filing implies, for
  the reason above.
