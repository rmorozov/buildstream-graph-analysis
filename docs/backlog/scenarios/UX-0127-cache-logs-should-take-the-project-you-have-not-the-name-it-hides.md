# UX-127: cache-logs should take the project you have, not the name it hides

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-91 (done — this is its front door)

Post-MVP polish, direction: simplify the user scenarios.

## Motivation

Plane 3's whole pitch is "costs nothing — reads what is already on
disk", and its front door undercuts it. The thing a user *has* is a
project directory; the thing `bga cache-logs` wants is the project's
**name** (BuildStream's log-tree directory name), discoverable only by
listing `~/.cache/buildstream/logs/` yourself. Round 13, live:

```text
$ bga cache-logs examples/06-macro-micro-optimization
Error: no element logs found under examples/06-macro-micro-optimization. Nothing to report on.
```

The positional is the log *root*, so handing it the obvious argument —
the project — produces a confidently wrong "nothing to report" about a
project whose logs exist two directories away. The audit itself used
`--project macro-micro-optimization-example-optimized` for three
rounds, a value obtained by `ls`-ing BuildStream's cache, which is
precisely the folklore step Plane 3 exists to not need.

## Required Fix

1. A project-directory argument (`bga cache-logs PROJECT_DIR`, detected
   by the presence of `project.conf`) that reads the name from
   `project.conf` and resolves the default log root itself — the
   obvious call does the right thing.
2. Bare `bga cache-logs` (or `--list`) enumerates what the log tree
   holds: project names, log counts, time spans — so discovery is the
   tool's job. The current bare-invocation behaviour (report over
   everything) moves behind an explicit `--all`, because "report on
   every project I ever built" is never what one user's question is.
3. The misleading error becomes a redirect: given a path that is a
   project but not a log root, say which project name was derived and
   whether the tree has it, rather than "nothing to report".

## Out of Scope

- Non-default BuildStream cache locations beyond honoring
  `XDG_CACHE_HOME` (already the log tree's own rule).
- Any analysis change.

## Acceptance Test

`bga cache-logs examples/06-macro-micro-optimization` (after one real
build) renders that project's Plane 3 report with no `--project` flag.
Bare `bga cache-logs` lists the machine's projects with counts and
spans. The wrong-argument case from Motivation names the derived
project and where it looked. `--project NAME` keeps working unchanged.
