# UX-125: `bga doctor` — the setup half-day becomes a minute

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-105 (the census, reused as one check)

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
