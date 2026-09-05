# UX-660: one sentence, two line numbers, and only one of them is guarded

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-556 (which wrote the sentence), UX-584 (which required the process layer's figures to be derived or dated) | **Found by:** round 89, track Y, when adding a line to Part 32 moved both figures | **Serves:** anyone following item 12 to the sentence it points at | **Topic:** docs | **Shape:** judgement

## Motivation

`fixing-guide.md` item 12 carries two line numbers in one sentence:

> the sentence is at line 1673 and Part 32 spans 1515-1941

`Part 32 spans` is read by
`test_the_spec_outside_part_32_is_read_only.py` and by
`test_the_process_documents_derive_their_figures.py`. `the sentence is
at line` is read by nothing. Traced over every commit that touched the
guide, against where the sentence actually sits:

```console
$ python3 scratchpad/drift.py
commit    date        says   actual   drift
003ba92   2026-09-03  1671   1671
812fe74   2026-09-03  1671   1671
ff3e08e   2026-09-03  1671   1671
5343bd6   2026-09-04  1671   1671
c6193ea   2026-09-04  1671   1672     <-- drifted
...
74fbeac   2026-09-04  1671   1672     <-- drifted
c571299   2026-09-04  1673   1673
```

Thirteen commits carried it wrong. And the commit that broke it is the
finding, because it moved the *other* figure on the same line correctly:

```console
$ git show c6193ea -- docs/contributing/fixing-guide.md \
      | grep -oE "(Part 32 spans [0-9-]+|sentence is at line [0-9]+)" \
      | sort | uniq -c
      1 Part 32 spans 1515-1939
      1 Part 32 spans 1515-1940
      2 sentence is at line 1671
```

`UX-613` added a line to Part 32. Both figures moved by one. The
session updated the guarded one — because a guard was red — and left
the unguarded one alone, in the same edit, in the same sentence. It was
not carelessness about the sentence; it was a guard doing exactly what
it does and nothing telling anyone about its neighbour.

`c571299` (`UX-659`, this round) moved the sentence again and corrected
both, because a figure that commit moves is that commit's to fix. That
is the repair of one instance, not of the arrangement.

## Required Fix

The unguarded figure stops being a figure a tree can move past. Either
item 12 stops naming a line number for the sentence — it already names
the sentence's own words, which is how a reader finds it — or the
number is derived the way the span is, by the guard that already reads
this file for the span.

Deciding between them is a measurement, not a preference: `UX-584`'s
rule for the process layer is *derived or dated*, and
`test_the_process_documents_derive_their_figures.py` is where the span
is derived. If the sentence's line is cheap to add there, it is one
more derived figure; if it is not, the sentence loses the number and
keeps the quotation.

## Out of Scope

- The span figure and its two guards — both correct at this commit, and
  this row is about the figure beside it rather than the one that works.
- Every other line number quoted in a process document. Declined
  because the population has not been measured, and a sweep would want
  it derived rather than grepped, which is a different row.
- `test_a_retired_line_holds_retired_ids_only`, whose converse
  direction `UX-659` left keyed on the note's prefix: same file, its
  own row, and it is about liveness rather than a figure.

## Acceptance Test

Item 12 carries no line number the tree can move past, or carries one a
guard reddens on. Mutation: adding a line inside Part 32 above the
sentence reddens the guard naming the figure, exactly as it already
reddens the one naming the span.

## Outcome

🟢 Done. The number is derived, not dropped.

**The decision was a measurement, as the row asked.** The choice was
"derive it or lose it, whichever is cheaper", and the words item 12
points at — *written but not printable* — appear **once** in the whole
spec:

```console
$ grep -c "written but not printable" docs/spec/specification.md
1
```

One match is an unambiguous anchor, so `_registry_sentence()` is six
lines beside `_part_32()`, which was already deriving its neighbour on
the same sentence. Deriving cost less than deleting would have, and the
reader keeps the number.

`test_the_process_documents_derive_their_figures.py` now derives both
halves of the sentence. The helper raises rather than guesses if the
anchor ever stops being unique — a silent `[0]` would have re-created
this row's own defect one layer down.

### Acceptance

The mutation the row names: one line added inside Part 32 above the
sentence.

```console
$ python3 - <<'EOF'   # insert a line at 1660
...
EOF
$ python3 -m pytest tests/unit/test_the_process_documents_derive_their_figures.py
E   assert not ['the sentence is at line 1674', 'Part 32 spans 1515-1942']
1 failed, 22 passed
```

**Both** figures are named in the failure. Before this commit the same
mutation named only the span — which is exactly how `UX-613` moved one
and left the other.

### Mutations

| mutation | guard |
|---|---|
| a line added inside Part 32, above the sentence | names both figures, not one |
| (control) the tree unmutated | 23 passed |

### Deviation

None. The row offered two doors and a rule for choosing between them;
the rule chose, and the cheap door was the one that keeps the number.
