# UX-777: the nine page-built sections are thirteen, in two documents

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-650 (the round that found the count wrong and fixed only the code) | **Serves:** the reader deciding whether chaptering belongs in the schema, on a figure that is 44% low | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

Two documents say nine. The count is thirteen, and the repository
already knows:

```console
$ grep -n 'data-section", "\|"data-section": "' \
    bga/viewer/views.js bga/viewer/element.js bga/viewer/questions.js | wc -l
13
$ grep -n "sites) >= 13" tests/unit/test_a_reader_role_demotes.py
353:        assert len(sites) >= 13, sorted(sites)
$ grep -n "nine of the forty-eight" docs/design/architecture.md
796:  viewer rather than the schema because nine of the forty-eight sections
$ sed -n '31p' bga/viewer/chapters.js
 * **Why the table is here and not in the schema.** Nine of the
```

`UX-650` (round 88) found this exact undercount and says so in its own
Outcome — *"The nine are thirteen. The list this row was filed with
came from a…"* — then fixed the code and the guard and left both
sentences standing. `architecture.md` is cited by 36 test files and
none reads this number; `chapters.js`'s docstring is read by nothing.

The sentence is not decorative. It is the argument for where the
chaptering table lives: *nine of forty-eight are page-built, so a
chaptering in `bga:question`'s neighbourhood would leave a fifth of
the document unassigned.* At thirteen it is closer to a quarter, and
the sentence a reader uses to check the reasoning is the one that is
wrong.

This is fixing-guide item 6 unguarded — "if your fix changes a number
an earlier task file presents as current, annotate that file in the
same commit" — and it is the second instance this session, after
`UX-744` left `UX-759` pointing at a vanished premise.

## Required Fix

Derive it. The construction sites are greppable and the guard at
`test_a_reader_role_demotes.py:353` already counts them, so the figure
has a source: state it once, from that source, the way `UX-549` did
for the contract registry. Both copies then read the same number or
neither does.

If a derivation is judged too heavy for a docstring, the fallback is
`UX-511`'s dated label — but say in the Outcome which was chosen and
why, because a bare corrected number is what put this here.

`forty-eight` is the other half of the same sentence and is not
checked either. Count it in the same pass.

## Out of Scope

- The chaptering decision itself — the sentence is wrong, the
  conclusion it supports is not being reopened here.
- Every other unguarded figure in `architecture.md`. Review 20 swept
  them and found this one; a general sweep is `UX-689`'s.

## Acceptance Test

Add a fourteenth construction site and watch both the guard and the
stated figure move together, or the guard red naming the document that
did not.

## Outcome

_Not started._
