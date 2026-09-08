# UX-683: the foundation tier is declared, and the kind-based exemption misses it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-479, UX-681 | **Serves:** R2 who owns the toolchain and wants out of the noise; R3 reading the ranking | **Topic:** analysis | **Shape:** judgement

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

**Gap measured:** `git show cc202d2c:bga/findings.py | grep -c foundation`
→ 0; `git show cc202d2c:tools/bst_extract_run.py | grep -c foundation`
→ 0 — no declared tier existed anywhere in the ranking or extractor.

**Two decisions the code carries:**

- **No `--foundation` CLI flag.** `extract --help` was already at
  `test_help_is_short.py`'s 45-line cap with zero headroom; any new
  flag pushed it over. `project.conf` is the only user-facing
  declaration path; `extract_run(foundation=...)` stays a
  programmatic caller's kwarg.
- **Declared beats kind.** An element that is both declared foundation
  and a `STRUCTURAL_ELEMENT_KINDS` kind (`toolchain.bst` is `import`)
  reports under `blast-radius-foundation`/`fan-in-foundation`, not the
  kind-based finding - the declaration is the stronger, human claim.
- **The declaration is `variables: {bga-foundation: "a.bst,b.bst"}`,
  not a top-level `bga:` key** - real `bst show` against
  `examples/06-macro-micro-optimization` (schema-only, no artifacts)
  gave `Unexpected key: bga`; `variables:` values must be scalars
  (`Value of 'bga-foundation' is not of the expected type 'scalar'`
  on a list), so a comma-separated string is the one shape both real
  checks accept. `examples/06-macro-micro-optimization/project.conf`
  now declares it.

**Close measured:** `python3 -m pytest tests/unit/test_the_foundation_tier_is_declared.py -q`
→ `14 passed`. `tests/fixtures/macro_micro` (example 06) is
chain-bound (`UX-65`/`UX-479`), so only `blast-radius-foundation`
(`elements == ["toolchain.bst"]`) and `blast-radius-reach` (lists
`core.bst`, never `toolchain.bst`) publish there; the *ranked* arm
(`blast-radius-ranking`) is exercised on a synthetic, non-chain-bound
population instead - declaring `toolchain.bst` (900) foundation drops
it and `core.bst` (700) leads. Undeclared, `foundation-candidates`
names it. `tests/fixtures/foundation_declared` (`fan_in(n=4)`,
`sink.bst` declared) reaches `fan-in-foundation`.
`python3 -m pytest tests/unit/test_bst_extract_run.py -q` → `23
passed`. `python3 -m pytest
tests/unit/test_a_committed_analysis_matches_the_analyzer.py -q` →
`6 passed`. `PYTEST_XDIST= make test-touching` → `5910 passed, 98
skipped`, 5 failed: 4 `Cache too full` (`@pytest.mark.bst`) and 1 the
review-cadence guard (`closed.md` row count) - both confirmed
identical on `cc202d2c` via `git stash`, unrelated to this diff.
`make lint` → clean, 0 new findings.

**Fixture regeneration attempted, blocked, documented per-instruction:**
`tests/fixtures/macro_micro/run/graph.json` (last produced by `UX-276`
copying a real `bga snapshot` store) still carries a hand-typed
`"foundation"`. `bst --directory examples/06-macro-micro-optimization
show all.bst` (real `bst 2.8.0`, real staged toolchain via
`examples/stage_cpp_toolchain.sh`) loads the corrected project.conf
and reaches staging, then: `Cache too full` - this machine's `bst show`
fails identically on every real project with local sources
(`tests/unit/test_bst_show_to_graph.py`'s two `@pytest.mark.bst`
failures above, confirmed independent of any project.conf content).
The hand-edit stays; `_read_bga_foundation` is exercised for real by
the new `extract_run`-level test below instead.

**Mutation table** (each: copy saved, mutated, pytest run, restored
from the copy, re-run green):

| mutation | reddened | count |
|---|---|---|
| `actionable` (blast ranking) drops the `is_foundation` exclusion | `test_a_declared_non_structural_element_does_not_lead` | 1 failed, 13 passed |
| `top_fan_in` drops the `is_foundation` exclusion | `test_the_declared_sink_is_excluded_from_the_fan_in_ranking` | 1 failed, 13 passed |
| `_foundation_candidates` drops the `is_foundation` exclusion | `test_a_declared_element_is_never_proposed_as_a_candidate` | 1 failed, 13 passed |
| `bst_extract_run.py:417-424` collapsed to `graph["foundation"] = sorted(declared_foundation)` (no validation, no warning) | `test_a_name_not_in_the_graph_is_a_diagnostic_not_a_crash` | 1 failed, 13 passed |

All four restored to `14 passed`.

**Deviation.** The declaration is `variables: {bga-foundation: toolchain.bst}` in project.conf, not a `bga:` block: BuildStream 2.8 rejects an unknown top-level key and a list-valued variable, both shown on the real project. The `--foundation` CLI flag was dropped (the help screen sits at its 45-line cap); expected cost lives in `correlate.py`, not `findings.py`. Five exact-count guards moved with the new field, each re-derived with the number. The macro_micro fixture's field stays typed: the extractor could not run here (`Cache too full` on a shared CAS), stated in the Outcome. One verifier hold (a proxy validation test, the undisclosed decisions), fixed in a second commit (8225900a). Two commits, one verifier.
