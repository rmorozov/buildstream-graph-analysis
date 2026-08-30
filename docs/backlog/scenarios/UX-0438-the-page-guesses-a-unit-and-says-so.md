# UX-438: the page guesses a unit on a real capture, and says so on the console

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 69, strand (b) — pressing all 468 controls on a real capture | **Serves:** every reader, and the next round that trusts a clean console | **Topic:** contracts

## Motivation

Booting the export of a real capture of `examples/06` and pressing every
control produced exactly one console message:

```text
bga: transfer_share has no bga:quantity; guessed share
```

The page is name-sniffing. §1a's rule is the one being broken:

> **A hint is a declaration, never a guess**: the page reads what the
> schema says a value is and falls back to name-sniffing only where the
> schema says nothing, which is a schema gap rather than a feature
> (`UX-201`).

And the quantity is not missing from the repository — it is declared:

```text
bga/schemas.py:1413
    "transfer_share": ("share",
        "Artifact transfer as a share of wall-clock."),
```

So the table knows the unit and the value still arrives without it.
The likely reason is the path it travels: `transfer_share` is written
into a **finding's `evidence`** —

```text
bga/findings.py:451
    evidence={'transfer_share': share, 'transfer_us': transfer},
```

— and an evidence map is a free-form object, so the property carries no
hint even though the name is in the quantity table. That is a
hypothesis the item must confirm; it is not established here.

**Why nothing caught it.** `UX-334` gave the page a clean-console
guard, and the console is clean on the committed fixtures. This warning
needs a capture with artifact transfer in it, which the fixtures do not
have — the same shape as the rest of this round: **a real capture says
things the fixtures cannot.**

`transfer_us` sits beside it in the same map and is presumably in the
same position; the sweep saw only one warning because only one value
was rendered.

## Required Fix

- **Establish the path**, then close it where it actually breaks:
  either evidence maps carry hints for the keys the quantity table
  already names, or the value is published somewhere schema'd and the
  evidence map references it.
- **Check the whole map, not the one key that warned.** A warning per
  rendered value means the count of warnings measures what was drawn,
  not what is undeclared.
- **The clean-console guard runs against a capture that has transfer
  data.** A guard whose fixture cannot produce the finding is one whose
  setup excludes what it tests, which this repository has now seen nine
  times.

## Out of Scope

- **The name-sniffing fallback itself**: it exists deliberately so a
  gap degrades rather than crashes (`UX-201`), and this item fills a gap
  rather than removing the net.
- **The other 467 controls**: all pressed, none threw, none raised a
  window error — recorded in the round's notes and needing no item.
- **`UX-334`'s guard rewrite** beyond giving it a capture that can
  produce this warning.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga view @last --export /tmp/report.html
```

Boot it, press every control, and the console stays empty. A mutation
removing `transfer_share`'s quantity declaration must redden the guard.

## Outcome

_Not started._
