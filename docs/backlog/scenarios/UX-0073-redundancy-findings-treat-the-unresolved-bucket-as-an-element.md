# UX-73: 87% of the redundancy findings' claimed recoverable time comes from an element that does not exist

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-64`, `UX-66` (done — which introduced the unresolved bucket this now mistakes for an element) | **Topic:** capture

## Motivation

`detect_redundant_operations` (`UX-23`) is the one Plane 2 producer that
answers "the same work is being done N times across elements". Its
guard is explicit about not claiming redundancy it cannot attribute:

```python
if r["open"] or r["element"] == "unknown":
    continue
```

That was complete when `unknown` was the only non-element name. `UX-64`
and `UX-66` then introduced a *second* one: processes whose sandbox could
not be matched to exactly one element are placed in an explicitly
unresolved bucket named `buildstream-build`, which by design is not an
element and is reported as such everywhere else in the tool.

`detect_redundant_operations` does not know that. It treats
`buildstream-build` as a distinct element, so "this signature occurs
under 2+ distinct elements" is satisfied by *one* real element plus the
bucket.

Measured on round 9's capture (93 findings above the 0.05s floor):

| | count | claimed recoverable wall-clock |
|---|---|---|
| all findings shown | 93 | 4129s |
| **findings that include `buildstream-build`** | **79** | **3588s (87%)** |
| findings that vanish entirely without it (bucket is 1 of only 2 elements) | 19 | — |
| of the top 10 by claimed impact | 8 | — |

The single largest finding in the whole report is:

```text
88x across 2 elements (buildstream-build, components/python3.bst)
  - up to 1932.9s recoverable wall-clock (worst element: buildstream-build)
```

`lto-wrapper`, "recoverable" against a worst element that is a bucket of
17,754 unattributed processes. The number is meaningless and it is the
headline.

## Two more false-positive classes in the same list

**The `sh -c -e` build wrapper slips past `_is_element_build_driver`.**
`UX-37` correctly excluded each element's own build driver, because
`make -jN` is identical across elements by construction while doing
entirely different work. But BuildStream's own per-element command
wrapper is not caught:

```text
21x  worst=664.6s  'sh -c -e if [ -n "bst_build_dir" ]; then'
 2x  worst=512.6s  'sh -c -e (set -ex; sh -c -e \'cmake -B_builddir -H"." -G"Ninja" ...'
```

The first is BuildStream's shared `build-commands` preamble — identical
in every element by construction, exactly the case `UX-37` ruled on. The
second slips through for a narrower reason worth stating: the token is
`'cmake` (with the opening shell quote attached), so `os.path.basename`
yields `'cmake` and the `_BUILD_DRIVER_BINARIES` membership test misses
it. 11 of the 93 shown findings start with `sh -c -e`, together claiming
2071s.

**The claimed savings sum to more than the build.** Adding the 93
findings' "up to X recoverable" gives 4129s against a 3614.2s build.
Each figure is individually defensible as an upper bound on one
signature, but a list a reader scans top-down invites the sum, and the
sum is impossible. Nothing in the block says the figures are neither
additive nor achievable together.

## Why this matters more than it did

These findings were never rendered by `bga analyze` or `bga correlate`,
so nobody has been misled by them yet — they appear only in the tracer's
own text report, which the CI capture does not even save. `UX-72`
proposes wiring `redundant_operations` into the join. **That must not
happen until this is fixed**, or the join's freshly-widened evidence base
inherits a list whose top eight entries out of ten are artifacts of an
attribution gap.

## Required Fix

1. **Exclude the unresolved bucket by identity, not by name.** The
   producer already knows which bucket is unresolved
   (`element_attribution.unresolved_bucket`); redundancy detection should
   read that rather than hard-code a string, so a future rename cannot
   silently re-open this.
2. **Require 2+ *resolved* elements.** A signature seen under one real
   element and the bucket is not evidence of cross-element redundancy; it
   is one element plus unknown.
3. **Extend the build-driver exclusion** to BuildStream's own
   `sh -c -e`/`bst_build_dir` command wrapper, and strip shell quoting
   before the basename test so `'cmake` matches `cmake`.
4. **State that the figures do not add.** One line under the block, the
   same way `peak_memory`'s note already says its per-element maxima
   "must not be summed".
5. **Report the excluded population.** How many findings were dropped for
   involving only the unresolved bucket is itself a coverage signal — it
   goes up when attribution gets worse.

## Out of Scope

- Improving attribution so the bucket shrinks. That is `UX-56`'s residual
  (16 ambiguous sandboxes, 13.9% of processes) and is a different task;
  this one is about not building claims on top of a bucket that is
  honestly labelled unresolved.
- The `_REDUNDANCY_MIN_SECONDS` floor (0.05s), which is doing its job:
  it already removes 506 of the 599 findings.

## Acceptance Test

1. On round 9's capture, no finding lists `buildstream-build` among its
   elements, and the `lto-wrapper` finding is gone.
2. The `sh -c -e if [ -n "bst_build_dir" ]` and quoted-`cmake` findings
   are gone.
3. The block states that the per-finding figures are upper bounds and do
   not add, and reports how many findings were excluded as
   unresolved-only.
4. A synthetic case with the same signature under two genuinely resolved
   elements still produces a finding — this must not become "report
   nothing".

## Fix Implemented — with two measured corrections to this task as filed

Round 9's capture, the same 0.05s reporting floor, before and after:

| | before | after |
|---|---|---|
| findings | 599 | **329** |
| shown above the floor | 93 | **42** |
| claimed recoverable wall-clock | 4129s | **91s** |
| findings involving the unresolved bucket | 79 | **0** |

The remaining list is the class `UX-23` was built to find, and nothing
else:

```text
  30x worst= 20.4s els=2  /usr/bin/m4 -P
 594x worst= 16.3s els=3  .../x86_64-unknown-linux-gnu-gcc ... (autoconf probe)
 242x worst= 10.3s els=2  x86_64-unknown-linux-gnu-gcc -o conftest ...
 551x worst=  9.7s els=2  /usr/libexec/gcc/.../cc1 -quiet ...
   8x worst=  2.2s els=8  rm -rf -- /buildstream-build
   2x worst=  1.6s els=2  /usr/bin/perl /usr/bin/automake --add-missing ...
```

### Correction 1: identity, not the bucket's name

This task proposed reading `element_attribution.unresolved_bucket` so a
rename could not re-open the hole. That is weaker than it looks — the
field names only the *largest* unrecognized bucket, and a capture can
carry several. The fix instead shares the predicate
`assess_element_attribution` already judges by: an element name ends in
`.bst`. Anything else is not a second element, whichever bucket it is.

### Correction 2: the `sh -c -e` wrapper needed no string heuristic

This task proposed extending the build-driver exclusion to BuildStream's
own command wrapper and stripping shell quoting so `'cmake` would match
`cmake`. Measurement found a structural identification instead, so no
string rule was added at all:

- bwrap gives each sandbox a PID namespace, so the element's command
  block is **pid 2 with ppid 1**. On the real capture, **exactly 25
  records match — one per each of the 25 sandboxes**, all pid 2.
- The block is *two* processes: BuildStream runs
  `sh -c -e (set -ex; sh -c -e '<script>')`, so the script runs in an
  inner shell. All **21** occurrences of the largest surviving false
  positive — `sh -c -e if [ -n "bst_build_dir" ]; then`, 664.6s across 5
  elements — carry `ppid == 2`, with the same script one nesting level
  out as their invocation's root.

So a direct child of the root that is *itself a shell* is part of the
command block; a direct child that is a compiler is the element's real
work and stays. That distinction is tested both ways. A capture taken
without a PID namespace matches neither clause, so the rule never fires
rather than mis-firing.

The quoted-`cmake` case (`sh -c -e (set -ex; sh -c -e 'cmake -B_builddir
...`, 512.6s across 2 elements) is a command block and is excluded by the
structural rule, so `UX-37`'s deliberate decision to keep `cmake`
*configure* as a finding is left exactly as it was.

### Coverage is published, not implied

`redundant_operations_coverage` is an additive sibling key — the same
shape `UX-04`'s `attribution_hints` uses, so an existing consumer of
`redundant_operations` sees no change. On round 9's capture it reports
**256 candidates excluded as unresolved-only** and **169 processes
excluded as command blocks**, and carries the note that the per-finding
figures are maxima over concurrent elements and must not be summed. The
text report prints both, because a list that merely got shorter reads as
a cleaner build.

Tests: 6 new in `tests/unit/test_redundancy_scoring.py`. Suite: 1075 →
1081.

## Verification Log

Filed 2026-08-18 (round 10 preparation). All counts are from
`redundant_operations` in `native-report.json` of the capture published
as `5eda28a` (run `32064333551`, `bga_ref` `1143f2b`), filtered with the
tool's own `_REDUNDANCY_MIN_SECONDS`. The 3614.2s build duration is that
capture's `analyze.txt`.
