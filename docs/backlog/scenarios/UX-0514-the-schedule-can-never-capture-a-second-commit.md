# UX-514: the capture schedule can never produce a second commit

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-81` (the schedule), `UX-92` (the gate that needs the variation) | **Found by:** round 76, re-checking `UX-92` for the fourth time | **Serves:** `UX-92`'s gate, which has been "deferred, re-check next month" since n=3 | **Topic:** capture

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

## Outcome

_Not started._
