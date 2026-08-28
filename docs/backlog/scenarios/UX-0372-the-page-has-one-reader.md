# UX-372: the page has one reader

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-231 (every direction names its reader), UX-353 (the roles table), UX-365 (the finding that claims the superlative) | **Serves:** the build engineer, the CI owner and the module author, who currently share one page | **Topic:** viewer

## Motivation

The round asked whether the report should show the biggest problem *per
role*. It does not show one per role because it does not know roles
exist.

`bga:role` is in the vocabulary, and it is a **column** role — what a
cell is for a renderer, checked in `bga/schemas.py` against a closed set
and read by `bga/viewer/format.js`. There is no reader role anywhere in
the payload or the page.

So the page opens with one question — "What should I do?" — answered
once, for whoever is looking. Measured on `macro_micro`, the three top
actions are all the same kind of advice: shorten this element, shorten
that one, shorten the third. That is the right answer for someone who
can change `core.bst`. It is not an answer for:

- **the CI owner**, whose lever is `capacity-recommendation` (builders
  x max-jobs, finding #9) and the efficiency gate, not any element;
- **the module author**, who cannot see their own element unless it
  happens to be in the top three, and whose question is "is my thing a
  problem" rather than "what is the biggest problem";
- **the person who ran the build once** and wants to know whether the
  number is normal, which is `cache-hit-ratio` and the trend.

Every one of those answers is already computed. `capacity-recommendation`
is finding #9 of 11. The element table can be filtered to one element.
The cache and trend sections exist. What is missing is any statement of
who each is for, so the reader does the routing.

## Required Fix

Name the readers, and route the top of the page by them.

- A small closed set — the roles `UX-231` already made every *direction*
  name, applied to the report's own findings.
- Each finding declares which reader it serves, in the contract, so the
  page does not derive it (Direction 7).
- The decision chapter offers the biggest lever **for the reader who
  says who they are**, defaulting to today's behaviour when nobody says.

The default matters: this must not become a page that answers nothing
until you fill in a form.

## Falsification

Every published finding declares a reader, and the set of readers with
at least one finding is more than one. That fails today at zero.

Then the routing: choosing a reader changes which finding the decision
chapter leads with, and choosing a different one changes it again. A
selector that reorders nothing is furniture.

## Out of Scope

Per-role *pages*. One page, one payload; the roles select what leads,
not what exists — `UX-281` is what happens when the tool grows pages
nobody navigates back from.
