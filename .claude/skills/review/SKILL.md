---
name: review
description: Read a document group against the implementation and return only what drifted - the commands that check a count, a version, a named file, a pasted block or a Part against the tree, and the shape a finding takes. Use when the review cadence guard comes due, and use before trusting any sentence in docs/ that no guard reads.
---

# review

The rule is the checklist in
[`docs/audits/architecture-review.md`](../../../docs/audits/architecture-review.md);
this is how each item is answered with a command rather than a
reading. Round 82 ran it over every document with five agents and
found one pattern: **a sentence a guard reads is exact; a sentence no
guard reads has drifted at the rate the tool moves.** So the method
is: find the unguarded sentences, and run something against each.

## 1. Which sentences does no guard read?

```bash
grep -rn "docs/<file>.md" tests/unit/*.py          # the guards that cite it, and what they assert
grep -rn "§[0-9]\|Part [0-9]\|I[0-9]\+\b" tests/unit/*.py | grep -o "…"   # the § / Part / invariant each guard names
```

Everything the document says that no citing guard asserts is the
review's subject. Start there, not at line 1.

## 2. The five checks, each one command

| the sentence claims | run |
|---|---|
| a count (files, tests, contracts, questions, modules) | `ls … \| wc -l` · `pytest --co -q \| tail -1` · `python3 -c "import bga.contracts as c; print(len(c.ids()))"` · `grep -c "^| \`" <table>` |
| a version (contract, `bst`, tool) | `grep -n "SCHEMA\|/v[0-9]" bga/schemas.py` · `bst --version` · `bga --version` |
| a file or path exists | `ls <path>` — and backticked `*.md` names too, which the link guard does not see |
| a pasted output is current | run the command it shows on the fixture it names and diff the *shape*, not the numbers |
| a spec Part / invariant is held | `ls tests/unit \| grep -i <keyword>`; `grep -ln "Part N\b\|I<n>\b" tests/unit/*.py`; then run the file `-q` |
| a document describes a workflow or config | read the yml / Makefile it describes: triggers, file lists, timeouts |

A number with a date and a command beside it is a record, not a
claim — leave it. A bare number is the finding.

## 3. Novelty before filing

```bash
git grep -l "<keyword>" docs/backlog/scenarios/    # 560+ closed rows; cite the row that touched the surface
```

## 4. The shape of a finding

`path:line` · what it says · the command that showed otherwise ·
what the fix derives from (a `UX-549`-style derivation, a `UX-511`
dated label, or a guard that reads the source the sentence copies).
A stale sentence with no derivable source is dated, not deleted.

## 5. The log

The review lands as a row in the architecture-review log (`| n | date
| closed rows at review | findings |`) and a section answering the
five checklist items — `test_the_review_has_a_cadence.py` reads the
row. A review produces filings and no code.
