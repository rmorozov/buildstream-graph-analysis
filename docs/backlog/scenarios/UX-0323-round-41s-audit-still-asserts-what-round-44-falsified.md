# UX-323: round 41's audit still asserts what round 44 falsified

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R2 — whoever reads an audit to find out what was true | **Topic:** docs

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
