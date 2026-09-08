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

### The gap

`_sites()` — the same population `test_a_reader_role_demotes.py:353`
already parses over `views.js`/`element.js`/`questions.js` — counts
**14**, not 13:

```console
$ python3 -c "..."  # _sites() over the three built-in modules
14
```

The Motivation's own grep undercounts by missing a dynamic key:
`element.js:577`, `section.setAttribute("data-section",
elementAnchor(uid))`, has no literal string after the comma, so
`'data-section", "'` never matches it. `UX-650` (round 88) counted
13; `views.js::renderBandUnavailable` (line 214, `data-section:
"band"`, R4) was added after that round and is the 14th — drift the
"thirteen" this row was filed to write down had already caught up to.
`forty-eight` is a dated measurement (round 39, `UX-286`) of a
specific synthetic-run DOM, not a static population; re-deriving it
needs a browser render, which `test_the_report_has_chapters.py`'s own
docstring carries unguarded too. The verifier's DOM census confirms
the population, not just the figure: macro_micro's rendered page
carries 68 `data-section`s (published + page-built), the wrong count
for "page-built" — `_sites()`'s 14, over the three built-in modules
alone, is what the sentence names. Chosen: derive the page-built count
from `_sites()`; leave `forty-eight` as the round-39 figure it already
is, its round and id now stated beside it in `chapters.js`.

### The close

Both documents state `fourteen`. `chapters.js` no longer types a
fraction beside it (`over a quarter` was a figure the guard cannot
see, in the shape this task was filed against) — the dated `forty-eight`
now carries its round and id inline, one line: `` (`UX-286`, round 39) ``.
The word itself is built, not tabled: `dev_track_cost.count_word`
(`tools/dev_track_cost.py`, imported the way
`test_a_counted_figure_is_derived.py` does), so a count past a fixed
dict's range still reddens legibly rather than raising `KeyError`.

```console
$ grep -n "Fourteen of the\|forty-eight sections on" bga/viewer/chapters.js
31: * **Why the table is here and not in the schema.** Fourteen of the
32: * forty-eight sections on the synthetic run (`UX-286`, round 39) are
$ python3 -m pytest tests/unit/test_a_reader_role_demotes.py -q
21 passed in 2.84s
$ make lint
clean: 568 finding(s) match tests/quality_baseline.json; 281/1/2/1 forced
(UX-697/UX-744/UX-762/UX-781)
```

The guard is two clauses in `TestThePageBuiltCountIsDerivedInBothDocuments`,
beside the existing count at `test_a_reader_role_demotes.py:353` (not
`test_the_process_documents_derive_their_figures.py` — its population
is `.claude/**.md` and `docs/contributing/*.md`), reusing `_sites()`
rather than a second population. `architecture.md`'s prose edit is
substantive (`only_the_count_moved` does not excuse it), so it
re-anchors the document's Verification Log in the same commit — a new
`Updated 2026-09-08 (after UX-777)` entry. `test_the_verification_log_is_true.py`:
31 passed.

### Mutations, red then reverted

| # | mutation | reddened |
|---|---|---|
| M1 | `chapters.js`: `Fourteen` → `Fifteen`, population unchanged | 1 (chapters.js clause only) |
| M2 | `views.js`: `renderBandUnavailable`'s `data-section` site removed | 2 (both documents' clauses, together) |
| M3 | `views.js`: 5 stub sites appended (14 → 19, past the old dict's 9–18 range) | 2, message names `'nineteen'` in both — `count_word` built it, no `KeyError` |

Restored from the scratchpad copy each time; `test_a_reader_role_demotes.py`
green (21 passed) after each revert.
