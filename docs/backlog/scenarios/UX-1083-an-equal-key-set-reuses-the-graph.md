# UX-1083: a build whose key set equals the baseline's reads its graph again

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1082 | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R8 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

After every build `extract_run` runs `bst show --deps all` for
`graph.json` (`tools/bst_show_to_graph.py:241-281`), even when nothing
the graph is made of changed. Cache keys cover each element's config,
variables, sources and dependencies, so an equal key set means an
equal graph. Measured with BuildStream 2.8.1:

```text
examples/06 warm (build 1.07s)   bst show --deps all 1.27s
1,201 elements                    11.21s
5,001 elements                    42.28s
```

The warm `examples/06` snapshot's `graph.json` is structurally identical
to the cold one's (every key and value), but that is one pair, not a
general equivalence. `graph.json` also carries fields the key set does
not decide: `requested_target` follows the invocation's targets
(building B, which depends on A, and building A and B name the same
keys), `extract_run` adds the project's `bga-foundation` tier
(`UX-683`), and `max_jobs`/`notparallel` are resolved from the build's
options and configuration, which BuildStream keeps out of cache keys.
This is still the incremental and no-op review build, the most
frequent snapshot a team takes.

## Decomposition

Input classes: key set equal to the baseline's, different, unread
(`UX-1082`); baseline without `graph.json`; different global options
with equal keys. Journey: `bga snapshot`'s tail.

## Required Fix

In `tools/bst_extract_run.py`: the baseline's `graph.json` is reused
only when the whole graph fingerprint matches: the key set, the
requested targets, the `bst` global options, the resolved max-jobs
configuration, and the `bga-foundation` tier. `requested_target`,
`foundation` and the resolved widths (`UX-894`) are then re-applied
from this build rather than copied. Any difference or unread term runs
`bst show` as today. The snapshot records which happened and why.

Review finding (Ruslan, PR #300): a fresh extraction replays the
build's graph-affecting global options (`-o/--option`, `-c/--config`,
`-C/--directory`, `--strict/--no-strict` - read off BuildStream 2.8.1's
own `cli` group) before `show`, `--max-jobs` once from the log. Without
them `bst -o variant b build` wrote variant A's `graph.json` under a
B fingerprint, and a later B capture reused it.

## Out of Scope

Reusing the analysis itself (`UX-1073`).

## Acceptance Test

`tests/unit/test_an_equal_key_set_reuses_the_graph.py`: two snapshots
with the same fingerprint issue one `bst show --deps all` between them
(fake `bst` recording argv), and the second `graph.json` equals the
one a fresh `bst show` would write. Each of these issues the call or
re-derives the field, and matches a fresh extraction: a changed key;
the same keys under different targets (build B vs build A and B, where
B depends on A, so `requested_target` differs); a changed
`bga-foundation`; a changed `--max-jobs`. Mutation: drop any one
fingerprint term, and its case reds.

## Outcome

**Gap measured** (`docs/audits/perf-snapshot-view-2026-09-28.md`,
`bstshim`, `examples/06`): `bst show --deps all` cost 1.27s of a 1.07s
warm build (1.17s of a 34.72s cold one), even when nothing the graph is
made of changed - `bst show` scales to 42.28s at 5,001 elements.

**Close measured**: `tools/bst_extract_run.py`'s `extract_run` gained
`cache_key_set`/`bst_global_options`/`baseline_run_dir` and a
`_graph_fingerprint` of five terms (key set, targets, global options,
resolved max-jobs, `bga-foundation`); `graph.json` is reused from
`baseline_run_dir` only on an exact fingerprint match, and
`requested_target`/`foundation` are re-applied for this invocation
either way. `tests/unit/test_an_equal_key_set_reuses_the_graph.py`: 8
passed - one `bst show --deps all` call between two snapshots sharing
a fingerprint, and each of the four regression cases (changed key,
same keys under different targets, changed foundation, changed
`--max-jobs`) issues its own call and matches a fresh extraction.

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| `cache_key_set` term dropped from `_graph_fingerprint` | all 8 tests (every case now compares equal fingerprints regardless of key) | 8 of 8 |
| `targets` term dropped | `test_the_same_keys_under_different_targets_runs_bst_show_again` | 1 of 1 |
| `bst_global_options` term dropped | `test_different_bst_global_options_with_equal_keys_runs_bst_show_again` | 1 of 1 |
| `resolved_max_jobs` term dropped | `test_a_changed_max_jobs_runs_bst_show_again` | 1 of 1 |
| `bga_foundation` term dropped | `test_a_changed_foundation_runs_bst_show_again` | 1 of 1 |
| `BGA_BASELINE_RUN_DIR` env set dropped (`bga_snapshot.py`) | `test_a_baseline_snapshot_pair_issues_one_bst_show_through_the_snapshot_path` | 1 of 1 |

**Deviation**: `extract_run`'s new `baseline_run_dir` param is not
reached through a CLI flag. `bga_snapshot.take_snapshot` sets
`BGA_BASELINE_RUN_DIR` in the environment (the previous healthy
snapshot's own `run/`, the same `_healthy_baseline` the compare step
already picks) and `tools/bst_native_build_tracer.py`'s `run` reads it
straight from `os.environ`, following the existing `BGA_JOBSERVER_MODE`
precedent (UX-856) - a `--baseline-run-dir` flag was tried first and
reverted: `bga capture run --help` was already at its 66-line cap with
zero headroom (`test_the_nested_capture_run_help_fits_too`), and any
new flag adds at least three lines. `tests/unit/test_the_snapshot_passes_its_baseline_to_the_graph_reuse.py`
(new file, 1 test) proves the wiring end to end through the real
`take_snapshot`/`tracer.main`/`extract_run` path, `run_traced_build`
faked. `docs/guides/cli.md`'s environment inventory gained the row
(`test_the_environment_surface_is_an_inventory.py`).

**Review finding (Ruslan, PR #300)**: a fresh `extract_graph` got
only `--max-jobs`. Gap, measured through the fix's own test with the
options dropped: the `-o variant b` capture's `graph.json` was
`{'app.bst': '8a6d1423'}`, no edges, against `bst -o variant b show`'s
`{'base-b.bst': '6aa1e8b2', 'app.bst': '798170dc'}` and
`base-b.bst -> app.bst`. Close: `_graph_affecting_options` keeps
`-o`/`-c`/`-C`/`--strict` in order, drops every other global option by
its arity, and `extract_graph` gets them ahead of the replayed
`--max-jobs`. `bst_option_project`'s `app.bst` depends on `base-b.bst`
under `variant == "b"`. `tests/unit/test_the_graph_reads_the_builds_options.py`:
3 passed - real builds A, B, B-after-B (reused) and B-after-A (fresh)
each equal an option-aware `bst show --deps all`.

| mutation | reddened | count |
|---|---|---|
| `extract_graph(..., bst_options=replayed)` (options dropped) | the options-in-order-to-`show` test, the real two-variant test | 2 of 3 |
| `-o` branch dropped from `_graph_affecting_options` | all three | 3 of 3 |
| other valued options' values not skipped | the options-kept-in-order test | 1 of 3 |
| unfiltered global options passed (`--max-jobs` twice) | the one-`--max-jobs` test | 1 of 3 |

The new bst-gated file moved three pins: `ci.yml`'s bst tier 52 -> 53,
`test_a_generated_project_builds.py`'s gated population 19 -> 20 (18
CAS-writing), `test_the_loop_stays_fast.py`'s selector p90 61 -> 62.
