# UX-782: the register derives its rounds from `git log`, which is a property of the clone

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-781 (which stopped CI cutting it), UX-772 (the datelines this would read) | **Serves:** the round whose register disagrees with itself on a second machine | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`rounds()` takes its population from commit subjects reachable from
`HEAD`, plus the ledger's round column. Reachability is a property of
the clone, so the register's answer is too — `UX-776` and `UX-781` are
both that fact arriving as a red CI job.

Both are now closed at the level of "stop cutting the history", and
the derivation still rests on a source that a shallow clone, a
graft, a rebase or a squash-merge changes. Measured on this branch:

```console
$ derived from git log : 71     # varies with the clone
$ round documents      : 63     # identical in every checkout
$ ledger rounds        : 16
$ committed union      : 63
$ git-only, no document and no ledger row:
    26 29 31 47 48 50 52 53 55 58 60 67 69
$ committed but absent from the git derivation:
    2 3 4 5 6
```

Thirteen rounds exist only as a commit subject; five exist only as a
document. Neither source alone is the register, which is why this is a
design question and not a one-line swap.

## Required Fix

Decide, and state the decision in this file before writing code:

1. Whether the register's **population** becomes the committed union
   (documents ∪ ledger), with the thirteen git-only rounds given a
   document or accepted as lost.
2. Whether its **dates** come from `UX-772`'s datelines rather than
   `max(commit date)`. If they do, the guard comparing the two becomes
   tautological and must be replaced by something that still fails —
   otherwise this trades a clone-dependent answer for an unfalsifiable
   one, which is worse.

(2) is the trap in this row. Do not close it by making the register
read the document and the guard read the register.

**Decision:**

1. The population becomes the committed union: every round document
   plus every round the runs ledger carries a row for. The thirteen
   git-only rounds (`GIT_ONLY_ROUNDS`, frozen at 26 29 31 47 48 50 52
   53 55 58 60 67 69 — this Motivation's own measurement) are accepted
   as lost, not chased with `git log`; the register's header states
   their count and range, derived from that frozen list
   (`len()`/`min()`/`max()`, not typed). `git log` is not consulted
   for the population at all.
2. The date comes from `document_date()` — `UX-772`'s dateline — never
   `max(commit date)`. A round with no dateline reads an empty cell,
   stated as such, never a proxy. Because the register's date is now
   the same read as `document_date()`, comparing them is tautological;
   the replacement guard compares the dateline against
   `first_commit_date()` — the date `git log --diff-filter=A` gives
   for the document's own path, independent of what the document
   says — and skips, naming the depth, on a shallow clone
   (`is_shallow()`, unchanged, Out of Scope).

## Out of Scope

- `is_shallow()`'s refusal. It stays whatever this decides: a
  truncated history should refuse rather than answer, independently of
  what the derivation reads.

## Acceptance Test

```console
$ python3 tools/dev_round_register.py --write && \
  python3 tools/dev_round_register.py --check   # exit 0
$ python3 -m pytest tests/unit/test_a_run_is_priced.py \
    tests/unit/test_the_round_register_is_derived.py -q
```

`TestARegisteredRoundsDateMatchesItsDocument` is the clause that fails
when the date source and the comparison source are the same file: it
compares `document_date()` against `first_commit_date()`, an
independent read of `git log`, not against the register's own date
(which is `document_date()` by construction and would make the check
tautological). Mutation: make `first_commit_date()` return
`document_date()`'s own value — the comparison passes vacuously on
every round, which the guard's mutation table below catches by
naming the row that no longer discriminates.

## Outcome

### The gap, measured

```console
$ python3 tools/dev_round_register.py --write   # before this row
$ diff <(git show HEAD:docs/audits/round-register.md) docs/audits/round-register.md | wc -l
72   # every row's header text and 66 date cells changed shape
```

Population: 66 documented rounds (glob) union 19 ledger rounds, all
already documented — the committed union is 66, not the 71 `git log`
derived on this branch nor the old 63. Round 64 (previously excluded:
"its naming commit is not on this history", `UX-772`'s Deviation) is
now in, dated `2026-08-29` from its own document. Rounds 2-6 (moved
out of `directions.md`, no commit ever named them) are now in too,
with an empty date cell (`NO_DATELINE_WAIVER`).

### The close, measured

```console
$ python3 tools/dev_round_register.py --write && \
  python3 tools/dev_round_register.py --check
wrote docs/audits/round-register.md
$ echo $?
0
$ python3 -m pytest tests/unit/test_a_run_is_priced.py::TestARegisteredRoundsDateMatchesItsDocument -q
68 passed
$ python3 -m pytest tests/unit/test_a_run_is_priced.py tests/unit/test_the_round_register_is_derived.py -q
128 passed
```

Rounds 19 and 22, waived under the old commit-subject mechanism, now
match `first_commit_date()` cleanly and carry no waiver. Rounds
99-102 (all four, not just 101) now need `DATE_MISMATCH_WAIVER`: each
`docs/audits/round-N.md` was itself added by `UX-757`'s retroactive
commit on 2026-09-07, a day after the dateline it states
(2026-09-06) — a real, independent-source discrepancy the old
register-vs-document comparison could not see, because that
comparison was never independent of the document once the register's
date became the document's own dateline.

### Mutation table

| # | mutation | reddened |
|---|---|---|
| M1 | `docs/audits/round-103.md`'s dateline moved one day (09-07 → 09-08), in a copy | `test_a_documents_dateline_matches_its_own_first_commit[103]`, naming both dates (`2026-09-07` git vs `2026-09-08` stated) |
| M2 | `first_commit_date()` collapsed to return `document_date()` (the named trap: same source on both sides) | 4/128: the four `DATE_MISMATCH_WAIVER` rows (99-102), each now asserting a mismatch that no longer reproduces. Confirmed separately: with M2 *and* M1 stacked, the guard passes — proving the collapse is what the Required Fix warned against, not a false alarm |
| M3 | `ROUND_DOC_RE` narrowed to match only `round-register.md` (no capture group) | 2/22: both `TestDocumentedRoundsReadsFilenames` cases, one an `IndexError` |
| M4 | `rounds()`'s union dropped the ledger side (`set(docs)` only) | 1/22 fixture (`test_a_ledger_only_round_has_no_dateline_to_read`); the real-repo subset guard did not catch it — every ledger round already has a document, so nothing here discriminates that specific mutation against live data |
| M5 | `shallow_depth()` hard-coded 0 | 1/22 (`test_the_markers_own_entries_are_counted`) |

**Guard that did not discriminate**: `first_commit_date()`'s
`--diff-filter=A` flag is redundant to current behaviour, since
`out[-1]` already takes the *oldest* `git log` line for the path
regardless of filter, and no fixture here creates a delete-then-readd
history where the two would differ. Kept because the Required Fix's
guard text names it explicitly and it states the intent (first
*added*, not first *touched*) even where today's data can't tell the
two apart.
