# UX-887: the implementer brief's dev-deps reinstall repoints the shared editable install

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** — | **Found by:** round 127 (both UX-881 and UX-882 tracks: the brief's "reinstall dev deps if missing: `pip install -e '.[dev]'`" fallback repointed the shared editable `bga` install at the worktree it ran from — the round-109 failure mode CLAUDE.md opens with; both caught it via `pip show bga` and restored) | **Serves:** the pipeline (a track's env setup does not silently redirect every other track's and the orchestrator's `import bga`) | **Topic:** guards | **Area:** tools-dev | **Shape:** judgement

## Motivation

The `implementer` brief this session writes tells a track, when dev deps
are missing, to run `pip install -e '.[dev]'`. Run from inside a linked
worktree that is the CWD, that repoints the **shared** editable `bga`
install (`pip show bga` → "Editable project location: <worktree>"), so
every other track and the orchestrator's `import bga` resolves to that one
worktree — exactly the round-109 defect CLAUDE.md's header names. Round
127's two tracks each hit it and each restored it by hand
(`pip install -e /home/user/buildstream-graph-analysis`), but the brief
should not lead a track into it. A second, related snare: a stale
`/root/.local/bin/ruff` (0.15.8) shadows the pinned `/usr/local/bin/ruff`
(0.16.7) on PATH, so a track's `make lint` / `dev_baseline.py` can read a
wrong ruff and nearly rewrite `quality_baseline.json` with a bad
`ruff_version` (a UX-882 track near-miss).

## Required Fix

Fix the brief/skill guidance a track is given, and — where a guard can —
catch the hazard: the dev-deps step must not repoint the shared install
(install the pinned tools without `-e .` from the worktree, or `-e` the
**main checkout by absolute path**), and lint must use the pinned `ruff`
(a `PATH` that puts `/usr/local/bin` first, or invoking the pinned binary
by path). Consider a cheap check the orchestrator runs before a merge gate:
`import bga` from `/tmp` resolves to the main checkout, and `ruff --version`
is the pinned one.

## Out of Scope

Reworking the worktree isolation itself. The `quality_baseline.json`
single-line-JSON diff friction (a separate `jq`-diff-helper filing if
wanted).

## Acceptance Test

TBD by the fix: a brief/skill line no longer names the repointing command,
and (if a guard is built) a pre-gate check fails when `import bga` resolves
outside the main checkout or `ruff` is not the pinned version. Judgement
because the fix is partly to session guidance, not only code.

## Outcome

_(filed round 127, not built — deferred)_
