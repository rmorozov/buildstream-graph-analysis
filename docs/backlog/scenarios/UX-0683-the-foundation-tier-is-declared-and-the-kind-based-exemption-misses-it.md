# UX-683: the foundation tier is declared, and the kind-based exemption misses it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-479, UX-681 | **Serves:** R2 who owns the toolchain and wants out of the noise; R3 reading the ranking | **Topic:** analysis | **Shape:** judgement

## Motivation

```text
bga/ingest/models.py:25   STRUCTURAL_ELEMENT_KINDS = {junction, import, filter, compose, stack}
bga/findings.py:1361-1372 blast-radius-structural: excluded from the ranking, "reaching most of the graph by design"
```

The exemption is by *kind*. A toolchain or a base image is an
`autotools`, `manual` or `cmake` element with a fan-out in the top
percentile *by design* — and it is not exempt, so it tops every
blast ranking as the largest thing to fix, which is the noise the
user described. A discovered tier (top p5 fan-out) moves with the
graph; the honest form is a declaration.

## Required Fix

A `foundation` declaration — an element list in the project's `bga`
config (or a `bga:foundation` annotation the extractor reads from
`project.conf`), validated against the graph — reported as its own
tier in every blast, fan-in and expected-cost ranking: present,
separated, never the top row. The discovery half proposes candidates
(top p5 fan-out among non-structural kinds) and says "declare or
dismiss".

## Out of Scope

- Deciding what is foundation for a project — the owner declares;
  the tool proposes.

## Acceptance Test

Example 06 with `toolchain.bst` declared: the blast ranking's top row
is core.bst, toolchain sits in the foundation tier with its fan-out;
undeclared, the discovery names it; mutation: drop the tier from the
ranking — the tier guard reds.

## Outcome

**Gap measured:** `git show a3bcc2c6:bga/findings.py | grep -c foundation`
→ 0; `git show a3bcc2c6:tools/bst_extract_run.py | grep -c foundation`
→ 0 — no declared tier existed anywhere in the ranking or extractor.

**Close measured:** `python3 -m pytest tests/unit/test_the_foundation_tier_is_declared.py -q`
→ `14 passed`. Real graph (`tests/fixtures/macro_micro`, example 06,
`graph.json` now carries `"foundation": ["toolchain.bst"]`):
`blast-radius-foundation` fires with `elements == ["toolchain.bst"]`
and `blast-radius-reach` (macro_micro is chain-bound, so the *ranked*
arm is gated per UX-65/UX-479) lists `core.bst`, never `toolchain.bst`.
A non-chain-bound synthetic population (`_rank`, mirroring
`test_a_ranking_says_what_to_do.py`) exercises the ranked arm directly:
declaring `toolchain.bst` (kind `cmake`, count 900 vs `core.bst`'s 700)
foundation drops it from `blast-radius-ranking`, whose top row becomes
`core.bst`; undeclared, `foundation-candidates` names `toolchain.bst`
("declare or dismiss") when its count clears the run's own p95.
`tests/fixtures/foundation_declared` (a `fan_in(n=4)` topology,
`sink.bst` declared) reaches `fan-in-foundation` the same way.
`PYTEST_XDIST= make test-touching` → `5910 passed, 98 skipped`, 5
failed: 4 are `Cache too full` (`@pytest.mark.bst`, real `bst show`
against the shared BuildStream cache) and 1 is the review-cadence
guard (`docs/backlog/scenarios/closed.md` row count) — both confirmed
identical on `a3bcc2c6` via `git stash`, unrelated to this diff.
`make lint` → `All checks passed!` / `clean: 568 finding(s) match
tests/quality_baseline.json` (0 new).

**Mutation table** (each: copy of `bga/findings.py`/`bga/graph/fan_in.py`
saved, mutated, `pytest tests/unit/test_the_foundation_tier_is_declared.py -q`,
restored from the copy, re-run green):

| mutation | reddened | count |
|---|---|---|
| `actionable` (blast ranking) drops the `is_foundation` exclusion | `test_a_declared_non_structural_element_does_not_lead` | 1 failed, 13 passed |
| `top_fan_in` drops the `is_foundation` exclusion | `test_the_declared_sink_is_excluded_from_the_fan_in_ranking` | 1 failed, 13 passed |
| `_foundation_candidates` drops the `is_foundation` exclusion | `test_a_declared_element_is_never_proposed_as_a_candidate` | 1 failed, 13 passed |

All three restored to `14 passed`.
