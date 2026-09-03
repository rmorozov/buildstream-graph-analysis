# UX-578: the verbatim blocks that are neither dated nor fresh

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-139 (verbatim is evidence), UX-511 (the dated block), UX-492 | **Serves:** anyone diffing a guide's output against their own | **Topic:** docs

## Motivation

Five pasted outputs in the guides drifted from the tool without a
label saying so:

```text
cli.md:293-297     bundle --no-plane2       tool now lists "plane2.json, plane2.log.gz" and prints "load it with:"
real-project.md:685 correlate block        starts at PARTIAL ATTRIBUTION; the banner, Run/Instance, memory envelope and
                                            "Restructuring opportunity" precede it in a fresh run — no cut marker
cli.md:658/666 vs :1428 + guide L177        486,167 B and 491 KB for the same 16,832-track seeded trace (UX-430 vs UX-446)
what-the-viewer-answers.md:80               "the declared graph, in `structural`" — analyze/v5 has no such namespace (UX-344)
what-the-viewer-answers.md:41               element_join[].peak_rss_kb — absent on the macro_micro fixture's element_join[0]
```

`test_the_readme_block_is_the_real_output.py` diffs the README's
block against a fresh run; nothing does that for `cli.md` or
`real-project.md`.

## Required Fix

Every ` ```console`/` ```text` block introduced by `$ bga …` in
`docs/guides/` is either diffed against a fresh run on the fixture it
names (the README guard, generalised) or carries the dated
"kept, not current" label with its cuts listed (the `UX-511` shape).
The five above corrected or labelled; the two byte figures reconciled
to one measurement with its round.

## Out of Scope

- Blocks from real projects nobody can re-run (`ci-comment.md:79`) —
  labelled, not diffed.

## Acceptance Test

Mutation: change one line of a diffed block — red; remove a kept
block's label — red.
