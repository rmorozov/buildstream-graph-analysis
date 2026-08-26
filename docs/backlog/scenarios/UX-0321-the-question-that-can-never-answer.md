# UX-321: the question that can never answer, and three smaller seams

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-312 (the class it survives from), UX-308 (the contract it mis-reads) | **Serves:** R1, R2 | **Topic:** viewer

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
