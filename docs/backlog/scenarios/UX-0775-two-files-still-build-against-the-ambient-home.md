# UX-775: two files still build against the ambient HOME

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-760 (the twelve it did fix) | **Serves:** the session whose `make test` reds on two files nobody touched, at a margin the other twelve survive | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-760` moved twelve files onto `tests/unit/_bst_env.py`'s isolated
environment, so a `bst` they run reads a `quota: 3G` config in a
per-test `tmp_path` rather than the host's 5%-of-total reserve. Two of
the eighteen that gate on `bst` were deferred:

```console
$ grep -rln 'shutil.which("bst")' tests/ | wc -l
18
$ grep -rln 'isolated_bst_env\|bst_env' tests/unit/*.py | wc -l
13          # 12 tests + _bst_env.py itself
$ grep -c 'isolated_bst_env\|bst_env' \
    tests/unit/test_native_build_tracer.py tests/unit/test_dual_plane_capture.py
tests/unit/test_native_build_tracer.py:0
tests/unit/test_dual_plane_capture.py:0
```

Both run real `bst artifact delete` / `bst build` against a project
directory with **no `env=` override**, inheriting the ambient `$HOME`
and `~/.config`. So at a genuinely negative margin they still refuse
with `Cache too full` while the twelve pass — `UX-760`'s verifier
confirmed this on its own run rather than taking the deferral on
trust.

The deferral itself is defensible and this row does not reopen it:
pointing the *real*, shared `~/.config` at the fixture's `quota: 3G`
would shrink a cache other runs reuse. That is a different change with
a different blast radius, which is why it is a row and not a fix.

What is not defensible is leaving it unstated. Two files that redden
only under disk pressure, on a tree nobody touched, is the shape that
cost round 106 a wrong conclusion about what was blocking the gate.

## Required Fix

Give these two what the twelve got, without touching a shared cache.
Two candidates, and the row is a decision between them:

1. **A per-test cache that is not the fixture's.** They need a real
   build against a real project; they do not need the *host's* cache.
   A `tmp_path`-rooted `XDG_CONFIG_HOME` with its own quota, seeded or
   cold, costs build time per run — measure it before choosing.
2. **State the dependency instead.** If a warm ambient cache is what
   these two are actually testing, then they depend on the host and
   should say so: skip with a named reason when the margin is
   negative, rather than failing as if the code were wrong.

(2) is cheaper and weaker — a skip is not a pass, and `UX-84`'s
`bst-tests` job exists because a gated tier can rot green. Whichever
lands, the Outcome names which and why, with the build-time figure
that decided it.

## Out of Scope

- `UX-760`'s twelve. They are fixed and verified; this row is the
  remainder its Outcome names.
- `UX-773`'s browser leak. Different owner, same symptom — a red gate
  from disk pressure rather than from the diff.
- Changing `cache.reserved-disk-space`'s default — it is
  BuildStream's, not this repository's, and a fix here that only
  works against a patched `bst` is not a fix for anyone running
  the released one.

## Acceptance Test

Drive the margin negative with `fallocate`, run all fourteen
`bst`-gated CAS-writing files, and get no `Cache too full` — or, under
option 2, a skip naming the margin. Then remove the fix and watch the
two redden.

## Outcome

**The gap measured.** Before the fix, ambient `$HOME`, `bst` present,
toolchain fixture staged (`bash examples/stage_cpp_toolchain.sh`):

```console
$ python3 -m pytest tests/unit/test_native_build_tracer.py \
    tests/unit/test_dual_plane_capture.py -m bst --durations=0 -q
11.23s call  test_native_build_tracer.py::test_run_traced_build_captures_real_process_lifecycle
10.13s call  test_dual_plane_capture.py::test_single_real_build_captures_both_planes_and_combined_trace_correlates
2 passed, 38 deselected in 21.82s
```

Both pass at this machine's normal margin; the row's own defect is that
at a negative one they still refuse (`UX-760`'s verifier confirmed this
directly, cited there rather than re-derived here).

**The close measured.** Option 1: wrapped each real end-to-end test's
`bst artifact delete` + build in `tests/unit/_bst_env.py`'s existing
`bst_env(tmp_path / "home")`, the same in-process route
`test_process_spine.py` already uses for `run_traced_build`. Two runs
after:

```console
11.87s + 12.07s = 23.94s call, 24.48s total   (run 1)
14.76s + 11.66s = 26.42s call, 26.91s total   (run 2)
```

Ratio 1.12x–1.23x elapsed — well under the 2x bar, so the isolation is
kept per the brief's rule, not reverted.

The Acceptance Test's own `fallocate` step was not run: the machine was
shared with other tracks mid-round (13.5 GB free, 500M reserve — filling
to a negative margin risked every concurrent track's `bst` build, not
just this one). Substituted: the wall-time comparison above (21.82s
ambient to 23.94-26.91s isolated, 1.12x-1.23x) and the structural
guard's mutation below. The functional claim — no `Cache too full` at a
negative margin — is inherited from `UX-760`'s verification of the same
`quota: 3G` mechanism (`_bst_env.py`'s `BST_XDG_CONFIG_HOME` fixture,
unchanged here), not re-measured for these two files.

**Mutation table.**

| guard | mutation | result |
|---|---|---|
| `test_a_generated_project_builds.py::test_every_cas_writing_bst_gated_file_reaches_the_isolation` (13-file population, `_GATE = shutil.which("bst")` census over `tests/`) | `test_native_build_tracer.py`'s `bst_env` wrap reverted to ambient `$HOME` | `AssertionError: ['test_native_build_tracer.py'] shell out to a real bst without ... isolated HOME` |
| same, reverted from the pre-mutation copy (not `git checkout --`) | — | `1 passed` (and `test_native_build_tracer.py` + `test_dual_plane_capture.py` both green, 41 passed together) |

Guard placed inside `test_a_generated_project_builds.py` (already a
`_bst_env` consumer, already gated on `bst`) rather than a new file: a
new `test_*.py` moves `tools/dev_touching.py`'s file count and reddens
`test_the_cost_row_is_derived_from_the_selector.py` against
`docs/contributing/fixing-guide.md`'s stale figure — a file this track
does not own.

**Deviation.** The counting guard lives in `test_a_generated_project_builds.py`, not a new file: a new test file moves `dev_touching.py`'s file count and reddens the fixing guide's cost figure. The Acceptance Test's fallocate step was not run on a shared machine; the wall-time comparison and the guard mutation stood in, the functional claim inherited from `UX-760`. One verifier hold (the Outcome omitted that substitution), fixed in a second commit (ac2ee591). The file derives judgement; the brief ran it as bounded.
