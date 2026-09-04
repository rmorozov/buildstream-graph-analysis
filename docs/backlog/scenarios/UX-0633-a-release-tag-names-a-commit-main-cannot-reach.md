# UX-633: a release tag names a commit `main` cannot reach

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-597 (which declined this tag), UX-637 (which explains why this row is wrong) | **Found by:** round 86, closing UX-597 | **Serves:** anyone checking out a release this repository claims to have made | **Topic:** docs

## Motivation

**This row's premise is false, and the file is kept as the record of
how.** What it said:

> All three release tags now exist on the remote. Two are what the
> release guide asks for; the third is not. `v0.2.0` names `3ebe7e1b5`,
> a commit on a lineage `main` never merged, so `git checkout v0.2.0`
> hands the reader a tree that is not an ancestor of anything shipped.

Measured on a full history, every clause of that is wrong:

```text
tag      commit      pyproject version   ancestor of main
v0.2.0   3ebe7e1b5   0.2.0               yes
v0.3.0   bc1593557   0.3.0               yes
v0.4.0   679b9cf87   0.4.0               yes

$ git log --diff-filter=A --format='%h %ci' -- pyproject.toml
4ace856 2026-08-13          # not bc15935, which this row asserted
$ git rev-list --max-parents=0 origin/main
f706049 2026-08-12 Initial commit          # one root, not two
```

The clone this row was filed from was **shallow** (`UX-637`). Its
history stopped at a boundary that included `bc1593557`, which
therefore looked like a root, which made `3ebe7e1b5` look like a
disjoint lineage. CI, which sets `fetch-depth: 0`, said the tag was
reachable on four separate runs. CI was right each time.

## Required Fix

**None. There was no defect.** `v0.2.0` is a release tag on a commit
that sets its version and is reachable from `main`, exactly like the
other two.

What this row actually produced, and what to read instead:

- `UX-637` — the real defect: a shallow checkout answers reachability
  from a truncated history and says so to nobody.
- `UX-597` — its Outcome is corrected; the guard's version floor still
  came out, which was right for its own reason.

## Out of Scope

- The `0.3.0` and `0.4.0` tags — correct, and never in question.

## Acceptance Test

Superseded by `UX-637`'s: a `--depth 20` clone with tags fetched must
make the reachability clause decline rather than answer.

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise falsified.** Closed as *no defect*, and the file rewritten
rather than deleted, because the sequence is the lesson.

### What it cost

| | |
|---|---|
| a filed row | this one |
| a decision put to the repository's owner | keep the tag, or delete it, or re-point it — on a false premise |
| a shipped mechanism | `UNREACHABLE_BY_DECISION`, an exemption for a tag needing none |
| CI runs | 4, red on the clause that was right |
| documents made wrong | `UX-597`'s Outcome, `CHANGELOG.md`, `round-86.md`, `directions.md` |

### The two wrong turns, in order

**First**, four measurements agreed with each other and none of them
questioned the clone. `rev-list`, `merge-base`, `--is-ancestor` and
`for-each-ref` all read the same truncated history, so four
confirmations were one observation.

**Second**, when CI disagreed I reached for the difference I could
*see* — git 2.43 here against 2.55 there — and wrote it up as a version
bug, with a table, in the round document. It was a plausible story
built to fit, and building it delayed asking the cheaper question:
*what is different about my repository?* One `git rev-parse
--is-shallow-repository` would have ended it at the start.

### Deviation from the Required Fix

The Required Fix is now "none". Everything this row shipped is undone
except the version floor's removal, which `UX-597` keeps on its own
merits: reading every release row is right whether or not any of them
needs an exemption.
