# UX-869: the jobserver FIFO mounts under the bind destination

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-841, UX-846 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R2 (a cmake element builds under the mode on a project that is not under /tmp) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`open_jobserver` makes the FIFO under the trace's bind dir, which lives
at `<project>/.bga/tmp/trace-*/bind` by design (`UX-155`), and the shim
binds it onto its own host path: `--bind <fifo> <fifo>`
(`_jobserver_injection`, the line `UX-841` describes as "a bind of the
FIFO onto itself"). The sandbox root is read-only and the project's
path does not exist inside it, so bwrap fails to make the parents:
`can't mkdir parents for .../my_project/.bga/tmp/trace-*/bind/
jobserver: read-only file system`, and the build dies on its first
cmake element. `UX-846` moved the wrappers under the fixed `bind_dst`
(`/tmp/.bst-native-trace`) for the same reason and never reached the
FIFO. The bind is only injected under fifo-style auth, which
`jobserver_auth_style("auto")` picks for GNU Make 4.4 and newer on the
host; this box and CI run 4.3, fd style, so the defect never fired
here and the user's host hit it at once.

## Required Fix

`tools/native_trace/bwrap_shim.py`: the FIFO is not mounted on its own,
since it already sits inside the bind dir the shim mounts at
`bind_dst`, so the in-sandbox path is `bind_dst/jobserver`; `MAKEFLAGS`'s
`--jobserver-auth=fifo:<path>` and the wrappers' `BST_TRACE_JOBSERVER`
carry that path, and the host path stays with the tracer's own
reader. `tools/bst_native_build_tracer.py`: the `--diagnose` record
names both paths.

## Decomposition

Input classes: fd style (no bind), fifo style with the bind dir under
the project, fifo style with it under `/tmp`; the journey it extends is
the user's first build under the mode on a project outside `/tmp`.

## Out of Scope

The auth style choice (`UX-841`); a bind dir outside the project.

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: a fake `bwrap` on `PATH` that refuses
any `--bind`/`--ro-bind` destination outside `bind_dst` and `/tmp`
(exit 1 with bwrap's own message) runs the fifo-style injection clean,
and the composed `MAKEFLAGS` names `bind_dst/jobserver`; mutation:
restore `--bind <fifo> <fifo>` - red. A live pair on `examples/11` with
`--jobserver-auth fifo` from this box pasted in the Outcome.
