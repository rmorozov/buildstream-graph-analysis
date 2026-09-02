# UX-220: the numbers that need a sentence have one

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-201 (the description channel that already renders) | **Topic:** contracts

## Motivation

The round-24 review proposed "Why?" popovers on headline metrics and
called them almost free, "because the schema already carries
descriptions". Measured on `main`, that is false exactly where it
matters:

```text
floors             own description: no    described children:  0 / 0
capacity_verdict   own description: no    described children:  0 / 0
occupancy          own description: no    described children:  0 / 0
utilisation        own description: no    described children:  0 / 3
signals            own description: no    described children:  0 / 3
headline           own description: yes   described children:  4 / 6
confidence         own description: no    described children:  2 / 4
```

`floors.certified_us` is the most misreadable number this tool
publishes — a **lower bound certified by the graph and the observed
work, not a prediction** — and the schema says nothing about it at all.
`T∞`, headroom, efficiency and the capacity verdict are in the same
state.

The viewer already renders `description` as a popover, recursively, at
every depth (`UX-201`). The renderer is not the missing piece. **The
descriptions are the deliverable.**

## Required Fix

1. A description on every published node whose meaning is not evident
   from its name — every floor, every capacity-verdict field, the
   occupancy and utilisation members, the three signal arrays. Written
   in the register the tool already uses: what it is, what it is not,
   and what it cannot support.
2. Each says its own bound where it has one — `certified_us` is a
   floor, `chain_ratio` is a share of wall-clock, `efficiency` is a
   ratio against a floor and not against an ideal.
3. `bga analyze`'s text report and `--help` take the same sentences
   from the same constant, so a reworded description cannot leave two
   different explanations in the tool.
4. A guard that a published leaf carrying a `bga:quantity` also carries
   a description, so the next field added cannot arrive mute.

## Out of Scope

- New metrics, or changing what any of them mean.
- Long-form explanation — a sentence or two, with the docs link where
  there is more (`UX-170`'s disputed region is the precedent).
- Viewer work: the popover already renders.

## Acceptance Test

Every leaf in `analyze/v1` that declares a quantity also declares a
description (asserted over the whole schema, not a list). The rendered
page shows `certified_us`'s sentence on hover, read from the schema and
not from a string in the viewer.

Mutations, each asserted red: remove `certified_us`'s description → the
completeness guard fails and names it; put a second wording of it in
`report/text.py` → the one-source guard fails.

## Outcome (round 26)

The coverage table above reproduced exactly on `main` before anything
changed, and the premise held: the renderer was never the missing piece.
`hintsOf` has copied `description` since UX-201 and the popover renders
recursively at every depth. The descriptions were the deliverable, and
so — unexpectedly — was the structure under them.

**The number, over the five published documents:**

```text
before   112 leaves declare a bga:quantity, 84 of them say nothing
after    133 leaves declare a bga:quantity,  0 of them say nothing
```

The count rose because `floors`, `capacity_verdict` and `occupancy`
declared **no members at all** — 0 of 0, not 0 of 12. There was nothing
to describe until there was something to describe. Measured on the
exported golden page, what a reader can actually hover went from **54
to 185** embedded description keys.

### Two things in the task file were wrong, and both were worth finding

**`floors.certified_us` has never existed.** It is named above as "the
most misreadable number this tool publishes", and the acceptance test
asks for a mutation that removes its description. No such field is
emitted anywhere; the certified floor is `floors.lb` and the headroom is
`floors.certified_headroom`. The intent was right and is implemented on
the real fields. The accessor now refuses that exact path out loud,
which is the guard the phantom name deserved:

```text
KeyError: analyze/v1: no such path 'floors.certified_us'
```

**`utilisation` declared three names nothing emits.** UX-201 hinted
`peak_rss_mb`, `cpu_pct` and `cpu_seconds`; `_compute_utilization` has
never put any of them in that object, and a repository-wide search finds
them only in `schemas.py`, in comments, and in UX-201's own test. The
hints described a shape that does not exist — which is precisely why the
twelve members `utilisation` really carries went unhinted and
undescribed for four rounds without anything noticing. A guard that
checks each described member against a real payload replaces them, and
that guard is the general form of this bug rather than a patch for this
instance.

### A deliberate change to an existing guard, recorded rather than absorbed

UX-201's three tests used those phantom keys as their fixtures, so
removing them turned three green tests red. They test the *renderer* —
does a declared `megabytes` beat a name-sniffed `bytes`? — and that
question does not need a phantom to ask. They were **re-pointed at
fields a run publishes** (`correlate/v1`'s
`memory_envelope.host_memory_mb`, and `utilisation.useful_pct`) rather
than deleted or relaxed, and they still redden when `quantityFor` is
made to lose to `guessQuantity`: the original bug, caught on a real
shape now. The one test that asserts what `guessQuantity` does with a
*name* keeps the original two names, deliberately — it needs no schema
node at all.

### Clause 3 without a new constant

The obvious reading is a `DESCRIPTIONS` table that the schema, the
report and `--help` all import. That is one more thing that can drift
from the schema. Instead the schema *is* the source and
`schemas.description(document, path)` is how everything reads it —
walking `properties`, stepping into `items` on a `[]` segment, and
raising `KeyError` on a path that does not resolve or carries no
sentence. A caller asking for a sentence that does not exist is a typo,
and returning `""` would print nothing and look deliberate.

`bga analyze`'s Dispatch Occupancy line and `bga floors --help` both
read it now. The parenthetical the report used to carry in its own words
is asserted absent, so reintroducing it fails rather than drifting.

**Mutations, each verified red and reverted:** drop `floors.lb`'s
description (4 guards); re-add `peak_rss_mb` to `utilisation` (the
describes-what-is-published guard); give `text.py` its own second
wording of the occupancy sentence (2 guards); make the accessor return
`""` instead of raising; make `quantityFor` lose to `guessQuantity` (3
guards, including both re-pointed ones); re-add `cpu_pct` (the new
phantom guard).

One guard caught its own author: the first draft of
`findings[].evidence.failed_count` read "Elements that failed." — three
words — and the sentence-shape check rejected it. The sentence was
rewritten rather than the threshold lowered.

**Deviation from the Required Fix:** clause 1 says "every floor, every
capacity-verdict field, the occupancy and utilisation members, the three
signal arrays". That was done and then exceeded: clause 4's guard is
written over *every* published document, so `blast/v1`, `compare/v1`,
`correlate/v1` and `store/v1` were described too. A guard scoped to one
document would have let the next mute field land in another.
