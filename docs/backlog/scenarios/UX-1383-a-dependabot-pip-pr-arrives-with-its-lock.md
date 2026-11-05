# UX-1383: a dependabot pip pull request arrives with its lock

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** `retro-2026-10-26.md` proposal 1, repeated in `retro-2026-11-02.md`; Ruslan filed it on the decision card, 2026-11-05 19:54 UTC | **Serves:** every dependabot pip bump, and the owner's time per bump | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Four of four dependabot pip pull requests (`#302`, `#322`, `#332`,
`#334`) went red on `pip-audit`'s lock check, `bst-tests`' lint and
`test (3.12)` until a hand `requirements.lock` commit landed, and waited
0, 5, 9 and 1 days for it. Dependabot edits `pyproject.toml` only.

## Required Fix

A dependabot pip pull request carries a lock that `quality.yml`'s check
accepts without a hand commit: a job on `dependabot/pip/*` that runs
`make lock` and pushes it, or an ecosystem that writes the lock itself.

## Out of Scope

Auto-merging dependabot pull requests.

## Acceptance Test

The next dependabot pip pull request is green on its first CI run with
no commit but dependabot's and the lock job's.

## Outcome
