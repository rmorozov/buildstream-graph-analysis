# UX-514: the capture schedule can never produce a second commit

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-81` (the schedule), `UX-92` (the gate that needs the variation) | **Found by:** round 76, re-checking `UX-92` for the fourth time | **Serves:** `UX-92`'s gate, which has been "deferred, re-check next month" since n=3 | **Topic:** capture

## Motivation

`UX-92`'s cache gate has been deferred four times — n=3, n=5, n=6 and
now n=7 — each time on the same sentence: a gate needs history across
different commits and there is none. Each re-check implied the next
capture might supply one. It cannot:

```text
.github/workflows/real-project-capture.yml:74    default: 953683fb96b8...
.github/workflows/real-project-capture.yml:163   FDSDK_REF: ${{ github.event.inputs.fdsdk_ref || '953683fb96b8...' }}
```

A `schedule:` trigger cannot supply workflow inputs, so both crons take
the hardcoded default. Nine published capture refs, one commit:

```text
captures/fdsdk/953683fb-cold-b4j4-32133112003         captures/fdsdk/953683fb-incremental-b4j4-32177690506
captures/fdsdk/953683fb-cold-b4j4-33490577715         captures/fdsdk/953683fb-incremental-b4j4-32223468993
captures/fdsdk/953683fb-incremental-b4j4-32064333551  captures/fdsdk/953683fb-incremental-b4j4-32615919649
captures/fdsdk/953683fb-incremental-b4j4-32113933158  captures/fdsdk/953683fb-incremental-b4j4-33302016575
captures/fdsdk/953683fb-incremental-b4j4-32122941503
```

The pin is not a mistake. It is what makes the seven incrementals
repeated readings of one thing, which is what a noise band is. The
defect is that nothing anywhere says the schedule is structurally
incapable of the variation `UX-92` is waiting for, so the wait reads as
temporary and has been renewed four times.

## Required Fix

A decision, recorded, between the two shapes — not a third re-check:

- **Keep the pin, and say so.** `UX-92`'s gate is closed as
  "not gateable on this history by construction", and the workflow's
  comment states that the pin is why the band means anything.
- **Advance it on a stated cadence** — a third cron, or a periodic pin
  bump — and accept that captures either side of a bump are not one
  population. Then `UX-92`'s gate has commits to compare and the
  homogeneity check (`fdsdk_ref` is already a refusing field) keeps the
  two populations apart on its own.

Whichever it becomes, a guard reads the workflow for it: the pinned
default and the cron set are the mechanism, and `UX-354` is on file
because a workflow nothing reads drifts.

## Out of Scope

- The gate's threshold. That is `UX-92`'s, and it stays deferred until
  this is decided — this row exists so that deferral has an end.
- The cold cadence, which `UX-96` set monthly on a measured argument.

## Acceptance Test

`git grep -n 953683fb .github/workflows/real-project-capture.yml`
returns the pin with a comment stating which of the two shapes was
chosen, and a guard that reddens when the pin and the comment disagree.

## Outcome (round 80, 2026-09-02) — 🟢 Done

**The decision: keep the pin.** The first of the two shapes, taken from
this file's own Motivation — seven incrementals of one ref are repeated
readings of one thing, and captures either side of a bump would be two
populations with the band measuring the bump.

### The gap, measured

```text
$ git grep -n 953683fb .github/workflows/real-project-capture.yml
74:        default: 953683fb96b82cdf6d7941c4ba9859378942f22b
163:  FDSDK_REF: ${{ github.event.inputs.fdsdk_ref || '953683fb...' }}
```

Two literals, no comment on either, and nothing anywhere saying a
`schedule:` trigger cannot supply an input. `UX-92`'s gate had been
deferred four times against that silence.

### After

```text
$ git grep -n 953683fb .github/workflows/real-project-capture.yml
96:        default: 953683fb96b82cdf6d7941c4ba9859378942f22b
185:  FDSDK_REF: ${{ github.event.inputs.fdsdk_ref || '953683fb...' }}

$ sed -n '74,95p' .github/workflows/real-project-capture.yml
        # UX-514: capture-ref-policy: pinned.
        ...
        # What it costs, stated so nobody waits for it again: `UX-92`'s
        # cache gate needs history across *different* commits and this
        # schedule cannot produce any, so that gate is not gateable on
        # this history by construction. It was deferred at n=3, n=5, n=6
        # and n=7 on the reading that the next capture might supply the
        # variation; it cannot.
```

`tests/unit/test_the_pinned_ref_is_a_decision.py`, 4 passed 1 skipped.
The skip is the `advanced` branch, and it is a clause rather than a
hole: swapping the word runs it, and it reddens (C3).

### Mutations verified red and reverted (5, plus one that must not fire)

| # | mutation | reddened |
|---|---|---|
| C1 | the cron's copy of the pin bumped, the input's not | `test_the_two_copies_of_the_pin_are_the_same_commit` — 1 failed, 3 passed, 1 skipped |
| C2 | `FDSDK_REF` gains `github.event.schedule == '0 4 1 * *' && 'main'`, word still `pinned` | `test_a_pinned_ref_has_nothing_that_moves_it` — 1 failed, 3 passed |
| C3 | the word changed to `advanced`, nothing else | `test_an_advanced_ref_has_something_that_moves_it` — 1 failed, 3 passed |
| C4 | the comment stops naming `UX-92` | `test_the_comment_says_what_the_choice_costs` — 1 failed, 3 passed |
| C5 | the policy word deleted, the argument for it left | the declaration clause and both mechanism clauses — 3 failed, 2 passed |
| — | `capture-ref-policy: advanced` planted in the **`target`** input's comment | nothing: 4 passed, 1 skipped, which is the answer |

**A guard that did not discriminate, and what it reads now.** The first
version of C3's clause accepted "`ls-remote` appears in the file" as
evidence that something moves the ref. C3 stayed **green**: the only
`ls-remote` in this workflow is in a comment explaining how to *list*
published capture refs. Rewritten to read bindings — a non-comment line
matching `FDSDK_REF[:=]` — which then caught its own second version
counting the three steps that merely *read* `$FDSDK_REF`.

### Deviation from the Required Fix

The shape's second half — "`UX-92`'s gate is closed" — is a marker and a
row move, and this track may not write
`docs/backlog/scenarios/README.md`. `UX-92`'s file now states the
decision and that its row belongs at ⚪; **the row move is owed to the
index.**

```text
$ make lint          ruff + pymarkdown, All checks passed!
$ make test-touching 79 passed, 1 skipped in 2.22s
```
