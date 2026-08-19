# UX-127: cache-logs should take the project you have, not the name it hides

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-91 (done — this is its front door)

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

## Fix Implemented

The positional is now `PROJECT_DIR|LOG_ROOT`, detected by the presence
of `project.conf`. Given a project it reads `name:` from that file and
resolves the log root itself — the obvious invocation does the obvious
thing. A log root still works unchanged, and so does `--project NAME`.

`project.conf` is read directly rather than through BuildStream, for the
same reason `read_declared_build_deps` is: this has to work against a
project directory without loading a plugin, and the name is a plain
top-level key.

Bare `bga cache-logs` (or `--list`) enumerates the tree; `--all` keeps
the old report-over-everything behaviour for anyone who wants it.

## Verification Log

Done 2026-08-19, against a real log tree from this session's builds.

### The obvious argument

```text
$ bga cache-logs examples/09-fine-grained-siblings
============================================================
Cached Build Logs (Plane 3)
============================================================
Read 22 log(s), 11 of them builds, from macro-micro-optimization-example-optimized

Where each element spent its own time:
  tiny-1.bst [df47e0c4] 19-08-2026 13:24:50 (2.0s)
    Staging dependencies at: /           1.0s (50%)
```

No `--project`, no `ls` of the cache.

### Discovery

```text
$ bga cache-logs
============================================================
BuildStream log tree
============================================================
  …/cache-fine2/buildstream/logs

  project                                        logs  elements
  macro-micro-optimization-example-optimized       22        11
      2026-08-19 13:24:50 UTC .. 2026-08-19 13:24:55 UTC

  Report on one with `bga cache-logs PROJECT_DIR` (or --project NAME),
  or on every project at once with --all.
```

### The wrong-argument case from the Motivation

```text
$ bga cache-logs examples/06-macro-micro-optimization
Error: no element logs found under …/logs for project 'macro-micro-optimization-example'
  examples/06-macro-micro-optimization/project.conf declares
  `name: macro-micro-optimization-example`, and that is the log-tree directory
  this looked for.
  The tree holds: macro-micro-optimization-example-optimized
  `bga cache-logs --list` shows all of them with counts and spans.
```

The old message was `no element logs found under
examples/06-macro-micro-optimization. Nothing to report on.` — confidently
wrong about a project whose logs existed. The new one names what was
derived, where it looked, and what is actually there; and here it
happens to reveal a genuinely useful thing, that the *optimized* variant
is what was built and the base project was not.

Tests: 13 added in `tests/unit/test_cache_logs.py` (35 → 48).
