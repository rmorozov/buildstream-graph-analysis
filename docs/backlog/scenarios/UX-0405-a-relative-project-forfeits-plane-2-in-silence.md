# UX-405: a relative `--project` forfeits Plane 2 in silence

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-155 (the cwd lesson this module already recorded once), UX-376 (the census that should have refused) | **Serves:** R1, on the first capture they ever run | **Topic:** capture

## Motivation

Round 64's walk ran the documented shape from the repo root:

```text
$ bga snapshot --project examples/06-macro-micro-optimization \
      --trace-opens --trace-spine=on -- bst build lib-c.bst
Processes traced: 0 (0 matched, 0 no observed exit)     exit 0
```

Empty `plane2.log.gz`, green snapshot. The identical command with an
absolute path — or run from inside the project — traces 87 of 87.
The walk's "all planes" conclusion held only because the capture was
re-run from inside the project; a stranger keeps the zero.

Mechanism: `capture_scratch` roots the shim scratch at
`scratch_dir(project_dir)` and prepends the **relative** `shim_dir`
to `PATH` before `subprocess.Popen(cmd, cwd=project_dir, ...)`
(`tools/bst_native_build_tracer.py`, ~line 1020). A relative `PATH`
entry resolves against each process's *own* cwd — and
`buildbox-casd` chdirs away, exactly as this module's own `UX-155`
docstring records for `TMPDIR`. So nothing finds the shim and the
real `bwrap` runs untraced. `BST_TRACE_BIND_SRC` is relative too.
The capture even half-knows — it prints "ELEMENT ATTRIBUTION
UNRELIABLE: no process carried an element tag at all" — and
completes green anyway.

## Required Fix

- Absolutize `project_dir` (and everything derived from it: shim
  dir, `PATH` entry, `BST_TRACE_BIND_SRC`, scratch paths) at entry,
  the same normalization `UX-155` applied to `TMPDIR`.
- A traced build that matches **zero** processes while Plane 2 was
  requested is a refusal or a loud degradation, not a green line —
  `UX-186`'s refusal grammar, and the census (`UX-376`) already has
  the "could not assess" vocabulary for it.

## Out of Scope

- `--project` pointing at a directory that is not a project at all —
  that acceptance bug is `UX-410`'s, with a different mechanism.
- Re-litigating whether attribution warnings should be fatal in
  general — only the zero-traced-processes case turns loud here.

## Acceptance Test

- From the repo root, the relative invocation above either refuses
  with a sentence naming the fix or traces 87/87 like the absolute
  one; byte-identical plane2 results between the two shapes.
- Falsification: re-relativize the `PATH` entry — the new guard
  (unit-level, no bst needed: assert every `PATH` prepend and bind
  source the tracer builds is absolute) goes RED.

## Outcome (round 65, 2026-08-29) — 🟢 Done

### The gap, and the fix, on the documented invocation

The same command, from the repository root, against the same **cold**
`lib-c.bst` (its artifact deleted between the two runs so both build
from source):

```text
bga snapshot --project examples/06-macro-micro-optimization \
    --trace-opens --trace-spine=on -- bst build lib-c.bst

before   Processes traced: 0 (0 matched, 0 no observed exit)
         ELEMENT ATTRIBUTION UNRELIABLE: no process carried an element tag at all
         exit 0

after    Processes traced: 87 (87 matched, 0 no observed exit)
         By element:  lib-c.bst  87
         Wall span: 2.589s
         Real CPU time: 3.80s across 87 of 87 traced processes
         exit 0
```

Zero to eighty-seven of eighty-seven, from one `os.path.abspath`.

**A third run, worth recording because it is the case the second
clause exists for.** Between those two, a run of the same shape against
`lib-d.bst` also traced 0 — and that one is *correct*: `lib-d` was
already cached, no sandbox launched, and nothing was there to trace.
The new warning stayed silent on it, which is the distinction the whole
second half of this item is about.

### The fix

`project_dir` is absolutised at two places, and both are load-bearing:

- **`run_traced_build`'s entry**, which is what `Popen(cwd=...)` gets;
- **`capture_scratch`**, the choke point every derived path is joined
  onto — the shim directory that goes on `PATH` and
  `BST_TRACE_BIND_SRC`. `scratch_mkdtemp` reaches it by a second route
  that never passes through `run_traced_build`, so one site would have
  left the raw-log and Plane 1 scratch relative.

And `format_untraced_build_warning`: a capture that recorded zero
processes **while sandboxes ran** says so, on stderr, after the report.
Three states, `UX-376`'s vocabulary:

```text
0 traced, 9 sandbox tasks   PLANE 2 CAPTURED NOTHING ... + what to run next
0 traced, 0 sandbox tasks   silent - a cached build legitimately traces nothing
0 traced, no Plane 1 log    silent - "cannot say" is not a verdict
```

A **loud degradation rather than a refusal**, which is the choice the
Required Fix offers: the wrapped build's exit code is the wrapped
build's (`run_traced_build`'s own contract, in its docstring), and a
capture must never change whether a build succeeded.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `run_traced_build`'s entry absolutise removed | the cwd clause (1 failed, 5 passed) |
| A2 | `capture_scratch`'s absolutise removed | the PATH-and-bind clause (1 failed, 5 passed) |
| A3 | the warning never fires | the sandboxes-ran clause (1 failed, 5 passed) |
| A4 | the warning fires on a cached build too | the result-not-failure clause (1 failed, 5 passed) |
| A5 | the warning keeps its prose and drops its count | the count clause (1 failed, 5 passed) |

A1 and A2 are the pair that shows the two sites are not redundant: each
reverted alone leaves the other's paths absolute and reddens a
different clause.

### The guard runs without `bst`

`test_a_capture_finds_its_own_shim.py` drives the **real**
`run_traced_build` from a relative `--project` — real scratch, real
compiled hook, real installed shim — and intercepts only the `Popen`
that would spawn the build, reading the environment it would have
inherited. The two existence checks are made at spawn time rather than
after the call, because the scratch is a context manager and is gone by
then; the first version checked a deleted path.

### Deviation from the Required Fix

**None.** Both bullets landed. The zero-traced case is the loud
degradation rather than the refusal, which the Required Fix names as
the alternative and `run_traced_build`'s exit-code contract decides.

### Verification

```text
pytest tests/unit/test_a_capture_finds_its_own_shim.py         6 passed
pytest -k "capture or trace or snapshot or scratch or tmpdir"
                                              663 passed, 2 skipped
make lint                                                      clean
```

## Follow-up (round 64, from CI)

The guard this item landed
(`test_every_path_the_build_inherits_is_absolute`, in
`test_a_capture_finds_its_own_shim.py`) was skip-gated on a C compiler
and not on `bwrap`, so it passed here and failed on **every** CI
runner:

```text
tools/bst_native_build_tracer.py:179: in install_bwrap_shim
    raise TraceError("no real bwrap found on PATH - required for the
                      shim to fall back to")
E   TraceError: no real bwrap found on PATH
============ 1 failed, 2748 passed, 39 skipped in 21.61s ============
```

`install_bwrap_shim` writes a shim that *falls back* to the real
`bwrap` and refuses when there is none. The clause reaches that call
before it reaches anything it is about, and the `test` job installs a
compiler and no sandbox - so the environment it needs is wider than the
one it declared.

That is `UX-213`'s class exactly: a guard that only guards one machine.
Fixed with a second `skipif` and a one-string reason
(`NO_BWRAP`) so the skip census counts it once. Verified by running the
file with a PATH that has no `bwrap`:

```text
SKIPPED [1] tests/unit/test_a_capture_finds_its_own_shim.py:80:
            no bwrap for the capture's shim to fall back to
========================= 5 passed, 1 skipped =========================
```
