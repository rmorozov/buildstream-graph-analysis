# UX-596: build time in the team's units

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-230 (a price on a chosen set), UX-581 | **Serves:** R8, the engineering lead funding infrastructure | **Topic:** analysis

## Motivation

Direction 9's third argued step, and R8's half of it. Headline and
what-if price a fix in *build seconds*, for one project. `UX-580`
measured that nothing converts to anything a budget speaks, and
`git grep "cost translation" -- docs/backlog/scenarios` reaches only
`UX-234`.

## Required Fix

An opt-in rate — engineer-hours per build-hour, or a currency per
machine-hour — that converts a priced fix into the unit the lead
argues in, with the rate stated as an input the reader supplied and
never as a measurement.

## Out of Scope

- Choosing a default rate — declined: a made-up rate presented as a
  figure is the anecdote this item exists to replace.

## Acceptance Test

With no rate the output is unchanged; with one, every converted
figure names the rate that converted it. Mutation: print a converted
figure without its rate — red.
