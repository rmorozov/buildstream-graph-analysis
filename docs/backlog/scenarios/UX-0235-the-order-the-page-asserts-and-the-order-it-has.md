# UX-235: the order the page asserts, and the order it has

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-207, UX-216, UX-221 (the guards it repairs) | **Serves:** the maintainers; R1 indirectly | **Topic:** guards

## Motivation

Round 27's verification ran twenty-two mutations; twenty reddened.
The two that stayed green, plus one skip semantics seam:

1. **The decision panel's order guard is a tautology.** The
   acceptance said "DOM order asserted"; the harness builds the
   expected order as a hardcoded literal over three separately
   invoked renderers and never reads `boot()`'s insertion — so
   `root.prepend(decision)` mutated to `append` leaves
   `test_the_decision_comes_before_the_evidence` green. The same
   class holds for `UX-221`: "culprits above the band" is asserted
   for the *text* report and unguarded on the page.
2. **The anchor-equality probe set has an underscore gap.**
   `cssId` re-duplicated with `[^A-Za-z0-9-]+` — differing from
   `[^\w-]+` only on `_` — survives every guard, and `my_lib.bst`
   gets a link that misses its target. The probe uids simply
   contain no underscore.
3. **"Runs on a fresh clone" quietly means "plus dev extras".**
   The jsonschema-dependent guard files `importorskip` at module
   level, so a plain `pip install -e .` collapses whole files to
   "1 skipped" — CI installs `[dev]` and is covered, but the
   fresh-clone claim several logs make is one extras-flag wider
   than it sounds.

## Required Fix

Page-order guards that read the booted document's actual node
sequence (the two named sites, and the pattern documented so the
next "X above Y" claim ships with a real order assertion); an
underscore-bearing uid in the anchor probe set; and the skip made
loud — a conftest-level marker that counts module-level skips and
one canary asserting the expected number, so a vanished guard file
is a red line rather than a quieter green.

## Out of Scope

- New ordering behavior (both orders are correct today; only the
  guards are hollow).
- Making jsonschema a hard dependency (dev-only stays; the claim
  gets honest instead).

## Acceptance Test

`prepend`→`append` on the decision panel reddens; moving the
culprit strip below the band reddens; the `[^A-Za-z0-9-]`
re-duplication reddens on the underscore probe; deleting a
jsonschema-guarded test file (or its extras) fails the canary
rather than skipping silently.

## Outcome (round 28)

All three seams reproduced before anything changed, and the reproduction
found two more.

**Seam 1, exactly as filed.** `prepend`→`append` on the decision panel:
26 passed before the mutation, 26 passed after. The harness built
`order` as `[panel && "decision", evidence && "evidence", overview &&
"overview"]` — the source order of three function calls, which no
change to the page can move.

**A fourth defect, unfiled, and the reason the first three survived.**
The only harness that boots the real exported page implemented:

```js
prepend(...xs) { this.append(...xs); },
```

So everything the page puts *first* landed *last*. Booted through it,
the real order read `summary, run_instance, findings, …, overview,
evidence, decision` — the exact reverse of UX-207's promise. **The page
was never wrong; the instrument was**, and no order guard written
against that probe could have meant anything. With a real `prepend` the
same page reads `decision, evidence, overview, summary, …`.

The guards read that sequence now. For the culprit strip, which needs a
comparison the export does not inline, a `compare/v1` block is spliced
into the page and `load()` finds it before it tries the network — so the
real `boot()` path renders both, rather than a stub of it.

**A fifth defect, also unfiled, and it is mine.** Chasing seam 3 turned
up `tests/unit/test_publish_the_join.py:27` — a module-scope
`pytest.importorskip("jsonschema")` I added in round 25, hiding
twenty-one guards behind one import. Round 21's seam-6 guard exists to
ban exactly that, and missed it because it named **one file** to look
in. A guard written for the instance rather than the class is how the
class comes back. It reads every test file now, and the file was
converted to a method-level `skipif` — six tests skip without
`jsonschema`; the other fifteen still run.

### The skip census, and how its own first draft was hollow

`BGA_EXPECT_DEV` already turns the jsonschema case red *in CI*, which
sets it. It is opt-in, so a fresh clone is silent, and it knows about
one library. The census is the general form: every skip tallied by
reason, checked at session end — a reason that is undeclared, or one
accounting for more than eight tests, fails the session.

Its first draft gated on `session.config.option.file_or_dir`, **which
does not exist on pytest 9**. The hook raised, the census never ran, and
a full run with `jsonschema` genuinely blocked reported 81 skips and
said nothing. It was written, it looked right, and it measured nothing —
the same shape this whole item is repairing, found the only way such
things are found: by running it against a real absence and checking the
complaint actually appeared. With `config.args`:

```text
31 tests skipped for one reason ("jsonschema is not installed …") -
more than 8. That is a whole guard file going quiet.
```

On its first honest outing the census also surfaced three *undeclared*
reasons — UX-213's real-capture arm — which are legitimate and had
simply never been named. They are declared now, which is the census
doing its job rather than a fault in it.

**Mutations verified red and reverted:** `prepend`→`append` on the
decision panel (2 guards — the acceptance's first, and the one that was
green); the culprit strip moved below the band (1 — its second);
`cssId` re-duplicated as `[^A-Za-z0-9-]` (1 — its third, caught by
`my_lib.bst`, added to the probe set); the shim's `prepend` reverted to
`append` (8 — the whole order suite); a module-scope `importorskip`
re-introduced (1, on the generalised seam-6 guard); `jsonschema` blocked
on a full run (the census, the acceptance's fourth).

Full suite: 2984 passed, 3 skipped, census quiet.

**Deviation from the Required Fix:** none. The pattern is documented in
the fixing guide's Definition of Done as item 7, with both generalised
rules — read the order the page has, and a guard that names one file
will not see the second one.
