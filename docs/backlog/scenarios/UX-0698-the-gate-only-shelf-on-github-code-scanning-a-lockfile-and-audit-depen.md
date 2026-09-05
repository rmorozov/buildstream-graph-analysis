# UX-698: the gate-only shelf on GitHub — code scanning, a lockfile and audit, Dependabot, secret scanning

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-693 (the local shelves first) | **Serves:** R8 reading a red gate that a hosted tool raised, and the user who wants the heavier analyses without a slower inner loop | **Topic:** guards

## Motivation

`.github/workflows/` has `ci.yml` and `real-project-capture.yml`; no
`codeql*`, no `dependabot.yml`, no audit step. `pyproject.toml:25-33`
ranges every dependency with `>=` and there is no lockfile, so
`pip-audit` in round 93 could only read the ambient environment (37
advisories, none in `networkx` or `pyyaml`). `bandit -r bga tools -ll`:
2 High, 14 Medium, the shown one `B314` (`ElementTree.parse` on
untrusted XML, `tools/dev_tier_drift.py:298`). `bga view` serves a page
built from other people's logs; a field that reaches the page reaches
a browser (`REVIEW.md`, the security pass).

## Required Fix

A second workflow, `quality.yml`, on pull requests and a weekly
schedule, never in `make lint`: **code scanning** — CodeQL
(`python`, `javascript`); the repository is public, so code scanning
is free and `semgrep` is not needed; **a lockfile** (`uv lock` or `pip-compile`
into `requirements.lock`) committed and `pip-audit -r` against it;
**Dependabot** for pip and actions, weekly, grouped; **secret
scanning** with push protection on the repository. Each tool's
findings land as check annotations, not as a comment. The `B314` and
the two bandit Highs are fixed here, with the finding id in the
commit.

## Out of Scope

- Running any of these locally or in the edit hook — the shelf exists
  so the inner loop stays at `ruff`'s 10 ms.
- Pinning runtime dependencies in `pyproject.toml` — the lockfile pins
  the dev environment; a user's install keeps the ranges.

## Acceptance Test

`quality.yml` green on the adopting branch; `pip-audit -r
requirements.lock` clean; mutation: add `requests==2.19.1` to the
lockfile — the audit step reddens; commit a fake `AKIA…` key in a
fixture — push protection refuses it.
