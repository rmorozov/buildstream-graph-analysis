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

## Out of Scope

- `is_shallow()`'s refusal. It stays whatever this decides: a
  truncated history should refuse rather than answer, independently of
  what the derivation reads.

## Acceptance Test

To be written with the decision. It must include a clause that fails
when the register's date source and its comparison source are the same
file.

## Outcome
