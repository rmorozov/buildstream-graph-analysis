# UX-511: the guide the README sends readers to teaches a retired reading as current

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-492` (the same block, on the front door) | **Found by:** round 75, auditing `UX-492`'s block line by line | **Serves:** the reader who follows the README's link and gets the same stale output with prose built on it | **Topic:** docs

## Motivation

`UX-492` dated the README's real-project block and named the one
sentence no emitter can produce. The guide it links carries the same
defect and two more:

```text
docs/guides/real-project.md:415-432   the identical retired `Note:` line,
                                      and the pre-UX-365 `Biggest Opportunity`
docs/guides/real-project.md:456-460   prose teaching the retired mesh reading
docs/guides/real-project.md:1018      "analysed with the current code"
```

The last is the worst of the three, because it is a claim about
freshness rather than a stale figure: the appendix asserts the Plane 1
figures are that capture's `run/` directory analysed with the current
code, which `UX-492`'s audit has just shown is false — four sentences
the emitter prints today are absent from the pasted block.

## Required Fix

- The block is dated the way `UX-492` dated the README's, from the same
  capture record, or re-rendered from a run this repository can perform.
- The prose at :456 no longer teaches a reading the emitter retired.
- The appendix's freshness claim is true or is removed. It is one
  sentence and it is the one a reader would rely on.
- Whatever it becomes, a guard reads it — `UX-492` found that none of
  the three guards the round expected to cover its section did.

## Out of Scope

- `README.md`, closed as `UX-492`.
- The capture itself. It is a 3614-second freedesktop-sdk build
  that neither this container nor CI can perform, which is the
  same constraint `UX-492` recorded and worked within.

## Acceptance Test

`git grep -n "zero slack\|Biggest Opportunity" docs/guides` returns
nothing undated, and the appendix sentence pasted with whichever way it
was resolved.

## Outcome

_Not started._
