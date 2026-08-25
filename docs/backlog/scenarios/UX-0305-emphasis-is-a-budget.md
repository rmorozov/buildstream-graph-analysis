# UX-305: emphasis is a budget, spent once per block

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-304 (the tokens), styleguide §4.6 | **Serves:** R1 | **Topic:** viewer

## Motivation

The user's ask — rules for emphasis and color so valuable
information stands out — inverted into the rule that makes it
possible: emphasis only works when it is scarce. Styleguide §4
budgets it: one emphasized element per block, one accent for the
whole page, text in ink never in status tone, status tone never
without a shape. The current page grew section by section and has
never been audited against a budget — the audit *is* this task.

## Required Fix

A conformance pass over every rendered section against §4: demote
double emphases, move status tones off text onto badges/borders,
collapse any second accent into the one. Then the guards that keep
it: a booted check that no block contains two emphasis-class
elements; the status-tone-with-sibling check (`UX-304`); and the
checklist line in the fixing guide so a new section ships within
budget or amends the guide.

## Out of Scope

- New emphasis mechanisms (size scales, animation — declined:
  §4's budget is about scarcity, not new instruments).
- The chapter structure and ordering (UX-286's domain).

## Acceptance Test

The booted golden and 1,202-element pages pass the budget walk
(zero blocks with two emphasized elements; zero status-toned text
nodes; one accent hue in computed styles); mutation: bolding a
second value in the headline block reddens; the pass's demotions
are listed in this file's log with before/after screenshots or DOM
extracts for three sections.
