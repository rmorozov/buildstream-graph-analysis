# UX-89: correlate prints the same finding seven times instead of once

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-72 (done)

## Motivation

On `examples/06`'s baseline, `bga correlate`'s "What to do next" prints
seven near-identical blocks — `lib-a.bst` through `lib-f.bst` and
`app.bst` each get the same four lines ("compute-bound at ~1.6 cores …
`cc1plus` problem … `ranlib` is a SINGLE process holding 0.1s … opened
no file staged by N declared build dependencies"), differing only in the
dependency list. Forty lines to convey two facts. The `ranlib`/`ar`
"serialization point" line is also noise at this scale: 0.1s single
processes inside 2s elements are how `ar` works, not a finding — the
UX-72 relative bar appears not to apply to the single-process rule.

At fdsdk scale the same structure would bury the one distinctive row
(`core.bst`) under dozens of interchangeable ones.

## Required Fix

1. Group elements whose finding sets are identical up to parameters:
   one block naming the elements (`lib-a..lib-f, app.bst: already
   compute-bound at 1.4–1.8 cores; cc1plus is 70–76% of each`), with
   per-element figures available in JSON as today.
2. Apply UX-72's relative-materiality bar to the single-process
   serialization rule: a single process below the same share threshold
   of its element's realizable saving is not reported.

## Out of Scope

- JSON shape (stays per-element; grouping is a text-rendering concern).
- The ranking itself (UX-71, settled).

## Acceptance Test

On the round-10 baseline capture of `examples/06`: the text output
contains exactly one grouped block for the six libs + app, `core.bst`
still leads with its full row, no `ranlib`/`ar` line under 1% of the
element's worth appears, and `--format json` is unchanged. On the fdsdk
capture, `correlate`'s text length drops while naming the same top
elements first.

---

## Resolution (round 11)

**Status:** 🟢 Done

Reproduced first, against a real dual-plane capture of `examples/06`
taken for this task (bst 2.7.0 + a real `bwrap`, `--builders 4
--max-jobs 4`, BuildStream cache cleared between the two planes) — not
against the audit's recollection of one.

**Before — 48 lines**, of which seven blocks were interchangeable:

```text
  core.bst:
    - holds 42% of the critical path and fixing it is worth 9.0s (24.2% of the build), but runs at only 0.87 cores busy - it is waiting, not computing, and its native build asked for -j1: ...
    - 81% of its measured CPU is one binary, `cc1plus` (10 process(es), 9 CPU s) - ...
    - `ranlib` is a SINGLE process holding 0.5s of wall time - a serialization point no job count can help; ...
  lib-c.bst:
    - holds 9% of the critical path and fixing it is worth 3.0s (8.2% of the build) - already compute-bound at 1.82 cores busy, ...
    - 78% of its measured CPU is one binary, `cc1plus` (5 process(es), 4 CPU s) - ...
    - `ranlib` is a SINGLE process holding 0.2s of wall time - ...
  lib-a.bst:                      # and lib-d, lib-e, lib-f, lib-b, app - five more of the same
    ...
```

**After — 21 lines:**

```text
  core.bst:
    - holds 42% of the critical path and fixing it is worth 9.0s (24.2% of the build), but runs at only 0.87 cores busy - it is waiting, not computing, and its native build asked for -j1: remove `notparallel` / raise its job count before touching its sources
    - 81% of its measured CPU is one binary, `cc1plus` (10 process(es), 9 CPU s) - this element is a `cc1plus` problem, so look there before anywhere else
    (81% of this element's processes were measured)
  app.bst, lib-a.bst..lib-f.bst (7 elements, 6-9% of the critical path each, 2.0-3.0s apiece, 19.7s together):
    - already compute-bound at 1.4-1.8 cores busy - nothing to gain from their parallelism; shortening them means less work
    - `cc1plus` is 72-78% of each one's measured CPU - they are all the same problem, so look there before anywhere else
    (81% of each element's processes were measured)
```

### 1. Grouping

Elements are grouped on their **finding-id signature**, not on their
numbers: two elements with the same findings are the same *story*, and
the numbers are what the grouped line puts a range on. Consequences
worth stating:

- **A group takes the position of its strongest member**, so grouping
  never reorders what leads. `core.bst` is still first, and it is alone
  because `pinned-to-one-job` is exactly the distinction the report
  exists to surface.
- **A single-element group renders exactly as it always did** — the bare
  element name, the finding in its own words. Nothing changes for the
  case that was never repetitive.
- **The impact figures move to the header.** For one element they belong
  in the finding text; for a group they are what *distinguishes* its
  members while the findings are what it shares. The header also carries
  the total (`19.7s together`), because seven elements worth 3s each are
  a different decision from one worth 3s.
- **A finding whose figures do not generalize keeps its own words.**
  `peak-memory` is an absolute RSS to multiply by concurrency and
  `redundant-operation` names *other* elements; averaging either would
  say something the measurement does not. The block gets longer rather
  than wronger.
- **The name contraction never invents a family.** `lib-a.bst..lib-f.bst`
  only forms from names differing in a single trailing character that
  runs consecutively; `app.bst, codegen.bst, core.bst` stays spelled
  out, and two elements are never contracted.
- **The overflow line counts elements, not groups** — the cap is about
  how much a reader is asked to read, but "how many were withheld" is a
  question about elements.

### 2. The serialization bar

`ar` and `ranlib` are single processes by construction, so every element
linking a static library earned a "SINGLE process holding 0.2s" line.
The rule had no materiality bar at all while every other Plane 2 rule
had one.

It now uses the same shape as the redundancy rule:
`max(1.0s, 1% of the element's realizable saving)`. On this capture that
removes all seven (0.2s inside elements worth 2.0–3.0s, and `core.bst`'s
own 0.5s inside 9.0s). It is not switched off — a 12s `ld` inside a
60s-worth element still reports — and the *relative* half raises the bar
on large elements rather than lowering it: 4s of `ld` inside an element
worth 900s is 0.4% and stays silent.

### JSON

Grouping is a text concern and touched the JSON **not at all** — verified
by diffing `--format json` before and after and confirming that every
key, every element, and every remaining recommendation is identical. The
only JSON difference is the sub-materiality `serialization-point` rows
disappearing, which is item 2 doing its job.

### Acceptance

- Exactly one grouped block for the six libs + `app.bst`. ✅
- `core.bst` still leads with its full row. ✅
- No `ranlib`/`ar` line below the bar anywhere. ✅
- `--format json` unchanged apart from the intended filter. ✅
- Text length 48 → 21 lines on the same capture. ✅
- 20 new tests in `tests/unit/test_correlate_grouping.py`; suite 1201
  passed; `make lint`, `make check-clean` green.

**Not verified:** the acceptance test's second half — "on the fdsdk
capture, `correlate`'s text length drops while naming the same top
elements first" — was not run. The published fdsdk capture's `correlate`
output has no repeated finding sets to collapse (its elements differ),
so the grouping is a no-op there by construction; the claim that would
need checking is that it *stays* a no-op, and that needs a fresh capture
this task did not take.
