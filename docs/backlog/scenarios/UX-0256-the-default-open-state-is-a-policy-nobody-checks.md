# UX-256: the default open state is a policy nobody checks

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1, and every future change to the viewer | **Topic:** guards

## Motivation

The user asked for *"a checker if everything is really collapsed by
default"*. Measured on the exported page of a real run, the answer is
that the policy is the opposite of that, deliberately, and that nothing
asserts either version:

```text
<details> on the page   49
open on load             3   — all three labelled "Why"
sections                12   — all open, by design
```

Both defaults are decisions with reasons already written down:

- `nav.js`: *"Default-open, always: a report that hid itself on first
  load would answer the navigation complaint by making the document
  harder to read, not easier."* (`UX-199`)
- `views.js:1043` opens the provenance chain on the **top action**
  only — the one claim a reader is most likely to challenge
  (`UX-227`).

So "everything collapsed" is not the rule and should not become it. The
defect is that **nothing checks the rule that does hold**: a change that
opened forty of the forty-nine, or closed the one that should be open,
would ship with no guard reddening — and the page would be the
573px-of-chrome problem (`UX-254`) all over again, in a different
element.

This is `UX-235`'s skip census in a second place: a count with named,
reasoned exceptions beats a prose claim that everything is fine.

## Required Fix

1. A census guard over the booted page: how many `<details>` exist, how
   many are open, and **which** — with the open set named and each name
   carrying its reason, so an addition to it is a decision someone
   wrote down rather than a diff nobody read.
2. The same for sections: all open is the rule, and the guard says so,
   so `UX-199`'s reasoning survives the next person who thinks
   collapsing them would be tidier.
3. The guard fails on drift in **both** directions — something newly
   open, and something that stopped being open.

## Out of Scope

- Changing either default. The reasons are written and this item is
  about holding them, not revisiting them.
- Remembering per-reader state. `collapsible()` already persists what a
  reader collapses; this is about the state on first load.

## Acceptance Test

The census reports the real numbers on the real exported page; opening
one more `<details>` in the source reddens it naming that one, and
closing the top action's provenance chain reddens it too.
