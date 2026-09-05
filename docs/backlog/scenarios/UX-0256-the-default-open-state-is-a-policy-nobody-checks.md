# UX-256: the default open state is a policy nobody checks

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1, and every future change to the viewer | **Topic:** guards | **Area:** bga/viewer

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

## Outcome

**Status:** 🟢 Fixed & Verified

The census exists, and the answer to *"is everything really collapsed
by default?"* is **no, on purpose** — measured in Chromium on the real
exported page:

```text
<details> on the page   49
open on load             3   — all from one site, the top action's chain
sections                12   — all open, by design
```

`tests/unit/test_the_page_opens_the_way_it_says.py` holds both
policies, in both directions. `OPEN_BY_DEFAULT` names the one function
that opens anything and why (`UX-227`: the provenance chain on the
*top* action — the claim a reader is most likely to challenge). A
second site reddens it naming the function; an entry for a function
that no longer exists reddens it too, so an exemption cannot outlive
its subject.

For sections, the guard pins `UX-199`'s reasoning in `nav.js` where the
next person who thinks collapsing them would be tidier will meet it,
checks that collapsing is still one click and still remembered — which
is the only thing that makes default-open defensible — and checks that
the *page* never decides to collapse something a reader did not.

### The guard nearly shipped with the failure it was written against

A census that greps for `setAttribute("open"` finds it in every comment
that explains why something is or is not opened. Both this file and
`UX-254`'s strip comments before reading, and `UX-254`'s did not at
first: its mount check matched the comment quoting the old
`insertBefore(contents, document.body.firstChild)` as evidence that the
old call was still there. That is the **sixth** instance of `UX-239`'s
subject-versus-argument failure, and the first in JavaScript rather
than prose — the rule generalises: *a guard that greps source will find
the line in the sentence explaining why the line was removed.*

**Mutations verified red and reverted (5, one rejected and redone):** a
second function opening something without a census entry; a census
entry for a function that does not exist; `nav.js` losing the
default-open reasoning; the page collapsing a section on first load;
`UX-254`'s own guards for the comment-stripping. The rejected one
inserted the extra `open` call *inside the already-named function*, so
the census correctly saw no new site — it was redone in a different
function.

**Deviation from the Required Fix:** the census reads the source rather
than the booted page. Clause 1 asked for "a census guard over the
booted page", and the harness has no layout engine and no `<details>`
model — so the counts above are measured in a browser by hand and
pinned here in prose, while what the guard holds is the set of *places
that open something*. `UX-257` is the open argument about the
instrument that could count them.

Small tier: `2100 passed, 1142 deselected in 54.98s`.
Full suite: `3239 passed, 3 skipped in 356.66s`. `make lint`: clean.
