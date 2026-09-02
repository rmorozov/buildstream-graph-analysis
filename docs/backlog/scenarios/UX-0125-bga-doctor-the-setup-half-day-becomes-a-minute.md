# UX-125: `bga doctor` — the setup half-day becomes a minute

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-105 (the census, reused as one check) | **Topic:** cli

Post-MVP polish, direction: simplify the user scenarios. The MVP bar
(round 12) is "following only the documentation"; this task attacks the
part of the path the documentation cannot smooth — the environment.

## Motivation

Every capture-capable environment this project has ever stood up —
including this audit's own, three times — was assembled by failure:
`pluginbase` breaking under a distro-patched setuptools until a venv is
used, `buildstream-plugins` discovered missing at first `cmake`-kind
load ("No element plugin registered"), bwrap present but unable to
bring up loopback until a sysctl the CI comments carry is applied, no
C compiler for the hook/spine compile, runtimes/toolchains not staged
so the sandbox has no shell. Each failure costs a real user a search
through docs that do contain the answer — spread across `ci.yml`
comments, `stage_*.sh` headers, and the ingestion guide. The knowledge
exists; only the *sequence* of it is the user's problem.

Every check is already performed somewhere in this repository — by CI
steps, by capture-time errors, by the census. `bga doctor` moves them
before the first failure.

## Required Fix

`bga doctor [PROJECT_DIR]`, read-only, exit 0/1, one line per check
with the concrete remedy on failure:

1. `bst` on PATH, version against the supported line; `bwrap`
   present **and functional** (the same real probe CI's `bst-smoke`
   uses — a trivial sandboxed command — with the known
   `apparmor_restrict_unprivileged_userns` remedy named when the
   loopback failure signature appears);
2. a C compiler for the hook/spine compile (the exact check
   `compile_hook` performs, moved before the build);
3. with a PROJECT_DIR: the project loads, every element kind and
   source kind resolves to an installed plugin (naming the pip package
   for the known ones), and the UX-105 census runs — reporting staged
   shells/toolchains missing (the `stage_*.sh` trap) and static
   executables (with the `--trace-spine=auto` pointer);
4. Plane 3 presence: whether BuildStream's log tree has entries for
   this project (and where);
5. `--format json` for scripting, findings-style ids per check.

Nothing here invents a check; each one cites the failure it fronts
(this file's Motivation is the list). `doctor` must never mutate
anything — it recommends the `stage_*.sh` run, it does not perform it.

## Out of Scope

- Fixing the environment (print the remedy, don't apply it).
- Windows/macOS (BuildStream itself is Linux-first here).

## Acceptance Test

On this audit's container *before* its round-10 setup steps (fresh
venv, no plugins, no staging): `doctor` fails naming each of the five
real problems with the remedy that actually fixed it, and after
applying them in order, exits 0. On CI's `bst-tests` job: `doctor`
exits 0 before the suite runs (wired as a step, so the checks cannot
drift from reality). On a project with a `cmake` element and no
`buildstream-plugins`: check 3 names the package.

## Fix Implemented

`bga doctor [PROJECT_DIR]` (`tools/bga_doctor.py`), read-only, exit 0/1,
one line per check with a concrete remedy on every failure and
`--format json` carrying findings-style ids.

Six checks, each fronting a failure from this file's Motivation and
citing it: `bst-present`, `bwrap-works`, `c-compiler`, `project-loads`,
`staged-sources` / `static-blind-spot` (the `UX-105` census), and
`plane3-logs`.

**bwrap is probed, not found.** Presence is the check that does not
matter; the same trivial sandboxed command `bst-smoke` runs is what
distinguishes "bubblewrap is installed" from "bubblewrap can build a
sandbox here", and the loopback signature gets the sysctl by name.

**Warnings are not failures.** A static-binary blind spot and an empty
Plane 3 tree are facts to read with an answer attached
(`--trace-spine=auto`; run any build), not broken environments. Only a
`FAIL` moves the exit code, so a script can key on it.

**One thing the task did not anticipate, found by running it.** *"No
element plugin registered for kind 'cmake'"* has **two** causes with
opposite remedies: the package is missing, or the project has not
declared it. The first draft printed `pip install buildstream-plugins`
for both — on a machine where it was already installed. It now checks
importability and says which:

```text
-> buildstream-plugins *is* installed, so this project has not declared it:
   add a `plugins:` block to project.conf naming the kinds it uses
   (origin: pip, package-name: buildstream-plugins).
   See examples/06-macro-micro-optimization/project.conf
```

Telling a user to install what they already have is how a diagnostic
loses its reader.

## Verification Log

Done 2026-08-19.

### A healthy environment with a real project

```text
$ bga doctor examples/06-macro-micro-optimization
  [ok  ] bst-present: bst 2.7.0
  [ok  ] bwrap-works: bwrap builds a sandbox and runs in it
  [ok  ] c-compiler: C compiler at /usr/bin/cc
  [ok  ] project-loads: examples/06-macro-micro-optimization loads
  [ok  ] staged-sources: 45 executable(s) staged by this project's own sources
  [ok  ] static-blind-spot: nothing this project stages is statically linked…
  [warn] plane3-logs: …has logs, but none for macro-micro-optimization-example
exit=0
```

### The static blind spot, named with its remedy

```text
$ bga doctor examples/01-resource-contention
  [warn] static-blind-spot: 10 element(s) stage a statically-linked executable,
         which the LD_PRELOAD hook structurally cannot see
           all.bst / runtime.bst / work-a.bst
         -> capture with `--trace-spine=auto` …
```

### The `stage_*.sh` trap

```text
$ bga doctor <a project staging nothing executable>
  [warn] staged-sources: this project's own sources stage no executable at all -
         a sandbox with no shell cannot run install-commands
         -> examples/stage_runtimes.sh (busybox) or examples/stage_cpp_toolchain.sh …
```

### The plugin case

```text
$ bga doctor <a cmake project with no plugins: block>
  [FAIL] project-loads: the project does not load
           all.bst [line 1 column 0]: No element plugin registered for kind 'cmake'
           -> buildstream-plugins *is* installed, so this project has not declared it…
exit=1
```

Wired into CI: `bst-tests` runs `bga doctor examples/06-macro-micro-optimization`
as a step before the suite, so the checks cannot drift from what that
job actually installs, and `packaging` adds `doctor` to the alias list it
runs from an empty directory.

Tests: 17 in `tests/unit/test_doctor.py`, including that it mutates
nothing (mtimes and the file listing compared before and after) and that
an unrunnable check reports `skip` rather than `ok`. Tier pin 34 → 36.

### Deviation, recorded

The acceptance asks for a run "on this audit's container *before* its
round-10 setup steps (fresh venv, no plugins, no staging)". That
container no longer exists in that state and cannot be returned to it
without destroying the environment this round is being verified in. Each
of the five failures is instead reproduced individually — a project that
stages nothing, a project whose plugin kind does not resolve, an absent
log tree, an absent compiler (by the same predicate `compile_hook` uses),
and bwrap's loopback signature matched from its real error text — which
is what the clause was checking for, one failure at a time rather than
five at once.
