# UX-400: every population is tested at zero, one and many

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-388 (what zero does today), UX-367 (what many did until the sweep held it) | **Serves:** every future section, before its bug is filed | **Topic:** guards

## Motivation

The escape ledger for population-shape bugs is now three entries
long, and each was found by an audit round rather than the suite:

- **zero**: six sections vanish without a word on an incremental run
  (`UX-388`, found only because round 63 ran the cycle twice);
- **one**: superlatives and labels written for populations read wrong
  over a single row (`UX-365`'s class);
- **many**: the volume budget was unheld at the size people build at
  until the capacity sweep found it (`UX-367`).

Each class was fixed *where it was seen*. Nothing asserts the next
section handles all three, so the next section ships the same three
bugs — the suite tests sections on the populations their fixtures
happen to have.

## Required Fix

A parametrized sweep in the browser tier: for every section the
chapters registry knows, render the page against a payload where that
section's population is (a) empty, (b) one row, (c) the capacity
sweep's large size, and assert the section's contract at each point —
present-and-saying-empty at zero (`UX-388`'s rule once it lands), no
plural/superlative lies at one, within the volume budget at many.
`tests/degenerate_store.py` already builds degenerate payloads; this
sweep drives it per-section instead of per-filing.

## Out of Scope

- Fixing what the sweep finds on its first run — each real failure is
  its own filing; this task builds the instrument.
- Plane 2 capture-side populations — `UX-375` bounded the unbounded
  one; this sweep is about what the page does with what arrives.

## Acceptance Test

- The sweep runs in the browser tier and enumerates every registered
  section (guard: the enumeration count equals the chapters
  registry's count, so a new section cannot dodge it).
- Falsification: revert `UX-388`'s fix (once landed) — the zero leg
  must go RED; cap one budget clause — the many leg must go RED.
