# UX-113: turn the spine on only where the census says the hook is blind

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-105 (the census), UX-106 (the spine), UX-112 (the honest price)

## Motivation

The spine and the census were built in the same round and never
introduced to each other. The census (UX-105) knows **before the build
starts**, per element, whether the staged root contains any static
executable — i.e. whether the hook will be blind there. The spine
(UX-106) is all-or-nothing: on for every element or off for the whole
capture, priced accordingly (UX-108's +2.7% alone, UX-112's much worse
with opens on).

On real projects the blind set is small and stable: a glibc gcc/cmake
toolchain is entirely dynamic (fdsdk's census would flag little beyond
the odd static helper), while the elements that *are* blind — busybox
steps, musl bootstrap stages — are exactly known. Paying the spine's
price on the 95% of elements where it duplicates the hook, to cover
the 5% where it is the only witness, is the wrong trade — and it is
why the spine sits opt-in and therefore mostly off, which quietly
re-opens the blind spot the whole of Direction 4 closed.

## Required Fix

A `--trace-spine=auto` mode (and likely the new default once UX-112's
numbers are in): the shim consults the census result for the element
its bwrap invocation is about to build — the census runs pre-build and
its per-element verdicts can be written where the shim already reads
per-invocation state — and injects the spine **only for elements whose
staged root contains at least one static executable** (plus, cheaply
and always, any element whose kind/config the census could not
assess). Everything else runs hook-only, at hook-only cost. The
report's coverage line says which policy ran per element
(`spine: auto (N of M elements)`), so a capture remains
self-describing, and the UX-96 homogeneity check treats
`auto` as its own value rather than as equal to `true` or `false`.

## Out of Scope

- Changing what the spine records (UX-106's contract stands).
- The combination-cost fix itself (UX-112).

## Acceptance Test

On `examples/06` (all-dynamic): `--trace-spine=auto` produces zero
spine-traced elements, capture cost within noise of hook-only, and
the coverage line says so. On `examples/01` (static busybox): auto
traces all eight work elements, and the per-element records match a
full `--trace-spine` capture of the same build. On a mixed fixture
(one busybox element added to `examples/06`): exactly that element is
spine-traced, and Plane 2 coverage reads 100% of processes across
both policies combined.

---

## Fix Implemented

`--trace-spine=off|on|auto`, defaulting to `off`, with bare
`--trace-spine` still meaning `on` so every existing invocation and test
keeps working.

Under `auto`, `run_traced_build` runs the census before the build and
writes `{element: does the hook need help here}` beside the shim's other
state; the shim consults it per sandbox, in the one place that knows
which element is about to build, and injects the spine only where needed.

### It traces what it cannot vouch for

Three cases get the spine regardless of the verdict, and each is a
different kind of not-knowing:

- an element the census **has no verdict for** — "we did not assess it"
  and "we assessed it and it is clean" are different claims, and only one
  is safe to skip;
- an element whose **name the shim could not recover**, which under a
  build-root override (`UX-56`) is *every* element, so a project that
  collapses its names gets `on` rather than a silently empty policy;
- **any failure to read the census at all**, which degrades to `on`.

A policy meant to preserve coverage has to fail towards coverage.

### The acceptance, on both classes

| | sandboxes | spine-traced | spine records | processes |
|---|---|---|---|---|
| `examples/01` (busybox), `auto` | 8 | **8** | — | 24 |
| `examples/01` (busybox), `on` | 8 | 8 | — | 24 |
| `examples/06` (all-dynamic), `auto` | 9 | **0** | **0** | 813 |

The per-element records from `auto` and `on` on `examples/01` are
**identical** — same elements, same commands — so `auto` loses nothing
where the spine is needed, and costs nothing where it is not.

On a mixed fixture (`examples/06` plus a busybox element and its
runtime), the census flags **exactly those two of thirteen** elements —
so the discrimination works within one project, not only between them.

### What the decision is recorded in

The shim writes `spine_traced` into its per-sandbox invocation record,
and the report reads it whenever that log exists:

```text
The ptrace spine ran for 2 of 13 sandbox(es) - the ones the pre-build census
says the LD_PRELOAD hook is blind for, plus any it could not assess. The rest
ran hook-only, at hook-only cost (UX-113).
```

Recorded rather than inferred from whether spine records appeared: an
element the policy skipped and an element that ran no processes look
identical in the trace, and only one of them is a coverage gap.

### On the default

`UX-112` measured the price at about a millisecond per process rather
than the ratio the docs quoted, and found no spine × opens interaction.
That makes `auto` the right *recommendation* — the guides now lead with
it — but the default stays `off` for one round, because `auto` has one
real build of each class behind it and the shipped default should not
change on that alone. The homogeneity check already treats the three
values as distinct, so a capture that used `auto` cannot silently join a
band of `on` or `off` ones.

Tests: 12 in `tests/unit/test_spine_auto_policy.py`.

## Verification Log

Done 2026-08-19. Three real traced builds (`examples/01` twice, once per
policy; `examples/06` once) plus the mixed-fixture census.

### Follow-up: the census tests read fixtures CI does not stage

The two census tests above went red on every `test` matrix job of
PR #103 (`1 failed, 1436 passed, 26 skipped`, identically on 3.9-3.12):

```text
tests/unit/test_spine_auto_policy.py:65: in test_a_busybox_project_needs_the_spine_everywhere
    assert all(verdicts.values()), "every element here runs static busybox"
E   AssertionError: every element here runs static busybox
E    + where dict_values([False x 10]) = {'all.bst': False, 'runtime.bst': False, ...}
```

`examples/01`'s busybox lives under `examples/**/files/runtime/bin/*`,
which `.gitignore` excludes; `examples/stage_runtimes.sh` puts it there
and only `bst-tests` and `bst-examples` run that script. So the census
found nothing static and answered `False` everywhere — correctly, for a
project that stages no binaries. The tests passed locally for the same
reason they failed in CI.

The second test was worse than red: it *passed* in CI, and would have
gone on passing. `examples/06`'s toolchain is gitignored too, so its
`assert not any(verdicts.values())` was satisfied by an empty shelf
rather than by a classification. Measured on a fabricated copy of
`examples/06` whose `files/toolchain` holds one empty `usr/bin/gcc`:

```text
old assertion  not any(verdicts): True   <- still passes on an empty shelf
new assertion  dynamic > 0: False  dynamic = 0
```

Both now resolve their project through `staged_project()`, which skips
with the staging-script name when the sentinel binary is absent — the
pattern `tests/unit/test_process_spine.py` already uses. `bst-tests`
runs both staging scripts and then `make test`, so the tier is exercised
for real somewhere in CI rather than skipped everywhere.

A third test pins the positive half `not any(...)` cannot: the census
found 45 executables in `examples/06`'s toolchain and classified every
one of them as dynamic. Without it, deleting the toolchain would
strengthen the second test rather than break it.

Tests: 12 in `tests/unit/test_spine_auto_policy.py` (was 11).
