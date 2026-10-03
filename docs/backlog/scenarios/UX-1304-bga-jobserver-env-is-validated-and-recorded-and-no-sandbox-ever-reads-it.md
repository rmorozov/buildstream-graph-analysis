# UX-1304: `bga-jobserver-env` is validated and recorded, and no sandbox ever reads it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-851` filed `variables: {bga-jobserver-env: "NAME=-j"}` so an
unknown kind could join the jobserver; `tools/bst_extract_run.py:424`
reads and validates it into `run_context.jobserver_env`, and nothing in
the shim or tracer consumes it - `kind_job_env`
(`tools/native_trace/bwrap_shim.py:350`) joins an unknown kind only on a
composed `MAKEFLAGS`/`JOBS`/`MAXJOBS`.

```text
$ grep -rn jobserver_env --include=*.py bga tools | grep -v tests | cut -d: -f1 | sort -u
bga/disclosure.py
tools/bst_extract_run.py
```

## Decomposition

Input classes: an unknown-kind element with a declared `bga-jobserver-env`; one without; a shipped kind with a declaration; a malformed entry (already refused at read). Journey: `bga capture run --jobserver auto` on a custom-plugin project, then `jobserver_decisions`.

## Required Fix

Either the shim sets the declared `NAME` for an unknown kind, or the
declaration is documented as a record only; no guide names it today.

## Out of Scope

The per-kind table itself.

## Acceptance Test

A capture of an unknown-kind element under a declared
`bga-jobserver-env` reads `joined` in `jobserver_decisions`, or the doc
says it never will. Reading taken in this container.

## Outcome
