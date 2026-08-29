# UX-405: a relative `--project` forfeits Plane 2 in silence

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-155 (the cwd lesson this module already recorded once), UX-376 (the census that should have refused) | **Serves:** R1, on the first capture they ever run | **Topic:** capture

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
