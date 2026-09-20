# UX-902: a showcase case is two captures, and there is nowhere to put one

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-891 (the CPU floor, which the first case reads), UX-172 (blast) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 7) — adoption needs stories that can be shown, and the owner named the first two | **Serves:** R1 and R2 (the developers being asked to adopt it), R8 (the manager being asked to fund the time) | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

The repository documents what the tool *can* answer in fifteen guides
and ninety audit rounds, and holds no document of the form *a real
build was slow, bga said this, we changed that, and here is the
re-measured result*. That is the document adoption runs on, and its
absence is why the tool is currently sold by reading its own manual.

Two cases are in hand and neither is hypothetical:

- **The lone element capped at the default jobs.** An LLVM element
  builds alone for about forty minutes on an agent with far more cores
  than BuildStream's default `max-jobs` gives it. This is the axis
  argued in [`in-step-parallelism.md`](../../design/in-step-parallelism.md),
  whose first increment is `UX-891`, with the jobserver as the
  intervention half — the strongest before/after the tool can currently
  show.
- **Redundant rebuilds.** `bga blast` answers what a change to a
  repository, a path or an element rebuilds; the usual cause is source
  keying (a `git` source keys on its ref, a `local` source on content).
  A developer-scenario case that needs no new code.

## Required Fix

A case-file shape, and the first case written in it. The shape is the
rule this row exists to hold:

> A showcase case carries **both captures** — the before, the change,
> and the after, each with the command that produced it and the run it
> came from. A case that names a saving without the second capture is a
> projection, and `whatif` is where projections live.

Each case: the symptom as the owner saw it, the command, the finding
verbatim, the change made, the re-capture, and the delta with its noise
band (`UX-899`'s band where a band exists). Where a case is projected
rather than re-measured, it says so in its own first line.

## Out of Scope

Marketing copy, benchmarks against other tools, and any case whose
second capture does not exist yet — those wait rather than shipping as
projections dressed as results.

## Acceptance Test

`docs/audits/` or a new `docs/cases/` holds at least one case in the
shape above, and a guard reads every case file for two capture
references and a delta, reddening on a case that has only one. The
README's case link resolves. Mutation: remove the after-capture
reference from a case (the guard names that file).

## Outcome
