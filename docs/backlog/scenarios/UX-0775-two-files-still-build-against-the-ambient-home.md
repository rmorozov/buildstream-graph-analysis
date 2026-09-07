# UX-775: two files still build against the ambient HOME

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-760 (the twelve it did fix) | **Serves:** the session whose `make test` reds on two files nobody touched, at a margin the other twelve survive | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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
- Changing `cache.reserved-disk-space`'s default, which is
  BuildStream's, not this repository's.

## Acceptance Test

Drive the margin negative with `fallocate`, run all fourteen
`bst`-gated CAS-writing files, and get no `Cache too full` — or, under
option 2, a skip naming the margin. Then remove the fix and watch the
two redden.

## Outcome

_Not started._
