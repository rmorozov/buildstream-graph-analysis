# UX-760: six more files build against the broken reserve

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-755 (the mechanism and the fix's shape) | **Serves:** the session that runs `make test` on a container with a large disk and little free space | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-755` established the mechanism — BuildStream sizes its 5% cache
reserve against `disk_usage().total`, never `.free`, so on a 270 GB
filesystem with 13-17 GB free the reserve straddles what is left and
`bst build` refuses with `Cache too full` — and fixed one file with a
repo-owned `$XDG_CONFIG_HOME` carrying absolute values.

Its Required Fix named one file. The Motivation did not: the same
run that proved the mechanism reddened seven files at once, on a
branch touching nothing in the capture path.

```text
test_a_generated_project_builds.py       2 failures
test_blast_ranking_discriminates.py      1
test_bst_checkout_cost.py                1
test_bst_extract_run.py                  3
test_bst_extract_run_strict.py           2
test_build_root_override_join.py         2
test_shared_source_blast.py              1
                                        12 failed, 7606 passed in 593.08s
```

All twelve pass alone. `UX-755`'s verifier confirmed each of the six
remaining files invokes real `bst` and none sets the reserve, so the
gate is one-eighth repaired: a session running `make test` on this
container still gets failures it cannot act on, which is the defect
`UX-755` was filed on.

One of them is worth naming. `test_a_generated_project_builds.py`'s
`_isolated()` sets `XDG_CONFIG_HOME` to `home / "config"` and never
creates that directory, so BuildStream finds no file and falls back
to the 5% default — an isolation mechanism that looks like protection
and gives none.

## Required Fix

Reach the six with the same override `UX-755` proved, without copying
its two config files six more times — one fixture the real-`bst`
tests share, named once. `_isolated()`'s empty directory becomes that
fixture rather than a hole.

## Out of Scope

- The upstream arithmetic. `disk_usage().total` for a percentage
  reserve is BuildStream's, in `/usr/local/lib/python3.11/dist-packages`,
  and not ours to patch.
- `test_the_journey_has_an_answer_key.py`, already fixed by `UX-755`.
- A skip. `UX-755` established the fix works; skipping six files would
  hollow out the whole real-`bst` lane on any host of this shape.

## Acceptance Test

With the margin driven negative, all seven files pass where six
currently fail. Mutation: point the shared fixture at a config
carrying `reserved-disk-space: 5%` and they redden again — the
control `UX-755`'s verifier ran, applied to the six.

## Outcome

**The gap measured — wider than the row's own list.** A round-107
`make test` (cleared, quiet host, margin `+1.450 GB` at start,
`-1.321 GB` by the end - the suite spends 2.77 GB of its own temp) gave
`3 failed, 7983 passed, 83 skipped in 346.88s`:
`test_stream_merge.py::test_a_static_build_reports_itself_unmeasurable_
rather_than_clean` and `test_spine_ground_truth.py`'s two `UX-741`
clauses - none of the row's seven. Derivation: every file gating on
`shutil.which("bst")` (15), minus ones invoking only `bst show`/
`artifact delete` (no CAS write, so never `Cache too full` -
`test_bst_show_to_graph.py`, `test_element_kind_heuristics.py`) and
ones mocking `subprocess.Popen`/`.run` entirely (`test_interrupted_
capture.py`, `test_stale_casd.py`). Left: the row's 7 plus
`test_cache_logs.py`, `test_process_spine.py`, `test_snapshot.py`,
`test_spine_ground_truth.py`, `test_stream_merge.py` - all reaching
`tests/unit/_bst_env.py`'s `isolated_bst_env`, and 2 more that do not
(`test_native_build_tracer.py`, `test_dual_plane_capture.py` - real
`bst build` against the ambient, un-isolated `$HOME`, not a per-test
`tmp_path`; the shared fixture's `quota: 3G` there would shrink a
persistent cache other runs reuse, a different and larger change - not
fixed here, flagged for filing separately).

A second gap, found only by driving the margin negative and rerunning
the row's own six: `isolated_bst_env` alone was not enough.
`extract_run`'s and `run_traced_build`'s internal `bst show`/build are
*separate* subprocesses inheriting the pytest worker's own environment,
not the `env=` dict handed to an earlier, different `subprocess.run` -
so five files (`test_blast_ranking_discriminates.py`, both
`test_bst_extract_run*.py`, `test_shared_source_blast.py`) still failed
`Cache too full` after the first pass.

**The close measured.** `_bst_env.py`: `isolated_bst_env` now defaults
`XDG_CONFIG_HOME` to `UX-755`'s repo-owned, absolute-valued fixture
(overridable via `extra`), reaching every `subprocess.run(env=...)`
call site through one constant; a new `bst_env(home)` context manager
applies the same default to `os.environ` itself, for the in-process
call sites above. `test_a_generated_project_builds.py`'s `_isolated()`
now points at the same fixture instead of an empty, never-created
directory. At a driven margin (`free - reserved = -0.80 GB`,
BuildStream's own arithmetic, `fallocate`'d and removed after):

| population | before | after |
|---|---|---|
| the row's 7 + 5 more (12 files, 51 selected clauses) | 12 failed (`Cache too full`) | 51 passed |
| `test_spine_ground_truth.py`'s two `UX-741` clauses | `assert 255 == 0` (refusal, not the wall-clock tolerance - `UX-741` untouched) | both passed, `27.27s` |

At the container's normal margin (`+9.28 GB`) afterward: all of the
above still pass; `make test-touching` (40 files, 31 census + 9 naming
the change): `1397 passed, 3 skipped in 94.92s`.

**Mutation.** Both fixture files' `reserved-disk-space: 500M` changed
to `5%` (the row's own control), margin driven to `-0.67 GB`:

| file | result |
|---|---|
| `test_bst_checkout_cost.py`, `test_a_generated_project_builds.py` (x2), `test_bst_extract_run.py`, `test_spine_ground_truth.py`, `test_stream_merge.py` | `6 failed` - `Cache too full` / `assert 255 == 0` |

Reverted (`git checkout --` on the two unmodified fixture files); same
six green again at the same margin, then at the normal one.

`test_native_build_tracer.py`, `test_dual_plane_capture.py`: named,
not fixed - see the gap above.
