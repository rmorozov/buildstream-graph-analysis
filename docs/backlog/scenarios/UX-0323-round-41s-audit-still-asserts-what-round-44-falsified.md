# UX-323: round 41's audit still asserts what round 44 falsified

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Serves:** R2 — whoever reads an audit to find out what was true | **Topic:** docs

## Motivation

`docs/audits/round-41.md`, line 86, unqualified:

```text
- **The export ships the source commentary.** `UX-303` took the page
  from 183 KB to 197 KB and tripped `UX-287`'s data-dwarfs-the-page
  ratio at 3.90x. 175 KB of the 196 KB page is commented JavaScript,
  because `--export` inlines modules verbatim. Filed as `UX-307`
  rather than absorbed.
```

**Both halves of the mechanism are false.** `--export` does not inline
modules verbatim: `_uncommented` in `tools/bga_view.py` has stripped
comments from the inlined copy since `UX-205`, and its own docstring
records the 79,180 → 52,870 B that bought. So 175 KB of the page was
never commented JavaScript.

`UX-320` (round 44) measured it and said so — 89% code. `UX-307`
(round 45) measured what was actually left and removed it: **153 B**,
four trailing comments, 0.069% of the page.

Nothing in `round-41.md` says any of this. A `grep` for the annotation
finds one unrelated line.

The claim is not inert. It is the stated reason the `UX-287` ratio
threshold was lowered from 4x to 3.5x, and that threshold has since
moved again to 3.3x — twice restated against a cause that was
misattributed both times. The audit record is where it originated and
is the one place still asserting it without a marker.

## Required Fix

`UX-132`'s rule, applied: annotate the figure in place rather than
rewriting history. The paragraph keeps what round 41 believed and
gains a sentence naming the round that falsified it and the real
measurement.

Then the general question, which is the more useful half: `git grep`
the other audit rounds for figures a later round moved. This one was
found by reading, not by a tool, which is not a method.

## Out of Scope

- Rewriting round 41's conclusions. It filed `UX-307`, which was the
  right call, on a wrong mechanism.
- `UX-307` and `UX-320`'s own files: both already carry the
  correction.

## Acceptance Test

`round-41.md`'s paragraph names the round that falsified it and the
measured figure; a search of `docs/audits/` for figures later rounds
moved is run and its result stated, whether or not it finds a second
one.

## Outcome (round 46, 2026-08-26) — 🟢 Done

### The annotation

`docs/audits/round-41.md` keeps its paragraph and gains a block quote
under it, per `UX-132`: the claim is **not** rewritten. The annotation
says what round 44 falsified, what round 45 measured (153 B of a
223,227 B page, 0.069%), and the thing that makes this different from
an ordinary superseded figure — it was wrong **when it was written**,
not overtaken later. `_uncommented` had been stripping comments for
twenty rounds by then.

It also records the consequence, which is the reason the item was
filed above Low-and-forget: the false mechanism is the stated reason
`UX-287`'s ratio threshold went 4x → 3.5x, and the threshold has since
moved again to 3.3x against the same misattribution both times.

### The sweep the Required Fix asked for

"`git grep` the other audit rounds for figures a later round moved.
This one was found by reading, not by a tool, which is not a method."
Run over all 28 audit rounds, looking for page/export/module sizes:

```text
audit rounds on file                             28
distinct byte/size figures quoted across them    48
page-or-export sizes stated in the present tense  3

round-22.md:14   the page is 39,119 bytes
round-23.md:21   the page itself 68,087 B against the 80,000 B ceiling
round-27.md:30   the page stands at 123,785 B
```

The page is 223,074 B today, so all three are superseded. **They are
deliberately left alone**, and the distinction is the finding:

> A dated measurement that was true when taken is not the same defect
> as a mechanism that was never true.

Each of those three is anchored to its round, in a document whose whole
purpose is to record what that round saw. Annotating them would mean
annotating every measurement in every audit the moment the number
moved, which turns the audit log into a changelog and destroys the
thing it is for. Round 41's sentence is annotated because it asserts a
*mechanism* — "`--export` inlines modules verbatim" — that the code
did not have, and a reader has no way to date that claim from the page.

### Deviation from the Required Fix

- The Required Fix hoped the sweep would become "a method" rather than
  a reading. It has not: the sweep found the three above by pattern,
  but deciding that they are fine and round 41's is not was still
  judgement. What this round can honestly claim is that the *search*
  is now recorded with its result, so the next reviewer starts from
  three known-and-declined figures rather than from nothing. Making
  the distinction mechanical would need audits to mark which of their
  numbers are measurements and which are mechanisms, which is a
  filing-sized change and not this item's.
