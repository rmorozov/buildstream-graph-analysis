# UX-321: the question that can never answer, and three smaller seams

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-312 (the class it survives from), UX-308 (the contract it mis-reads) | **Serves:** R1, R2 | **Topic:** viewer | **Area:** tools

## Motivation

Round 44's verification ran seventeen mutations and all seventeen
discriminated — and still found one survivor of exactly the class
`UX-312` was filed against. **`element-commands` is structurally
dead**: it filters Plane 2 slices on `extract_arg(..., 'debug.element')`
(`bga/viewer/questions.js:141-153`), and Plane 2 slices never emit
`element` — the key is Plane-1-only in the contract
(`tools/bga_timeline.py:88-118`, `docs/spec/trace-dictionary.md:35`).
Verified on the wire: zero rows on every trace this emitter can
write, silently (`extract_arg` on an absent key is NULL, not an
error), and user-reachable — the `latent-heavies` finding drills
straight into it (`bga/provenance.py:182`). The dictionary guard
cannot see it: it checks key membership in the **union** contract,
not per-plane scope.

Three smaller seams ride along: the annotation guard's docstring
claims decoder independence its mechanism does not have (the
decoder imports the emitter's constants — only the pinned fixture
discriminates, which the Verification Log states correctly and the
docstring contradicts, `test_the_slice_says_what_bga_knows.py:153`);
`UX-312`'s progress note still calls the ui.perfetto.dev debt open
while `UX-298`'s file records it closed via `UX-314`; and the
handoff's snippet clause gates on `shutil.which` only, ignoring the
`BGA_TRACE_PROCESSOR` env var its sibling honors.

## Required Fix

`element-commands` reads a key Plane 2 actually carries (the lane
name / `debug.cmd` route, or `element` joins Plane 2's contract via
`UX-308`'s pass — decided against the dictionary, not improvised);
the dictionary guard learns **per-scope** membership so a question
keyed outside its plane's contract reddens statically; the
docstring states the fixture-pin mechanism; the two cross-file
notes reconciled; one gate helper shared by both trace_processor
clauses.

## Out of Scope

- New questions or contract keys beyond what the fix decides — the
  dictionary owns the vocabulary.

## Acceptance Test

`element-commands` returns non-empty on the committed two-plane
fixture under the real reader where available (and the in-repo
decoder always); the per-scope guard reddens on a question keyed
outside its plane (mutation: re-key it to `debug.element` → red,
statically); both trace_processor clauses use one availability
gate; the two progress notes agree.

## Log

**The survivor, and the decision it forced.** `element-commands` filtered
Plane 2 slices on `debug.element`, a key the contract gave Plane 1 only.
Zero rows on every trace this emitter can write, silently, because
`extract_arg` on an absent key is NULL rather than an error — and the
dictionary guard could not see it, because it asked whether a key is in
the **union**.

Two ways out, and the filing said to decide against the dictionary
rather than improvise. The declined one is the lane name: Plane 2's
track is labelled `native: <element> (<kind>)`, so a query could parse
its way back to the element. That is reading the *presentation* to
recover the data — the label carries the kind in brackets and is built
for a reader at a glance, while the uid is the identity the rest of the
tool joins on.

So `element` joins Plane 2's contract, which is what the question's own
`why` had claimed all along: *"Selected by the element uid both planes
carry, not by a lane name."* The rationale was right and the emitter
had never honoured it.

```text
element   Plane 1              ->  Plane 1, Plane 2
          one description shared by both, asserted equal
```

**The guard learns scopes.** `ANNOTATION_SCOPES` maps each emitted
category to the keys that ride it, `scopes_of(key)` answers the
per-scope question, and `ANNOTATION_CONTRACT` is the deduplicated union
built from them. Three clauses use it:

- a question filtering on a category must read only keys that scope
  carries — the clause `element-commands` needed and never had;
- the dictionary's `rides` column must equal `scopes_of` in both
  directions;
- and a key on two scopes must carry the **same description**, which is
  what "one key, one meaning" always meant. The rule it replaces was "a
  key rides one plane", a proxy that forbade the join outright.

**Off the wire, not asserted about the source**: every Plane 2 slice on
the committed fixture carries `element`, and each one equals the
`element` on the record it was built from. Not "Plane 2's elements are
a subset of Plane 1's" — they need not be, and on this fixture they are
not: `work-b.bst` has native processes and no Plane 1 task, which is the
ordinary shape when the wrapper log recorded no task for an element the
hook still saw. A guard asserting containment would have been asserting
a property of the capture.

**The three smaller seams.**

1. **The docstring that claimed more than the mechanism.** The
   annotation guard said its decoder was "written from the wire rules
   rather than from the emitter". It decodes the wire format by hand
   and takes its **field numbers from the emitter's own `trackevent`
   module**, so a number wrong in both places is wrong in neither. What
   discriminates is `tests/fixtures/perfetto_field_numbers.json`,
   pinned against upstream's `.proto` with a sha256 — which the
   Verification Log stated correctly and two paragraphs contradicted.
   Both corrected.
2. **The two progress notes that disagreed.** `UX-312` still called the
   `ui.perfetto.dev` debt open; `UX-298`'s file recorded it closed by
   `UX-314`. `UX-312`'s note now says what happened and who closed it.
3. **One availability gate.** `test_the_real_reader_agrees.py` honoured
   `BGA_TRACE_PROCESSOR` and `test_the_perfetto_handoff.py` did not, so
   a machine with the binary in an unusual place ran half the clauses
   that could have run — and the skip census counted the other half as
   "the tool is absent". `tests/trace_processor.py` is the one gate now,
   with the one reason string, and the handoff clause runs the binary
   the gate found rather than the one on `PATH`.

**The deviation this item inherits, restated.** Its acceptance asks
that `element-commands` "returns non-empty on the committed two-plane
fixture **under the real reader where available**". There is still no
`trace_processor` here, so the in-repo half is what ran: the key is on
the wire, on every Plane 2 slice, equal to its record's. The SQL itself
is unchanged by this fix — it was always the right query — which is why
the emitter moving is the whole of the change.

**Mutations — six, all discriminating.** Run against the committed tree,
one at a time, reverted between:

```text
Q1  element leaves Plane 2's contract      6 red   the defect, restored
Q2  the emitter declares it, never fills   3 red   off the wire
Q3  a Plane 1 query reads `debug.cmd`      1 red   the per-scope clause
Q4  the dictionary says Plane 1 only       1 red   both directions
Q5  the two planes describe it differently 1 red   one key, one meaning
Q6  the gate stops reading the env var     2 red   with the sibling scan
```

Q1 is the one worth naming: it puts the survivor back exactly as it was
and six clauses fire — the per-scope guard, the wire walk, the shared-key
census and the dictionary equality — where before, nothing did.
