# UX-71: `bga correlate` ranks and gates on a score that saturates, so the join's headline verdict never fires on a real build

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-70` (done — which measured the right number and did not wire it here)

## Motivation

`bga/correlate.py`'s own module docstring states what the join exists to
produce:

> **"the element that dominates your critical path is not compute-bound,
> so fix how it is built, not what it builds"**

On round 9's real `freedesktop-sdk` capture, that sentence is never
printed. Not for any element. The eight rows the join does print all say
the same, weakest thing — see `UX-72`.

The cause is one number. `_plane1_view` takes each element's share from
`structural.sensitivity.top_opportunities`, and `_recommend` gates every
compute-bound claim on it:

```python
matters = share is not None and share >= _CRITICAL_PATH_SHARE   # 0.05
```

Measured on the real capture (`bga correlate --format json`):

| element | share | `potential_saving_us` | cores busy |
|---|---|---|---|
| `components/_private/cmake-stage1.bst` | 0.0316 | 114.1s | 3.41 |
| `components/bison.bst` | 0.0316 | 114.1s | **0.91** |
| `components/doxygen.bst` | 0.0316 | 114.1s | 3.56 |
| `components/openssl.bst` | 0.0316 | 114.1s | 1.61 |
| `components/python3.bst` | 0.0316 | 114.1s | 1.86 |

**Every candidate carries the identical score, and it is below the gate.**

## Why the score saturates

`compute_sensitivity` caps each element's saving at the *global* next
binding gap:

```python
potential_saving[key] = min(float(durations.get(key, 0)), next_binding_gap)
```

On this build `next_binding_gap` is 114.1s, so every element longer than
114.1s — which is all five — is capped at the same value, and
`0.0316 = 114.1 / 3610.5`. The cap is not wrong as a *bound*; it is
simply not a *ranking*, because it is a constant over exactly the
population being ranked.

Two consequences, both visible in the real output:

1. **The order is alphabetical.** `joined.sort(key=lambda e:
   (-e.potential_saving_us, e.element))` breaks a five-way tie on the
   name, which puts `components/bison.bst` (144.2s, 4.0% of the path)
   second — above `openssl.bst` (672.1s) and `doxygen.bst` (513.5s). A
   list headed "ranked by Plane 1 impact" is not ranked by Plane 1
   impact.
2. **The gate never opens.** 0.0316 < 0.05, so no element is ever
   `matters`, so neither the compute-bound nor the not-compute-bound
   sentence is reachable on this build at all.

And what the gate suppresses is the finding the join was built for:
`components/bison.bst` ran at **0.91 cores busy** over 144.2s while
`cmake-stage1` ran at 3.41 and `doxygen` at 3.56 on the same 4-core
runner. One core busy is the `notparallel` signature named in
`_COMPUTE_BOUND_CORES`'s own comment. The tool measured it, held it in
`cores_busy`, and said nothing.

## `UX-70` already computed the number this needs

`signals.critical_path_detail[].realizable_saving_us` — "what the
critical path would actually lose if this element became instant" — is
published in `analyze --format json` and used by the text report:

```text
cmake-stage1  1569.8s realizable   (43.4% of the build)
openssl        522.5s realizable   (14.5%)
doxygen        513.5s realizable   (14.2%)
```

A 5× spread, a real ranking, already in the artifact `correlate` reads.
It is simply not read: `_plane1_view` predates `UX-70` and still consumes
`top_opportunities`.

So the two commands now disagree about what to fix first on the same
build — `analyze` says cmake-stage1, openssl, doxygen; `correlate` says
cmake-stage1, bison, doxygen, openssl, python3 — and only one of them is
ranked by anything.

## Required Fix

1. **Rank on `realizable_saving_us`.** `_plane1_view` reads
   `signals.critical_path_detail` and prefers it, falling back to
   `top_opportunities` only where the field is absent (a run analysed by
   an older `bga`), so an old artifact degrades rather than crashes.
2. **Gate on the same quantity.** `_CRITICAL_PATH_SHARE` becomes a share
   of the *build* that fixing this element would actually recover, not a
   share of a capped proxy. The threshold's job — "true but not what to
   do next" — is unchanged; only the quantity it reads changes.
3. **Never rank on a tie.** When every candidate carries the same score,
   say so instead of sorting by name. A silent alphabetical order
   presented as an impact ranking is the defect here, and it will recur
   with any saturating metric.
4. **Keep `analyze` and `correlate` consistent by construction.** Both
   should name the same first element on the same run. A test that
   asserts this on a fixture is cheaper than re-noticing the divergence
   in round 11.

## Out of Scope

- Changing `compute_sensitivity`'s cap. `min(duration,
  next_binding_gap)` is a correct *bound* and other consumers depend on
  it; the fix is to stop using a bound as a ranking.
- `_COMPUTE_BOUND_CORES`'s value (1.25). The population separation it was
  chosen from — 0.91 against 1.61–3.56 on real data — is wider than it
  was on `examples/06`, so the constant is if anything better supported
  now than when it was set.

## Acceptance Test

1. On round 9's capture, `bga correlate` names `components/bison.bst` as
   holding a real share of the path and running at 0.91 cores busy —
   "waiting, not computing" — and does so *below* `cmake-stage1`,
   `openssl` and `doxygen` in the ranking.
2. `bga analyze` and `bga correlate` name the same element first.
3. An artifact whose `critical_path_detail` carries no
   `realizable_saving_us` still produces a join, with the old ordering
   and no crash.

## Fix Implemented

`_plane1_view` now reads `signals.critical_path_detail`: the saving from
`realizable_saving_us`, the share from `share_of_path` — the same field
`bga analyze` prints, so the two commands cannot describe one element
with two different numbers. `top_opportunities` remains as a fallback for
an artifact analysed before `UX-70`, and which metric was used is
published as `ranking.metric`.

Same capture, same command, before and after:

```text
before                                   after
1. cmake-stage1  (114.1s, tied)          1. cmake-stage1  1569.8s (43.4% of the build)
2. bison         (114.1s, tied)          2. openssl        522.5s (14.5%)
3. doxygen       (114.1s, tied)          3. doxygen        513.5s (14.2%)
4. openssl       (114.1s, tied)          4. bison          144.2s ( 4.0%)
5. python3       (114.1s, tied)          5. python3        114.1s ( 3.2%)
```

And the sentence the join exists for now appears, for the first time on
real data:

```text
components/_private/cmake-stage1.bst:
  - holds 43% of the critical path and fixing it is worth 1569.8s (43.4% of the
    build) - already compute-bound at 3.41 cores busy, so there is nothing to gain
    from its parallelism; shortening it means less work
components/bison.bst:
  - holds 4% of the critical path and fixing it is worth 144.2s (4.0% of the build),
    but runs at only 0.91 cores busy - it is waiting, not computing: look at how it
    is built before what it builds
```

### One correction to this task as filed

The Required Fix said the threshold's job was unchanged and only the
quantity it read would change. Applied literally, that is wrong: at 5% of
the build `components/bison.bst` — worth 144.2s, running at **0.91 cores
busy** — falls *below* the gate and stays silent, which is the finding
this task was filed to surface.

Worth is only half of "low-hanging fruit". The other half is what the fix
costs, and ~1 core busy is the one Plane 2 signal that names a cheap fix
outright: a job count, not a rewrite. So an element below the gate still
earns a line when Plane 2 says the fix is cheap and its saving clears
`UX-65`'s existing "below 1% of wall clock is rounding" floor —
`_CHEAP_WIN_FLOOR`, reusing that floor rather than introducing a tuned
constant. `python3.bst` (3.2%, 1.86 cores busy) correctly stays silent
under the same rule: there is no cheap fix there to name.

### Degenerate rankings are declared, not broken by name

Any metric can saturate on some graph. When every ranked element carries
the same saving the join now says so, instead of presenting the
alphabetical tiebreak as impact order:

```text
NOTE: every ranked element carries the same Plane 1 impact (114.1s), so the order
below is alphabetical, not an impact ranking - read the rows, not their positions
```

Tests: 6 new in `tests/unit/test_correlate.py`, including the real
five-way tie as a fixture and a standing assertion that `bga analyze` and
`bga correlate` name the same element first. Suite: 1069 → 1075.

## Verification Log

Filed 2026-08-18 (round 10 preparation). Every figure is from the capture
published to `captures/fdsdk-latest` as `5eda28a` (run `32064333551`,
`bga_ref` `1143f2b`): the share/saving/cores table is from `bga correlate
--format json capture/run capture/native-report.json` run at
`74c94e3`, and the realizable savings are from `bga analyze --format
json` on the same `run/`.
