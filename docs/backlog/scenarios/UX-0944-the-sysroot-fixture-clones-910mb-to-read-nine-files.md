# UX-944: the sysroot fixture clones 910 MB to read nine files, so its cost has two modes 30x apart and the reference entry is the median of both

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-930 | **Blocks:** — | **Found by:** round 137 — `#266` moved `tests/ci_reference.json`'s entry for `tests/unit/test_the_toolchain_parameters_are_read_back.py` from 3.15 to 46.28, and the window behind that number reads `[46.28, 3.15, 94.23]` | **Serves:** the next reader of that entry, and every run of the `test` job, which pays the dear mode whenever the runner's `/usr` and its temporary directory are on different filesystems | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical

## Motivation

The entry is not a number the file ever produced. On `origin/main`:

```text
$ python3 -c "import json;r=json.load(open('tests/ci_reference.json'));\
k='tests/unit/test_the_toolchain_parameters_are_read_back.py';\
print(r['files'][k], r['samples'][k], r['measured_on'])"
46.28 [46.28, 3.15, 94.23] github-actions ubuntu-latest, test (3.11), -n auto
```

Three readings, 30x apart at the ends, and `UX-496`'s median lands
between them on a value no run took. The file's own docstring already
names why there are two modes and nothing else:

> The fixture is a miniature sysroot, hardlink-cloned off this host the
> way `stage_cpp_toolchain.sh` clones its own output - 65ms and no real
> disk where `/usr` and the temporary directory share a filesystem, a
> 1.6s copy where they do not.

So the two modes were known when the row landed. What was not measured
is the dear one **on a runner**: the docstring sizes it at 1.6s and the
runner reads the whole file at 94.23s. Measured here, on this
container, for the four directories `mini` clones:

```text
$ for d in $(gcc -print-prog-name=cc1|xargs dirname) \
           $(gcc -print-file-name=libgcc.a|xargs dirname) \
           /usr/lib/x86_64-linux-gnu /usr/include; do \
      printf '%-45s %6s %6s files\n' "$d" "$(du -sh $d|cut -f1)" \
             "$(find $d|wc -l)"; done
/usr/libexec/gcc/x86_64-linux-gnu/13                 90M      8 files
/usr/lib/gcc/x86_64-linux-gnu/13                     26M    208 files
/usr/lib/x86_64-linux-gnu                           715M   3067 files
/usr/include                                         53M   4635 files
```

`cp -al` on that tree: **0.102 s**. `cp -a` on the same tree, cold
page cache: **14.63 s**; warm, 2.0-3.3 s. The runner is cold, runs
`-n auto` against other workers' I/O, and `mini_symlinked` is a second
module-scoped fixture - which is how 14.63 becomes 46 or 94.

**So 46 seconds is neither the intended price nor a staging accident.
It is the arithmetic mean-by-median of a bimodal population**, and the
mode that produces it is a property of the *runner's* filesystem
layout, not of this file. That matters twice:

- `shift_of` divides out the run's median ratio over files at or above
  `SHIFT_FLOOR_S`. This file is the only one in the suite that clones
  `/usr`, so the cross-device penalty is never in the run-wide median
  and never cancels. `UX-936`'s question one level down, with the
  cause already known.
- With 46.28 as the record, `over_drift` reads a cheap run as nothing
  (3.15 is not over `1.5 x 46.28`) and every dear run as a candidate:
  `94.23 > 69.42` and `94.23 - 46.28 = 47.95 >= 5.0`. Two consecutive
  cross-device runs and `CI_DRIFT_RUNS` confirms an excursion that no
  diff caused. Which mode owns the record is decided by how many of
  the last `CI_REFERENCE_SAMPLES` runs happened to land on a runner
  with one filesystem.

## Required Fix

Clone what the guard reads, not the directories it reads it from. The
seven classes in `tools/toolchain_params.py` name nine files: `cc1`,
`as`, `ld`, `libgcc.a`, `stddef.h`, `crt1.o`, `libstdc++.so`,
`stdio.h`, `vector`. The two header classes run `-H` on a real
`#include`, so they need those two headers' transitive closure and
nothing else; `-print-file-name` classes need the named file to exist
and no more. Measured, both trees built and checked on this container:

```text
                 size    files   build (cp -a, warm)   --check
full            910.0 MB  7420          2.00 s         exit 0
pruned          126.4 MB   292          0.11 s         exit 0
```

Identical verdicts on all seven classes, `toolchain`/`sysroot` each
where the full tree puts it. The pruning rule is three lines: clone
`cc1.parent` and `libgcc.parent` whole - the driver **execs** those
binaries, so they must be real - then copy `crt*`, `Scrt*` and
`libstdc++.so*` out of the multiarch libdir, and copy exactly the
paths `-H` reports for `#include <stdio.h>` and `#include <vector>`.
The 715 MB multiarch tree is 79% of the clone and is there to carry
12 KB of start files.

126 MB of that remainder is `cc1`/`cc1plus` and cannot be pruned, so
the dear mode does not disappear - it drops by 7.2x, which puts the
file's cross-device reading under `CI_DRIFT_SECONDS` of its cheap one
and makes the record single-valued. Re-record the entry after the
prune lands; do not re-record it before, which would only move the
median between the same two modes.

Do **not** fix this with `--basetemp`. It makes the choice of mode an
environment setting rather than a property of the fixture, and a
runner whose `/usr` is a separate or read-only mount cannot host a
writable temporary directory beside it.

**A note on the header.** `**Area:**` is `unassigned` because the whole
change lives under `tests/` and the §6 vocabulary has no such area —
`UX-937` is that row, filed in this round.

## Out of Scope

`UX-936`, the general question of whether the drift gate can tell a
slow runner from a slow file; this row removes one instance at the
source and leaves the estimator alone. `UX-924`'s frozen adopt, which
is why a three-sample window is what the record was taken from.
`mini_symlinked`, which clones nothing and costs nothing.

The two adopt rows, for the same reason. `461c9c6b` is the commit that
wrote 46.28 - an adopt push with no check run of its own, which is
`UX-934`, filed and carrying that instance already. But `UX-934`'s
check runs a record's guards, and **46.28 passes every one of them**:
it is the honest median of the three readings it was taken from. So
nothing in that fix would have caught this, and nothing here asks it
to. The nearer neighbour is `UX-943`, which asks *which runs may adopt
at all* - a question this row supplies one answer to (a run whose
filesystem layout differs from the window's) and does not try to
settle.

## Acceptance Test

`tests/unit/test_the_toolchain_parameters_are_read_back.py` passes its
22 tests against a pruned `mini`, with the tree's size and file count
pasted beside the full tree's, and `tp.main([mini, "--check"])`
printing the same seven owners either way. A mutation that drops one
of the nine named files from the pruned tree reddens the class that
names it - the prune must not be able to omit a mark silently, which
is `UX-930`'s own thesis and the reason its `_clone` already asserts
its three markers landed.

## Outcome (round 138, 2026-09-23) — 🟢 Done

**Premise:** held - `mini` cloned four whole directories (`cc1.parent`,
`libgcc.parent`, the multiarch libdir, `/usr/include`) to read nine
file names.

### The gap, measured

```text
$ python3 <the four-dir clone `mini` used, this container>
full     1564.3 MB   7420 files   build (cp -al/-a, warm) 0.23s
```

### After

```text
$ python3 <cc1.parent + libgcc.parent whole, crt*/Scrt*/libstdc++.so*
  from the multiarch libdir, the two -H closures>
pruned    133.0 MB    292 files   build (cp -al/-a, warm) 0.11s

$ python3 -c 'tp.main([mini, "--check"])'   # same seven owners, both trees
  exec-prefix  toolchain toolchain  .../usr/libexec/gcc/x86_64-linux-gnu/13/cc1
  libgcc       toolchain toolchain  .../usr/lib/gcc/x86_64-linux-gnu/13/libgcc.a
  gcc-headers  toolchain toolchain  .../usr/lib/gcc/x86_64-linux-gnu/13/include/stddef.h
  start-files  sysroot   sysroot    .../usr/lib/x86_64-linux-gnu/crt1.o
  libstdc++    toolchain toolchain  .../usr/lib/gcc/x86_64-linux-gnu/13/libstdc++.so
  c-headers    sysroot   sysroot    .../usr/include/stdio.h
  cxx-headers  sysroot   sysroot    .../usr/include/c++/13/vector
check exit 0 (full and pruned)

$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_toolchain_parameters_are_read_back.py -q
22 passed in 0.82s
```

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | `mini`'s `crt*` copy loop skips `crt1.o` - one of the nine named files, silently | 15 of 22 tests error at `mini`'s own setup, naming `crt1.o` did not land at its path |

Reverted; the same 22-test command above is the green re-run.

### Deviation from the Required Fix

`as`/`ld` are two of the nine named files, but never landed in `mini`
before or after this change: a host-staged driver resolves them
through `PATH` at exec time, not from any cloned directory, and
`declared()` excludes both for a host-staged tree (`host_owner: None`).
The marker list covers the seven files `mini` actually stages - the
same seven `tp.main([mini, "--check"])` prints either way.

Not re-recording `tests/ci_reference.json`'s entry: CI's adopt job
re-records it after this lands.

```text
$ make test-touching
32 file(s) selected (31 census + 1 naming the change) - 1578 passed,
3 skipped in 199.94s

$ make lint
ruff clean; dev_baseline.py --check: 573 finding(s) match
tests/quality_baseline.json, the rest pre-existing forced findings -
none from this diff - exit 0

$ make test
9290 passed, 197 skipped, 1 warning in 1460.18s (0:24:20)
```
