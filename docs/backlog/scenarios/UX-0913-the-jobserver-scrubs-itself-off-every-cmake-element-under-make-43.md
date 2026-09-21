# UX-913: the jobserver scrubs itself off every cmake element under a make-4.3 sandbox, so auto and off are the same build

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-874, UX-878, UX-879, UX-882 | **Blocks:** UX-910 | **Found by:** round 132 — `11-serial-giant` reads `peak 2` under `auto` on six consecutive CI pairs, and the capture's own warning says why | **Serves:** every example and every real project whose sandbox ships GNU Make 4.3 | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Decomposition

surfaces: `tools/native_trace/bwrap_shim.py` (`_FD_DIRECT_POLICIES`,
the scrub not applied to it) · `tools/bst_native_build_tracer.py`
(`lto_preflight_warnings`, two-sided) · `docs/guides/cli.md` (§3.10,
three lines) · `examples/11-serial-giant/elements/*.bst` (the four
annotations, dropped as the acceptance test). No published key moves,
so no version bump.

guards: `test_the_lto_link_survives_the_jobserver.py` (policy: cmake
kept / cargo still scrubbed; make version: absent, 4.3, 4.4) ·
`test_a_compiler_lto_shim_fills_the_box.py` (override: matched,
unmatched-cmake, unmatched-cargo) ·
`test_a_preflight_warns_on_lto_meeting_old_make.py` (the line's two
sides).

gap: **no LTO cmake fixture exists**, so "the shims defuse a real
`gcc -flto` under cmake" is guarded at the argv level and never end to
end. That is the same gap `UX-880` shipped with, not one this row
opens; the live ICE reproduction it would need is `UX-884`'s.

track: serial after nothing; `UX-915` and `UX-916` touch the same
examples and must not run beside it.

gate: one `make test` here, then CI's `bst-examples` step 21, which is
the only place the acceptance test can actually run.

## The shim route was tried first, and CI measured it wrong

Design (B) of this row's two candidates — keep the auth **and** mount
`UX-880`'s `flto/` GCC-driver shims, so `lto-wrapper` never reads the
raw fd — shipped at `f8657034` and failed `bst-examples` on run
35610762079, at the step before this row's own:

```text
OK: 11 element key(s) equal with and without the mode's environment
##[error]Process completed with exit code 255.
```

The step is `The cache key is equal with and without the jobserver
(UX-844)`, `.github/workflows/ci.yml:1409`, and the 255 is the
`--jobserver 4` build of `examples/06-macro-micro-optimization` — nine
`kind: cmake` elements, every one of which design (B) newly put the
`flto/` subdir on `PATH` for.

`_wrapper_mount`'s own docstring had already recorded the failure mode
(`bwrap_shim.py:571`): the shims shadow `cc`, `gcc`, `g++` and `c++`,
and open on

```sh
bga_self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
```

under `set -eu`. `examples/stage_cpp_toolchain.sh:36` stages exactly
`gcc g++ cc c++ cmake make ld ld.bfd as ar ranlib nm strip env sh uname
sort cat` — no `dirname`, `basename`, `head`, `grep`, `date` or
`readlink`. All four shadowed names are staged; none of the tools the
shim needs is. So every cmake element compiled through a script it
could not source.

**So the shims stay behind the `flto` override and this row ships
design (A):** `cmake_meson` keeps its auth because `make` is a direct
child, and nothing is mounted with it. `11-serial-giant` uses no `-flto`
at all (`grep -rn flto examples/11-serial-giant` finds only the width
check's own comment), so the acceptance test never needed them.

The half this leaves open is real and filed separately: a cmake element
that *does* drive LTO now keeps a raw fd `lto-wrapper` cannot use, and
the shims that would defuse it are unmountable in a staged-toolchain
sandbox until `wrappers/_common.sh` stops needing coreutils.

## Motivation

`UX-910` asks why `11-serial-giant` reads `peak 2` against a ceiling of
4 under `--jobserver auto`. The capture answers it in its own output,
four times per run, and no round had read it:

```text
Warning: giant.bst scrubbed to recipe -jN (sandbox make <4.4); move it to
  make >=4.4 for fifo pool-fill, or force fd/flto (UX-879/880)
Warning: leaf-a.bst scrubbed to recipe -jN (sandbox make <4.4); ...
Warning: leaf-b.bst scrubbed to recipe -jN (sandbox make <4.4); ...
Warning: leaf-c.bst scrubbed to recipe -jN (sandbox make <4.4); ...
```

`12-junctioned`'s `core.bst` carries the same line in the same run
(`35545829617`, `artifacts/11-serial-giant/run-auto`).

The chain, run against `giant.bst`'s real parameters rather than
described:

```text
jobserver_decision(2, 2)                        -> joined
style_for_make_version("GNU Make 4.3")          -> fd
kind_job_env("cmake", auth, ninja unavailable)  -> [("JOBS",""),("MAKEFLAGS",auth)], "cmake_meson"
"cmake_meson" in _COMPILER_SAFE_POLICIES        -> True
compiler_safe_auth(fd-style, make_below_44=True)-> None
```

A `None` from `compiler_safe_auth` drops `MAKEFLAGS` **and** `JOBS`, so
BuildStream's own `-j2` stands: jobserver-off behaviour, reached from
`--jobserver auto`. No ninja is staged in that sysroot (`BINARIES` in
`examples/stage_cpp_toolchain.sh` names gcc, g++, cmake, make,
binutils, and no ninja), so the cmake row takes its make path, and the
sandbox's `make` is the host's — Ubuntu 24.04 ships GNU Make 4.3.

**The consequence is that `auto` and `off` are the same build.** That
is one fact explaining every reading `UX-910` collected: `peak 2` on
all six pairs, and walls that differ only by run-to-run noise. They
were never two configurations. The `11-serial-giant` step asserts a
strict inequality between a thing and itself, which is why which side
of zero it lands on is a coin flip.

**Why the scrub exists**, and why it over-reaches here. `UX-878` stops
a raw fd auth reaching an *unwrapped* native jobserver client — gcc's
`lto-wrapper`, cargo — which is a deep grandchild across `bwrap` and
cannot open the fd (measured: a GCC-13 ICE). `UX-874` had already
downgraded `fifo:` to `fd` for a sub-4.4 make, which rejects a `fifo:`
auth outright. Together, on a make-4.3 sandbox, every `cmake_meson`
element loses its jobserver. But the consumer under `cmake_meson` with
a Unix Makefiles generator is `make` itself, a direct child that can
use an inherited fd, and this example requests no LTO at all.

## Required Fix

Two questions, and the first is cheap enough to answer before the
second is designed.

**Does forcing `fd` restore the width?** `UX-879`/`UX-882` already
provide the lever: `_forced_auth("fd", …)` keeps `auth_value` raw,
"exactly as `_jobserver_injection` computed it pre-UX-878 (no fifo
rewrite, no scrub)". A `public: bga: jobserver-auth: fd` annotation on
the four elements of `11-serial-giant` turns the mode back on for them
without touching any shared code. One CI run then says whether `peak`
rises above 2.

It may not. If the fd does not survive `bwrap` into the sandbox, make
4.3 will report the jobserver unavailable and fall back to `-j1`, and
the element gets *slower*, at `peak 1`. That outcome is as informative
as the other and must be recorded either way, not retried until it
reads well.

**Should `cmake_meson` be in `_COMPILER_SAFE_POLICIES` at all?** The
policy's own consumer is `make`. Narrowing the scrub to the policies
whose consumer really is an unwrapped grandchild (`cargo`, and
`cmake_meson` only when LTO is actually requested) would restore the
mode for every make-4.3 cmake project rather than for one annotated
example. That is the real fix and it needs its own measurement: what
`UX-878`'s own guard reddens on, and whether a non-LTO cmake build
with a raw fd reproduces the GCC-13 ICE that motivated it.

## Out of Scope

Changing `UX-874`'s downgrade, or the `fifo:`/`fd` resolution itself.
Staging a `make >= 4.4` into the examples' sysroot — a second remedy
the warning names, and a bigger change than this row (Ubuntu 24.04 has
no 4.4 package, so it means building one). `12-junctioned`'s
`core.bst`, which carries the same warning and is its own fixture.
`UX-910`'s gate, which stays wrong whatever this row finds: a strict
unbanded inequality is the wrong instrument even once the two arms
genuinely differ.

## Acceptance Test

**Measured, run `35564652560` on `a14ba0c1`.** The annotation landed
and the width did not move — a fourth outcome the three below did not
enumerate:

```text
scrub warnings: mod-c.bst, mod-d.bst (example 10), core.bst (example 12)
                giant/leaf-a/leaf-b/leaf-c: absent

  element                  peak  req  achieved     span work
  giant.bst                   2    2      100%   45.36s  530
  leaf-a/b/c                  2    2      100%    ~1.4s   34
```

The warning is element-scoped and still fires for the three
unannotated elements, so its absence for these four is evidence the
annotation took effect rather than evidence the warning stopped. The
step read `off=218.52s auto=215.46s`, IMPROVED -1.4% — inside the
+-2% spread `UX-910` measured over six pairs, and with `peak`
unchanged, so the green gate is the coin flip landing heads and is
**not** evidence for this row.

**RETRACTED by two later readings.** The paragraph that stood here
said the scrub was necessary but not sufficient and that a second,
unidentified gate sat between "the pool is reachable" and "`make`
draws from it". Both arms of two later CI runs say otherwise:

```text
job 106314552412, head 0567ee72:
  giant.bst   off peak 2 / req 2, work 530     auto peak 4, work 530
run 35592532623, job 106317022896, head ef9d3629 (UX-910's own check):
  off=217.80s auto=215.04s
  giant.bst: off peak 2, auto peak 4, resolved width 2
  giant.bst: auto exceeded its resolved width (UX-913)
  compare: giant.bst -3.05s (212.25s -> 209.20s), total -1.3%
```

So the annotation is sufficient and `make` does draw from the pool.
What the retracted reading rested on was **one table of unrecorded
arm**: run `35564652560` printed a table per capture, and nothing in
the record says the quoted one came from `run-auto`. The instrument
did not move under it - `git log a14ba0c1..46e16112 -- tools/` carries
only `53bc5992`, whose tracer hunks are the token ledger and
`requested_jobs`, not `_concurrency_profile`, and `work 530` is
identical across all three readings. The lesson is the one `UX-910`
shipped: read **both** arms in the same run and print which is which.

`req 2` is still `UX-894`'s static resolved width and still cannot
distinguish "make asked for two" from "make was granted two" - that is
why the reading above is `peak` against `req`, not `req` alone.

What remains of this row is the default: `cmake_meson` stays in
`_COMPILER_SAFE_POLICIES`, so every make-4.3 cmake element still
scrubs unless annotated one by one. `12-junctioned`'s `core.bst` does,
in the same run (`core.bst 2 4 ? 0.36s 18`), and `10-jobserver`'s
`mod-c`/`mod-d` with it.

The three outcomes this section originally listed. The first is the
one that happened:

- **`peak > 2` means the mode is restored** - measured, `peak 4`,
  twice.
- `peak 1` would have meant the fd does not cross the sandbox
  boundary. It does.
- `peak 2` with the warning still printed would have meant the
  annotation did not match the element. It matched.

What the reading now needs is the run's own `plane2.json`, which
carries the per-sandbox decision and which `examples/10-jobserver`'s
`check_jobserver_decision.py` already reads. It is uploaded as a CI
artifact and unreachable from a dev container behind the egress proxy
(403), which is itself the finding below.

**The asymmetry to fix first.** bga warns loudly when it scrubs the
jobserver and prints nothing when it keeps it, so a reader can see the
mode give up but never see it engage. That is why six runs carried
`peak 2` before anyone read the warning, and it costs every user the
same way, not only this fixture. The decision belongs in the report.

## Outcome

**The gap.** The default scrubbed every `cmake_meson` element under a
sub-4.4 sandbox make, so `--jobserver auto` and `off` built identically
unless each element carried `public: bga: jobserver-auth: fd` by hand.
`11-serial-giant` wore four such annotations; `12-junctioned`'s
`core.bst` did not, and read `peak 2` against a ceiling of 4 in the same
run.

**The close.** The four annotations are gone (`76c3fe2f`), and
`_FD_DIRECT_POLICIES = frozenset({"cmake_meson"})` exempts the policy
from `compiler_safe_auth`'s scrub without mounting anything. Measured by
CI's own `bst-examples` step 21 on `851f8b55`, run `35625287116`, job
`106426877997`, both arms in one run:

```text
Note: giant.bst keeps its jobserver auth (sandbox make <4.4,
cmake_meson); make reads the fd directly. An element that also drives
LTO needs the flto override (UX-913)

  element                  peak  req  achieved     span work
  giant.bst                   2    2      100%   37.17s  530   <- off
  giant.bst                   4    ?      100%   28.26s  530   <- auto

  off   70.83s CPU over 38.13s wall = 1.86 cores busy
  auto 107.07s CPU over 29.04s wall = 3.69 cores busy

off=185.70s auto=178.12s
giant.bst: off peak 2, auto peak 4, resolved width 2
giant.bst: auto exceeded its resolved width of 2 (UX-913)
```

`work 530` is identical across the arms, so `peak 4` is four concurrent
compilers on the same work, not more work. The wall moved -4.1% on
**one** pair; `UX-910` measured +-2% over six, so that number sizes
nothing and is recorded, not claimed. The structural reading is the
peak and the 1.86 -> 3.69 cores.

The same job's step 16 (`06-macro-micro-optimization`) and step 17 (the
`UX-844` cache-key equality, `ci.yml:1409`) both passed - the two that
exited 255 under design (B), on run `35610762079`.

**Mutations.** 34 guards over the three files, each mutation applied to
`bwrap_shim.py` alone:

| mutation | reddens |
|---|---|
| `_FD_DIRECT_POLICIES = frozenset()` (the old default) | 6: `..._keeps_the_auth_without_the_flto_shims`, `..._and_no_wrapper_dir_still_keeps_the_auth`, `..._proxy_auth`, `test_unmatched_cmake_element_keeps_the_auth_and_not_the_shims`, and the preflight's two kept-auth sides |
| `frozenset({"cmake_meson", "cargo"})` (too wide) | 4: `test_cargo_fd_with_make_4_3_is_also_scrubbed`, `test_unmatched_element_on_the_same_4_3_make_is_still_scrubbed`, and the preflight's two scrub sides |
| `"flto_active": True` (design (B), the mount) | 3: `..._keeps_the_auth_without_the_flto_shims`, `test_unmatched_cmake_element_keeps_the_auth_and_not_the_shims`, `..._wrapper_mounted_for_other_reasons_gets_no_flag` |

Both directions redden, and the third reddens the exact change CI
measured at exit 255 - so the guard would have caught design (B)
locally had it existed first.

**Deviation.** The row set out to ship design (B) and shipped (A); the
paragraph above the Motivation carries why, with the measurement. Two
things this row does not close:

- A `cmake_meson` element that *does* drive `-flto` now keeps a raw fd
  `lto-wrapper` cannot use, and must take the `flto` override by hand.
  `UX-918` made `wrappers/_common.sh` shell-only so that override is
  deliverable on a staged sandbox, but mounting the shims for
  `cmake_meson` by default is not re-attempted here and has no filing.
- The Decomposition's declared gap stands: no LTO cmake fixture exists,
  so "the shims defuse a real `gcc -flto` under cmake" is still guarded
  at argv level only. That is `UX-880`'s gap, not one this row opened.
