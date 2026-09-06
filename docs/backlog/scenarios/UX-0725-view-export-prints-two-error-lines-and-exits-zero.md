# UX-725: `bga view --export` prints two ERROR lines and exits 0

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-326 (the tool's own sentences are contracts), UX-55 (compare's run-mode refusal) | **Serves:** anyone exporting a run whose neighbour is a different run mode | **Topic:** cli | **Shape:** judgement | **Area:** bga

## Motivation

Found by `UX-685`'s walk at seed 2, reproduced here verbatim:

```text
$ bga view @last --export verify.html; echo "exit=$?"
ERROR bga.cli: Not comparable: baseline run .../20260906T021223Z/run is a
  full run but the candidate is incremental - a noise band may only be built
  from runs of the same kind (UX-55)
Error: baseline run .../20260906T021223Z/run is a full run but the candidate
  is incremental - a noise band may only be built from runs of the same kind
  (UX-55)
Wrote .../verify.html (418 KiB). Open it with a browser - it needs no server
  and no network.
exit=0
```

Three things are wrong at once. The **same sentence prints twice**,
once as a log record and once as `Error:`. It is called an error on a
command that **succeeded** — a complete 428,044 B export was written
and the exit code is 0. And what actually happened is that one
optional section (the comparison band) had no comparable neighbour,
which `UX-388`'s vocabulary calls an absence, not a failure.

`UX-326` is the rule: the tool's own sentences are contracts. A
sentence that says `ERROR` on a run that produced its whole output
teaches a reader to ignore the word.

## Required Fix

The band's unavailability is stated once, in the absence vocabulary
(`UX-388`), on the surface the export itself carries — not as `ERROR`
on stderr. `bga compare`'s hard refusal for the same mismatch stays as
it is: `UX-55` governs a command whose whole output is the comparison,
and this one's is a page.

## Out of Scope

- `bga compare` — its refusal is correct and this item does not touch it.

## Acceptance Test

`bga view --export` on a run whose only neighbour is a different run
mode exits 0, writes the export, prints no line matching `^ERROR|^Error:`,
and the page names the band's absence. Mutation: restore the stderr
pair — the guard reds on the duplicate and on the word.
