# UX-766: the forced baseline is loud only until it is committed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-745 (which built the visibility) | **Serves:** the session reading `make lint` and believing the baseline did not grow | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-745` found that a track could authorise its own baseline growth
with every gate green, and chose visibility over refusal — its Outcome
says so: *"Making the growth loud in the output the session reads
discriminates where a self-declared reason does not."*

The loudness does not survive the commit that carries it.
`gained_since_head` compares the working tree against `HEAD`. While
the forced entry is uncommitted the two differ and `--check` prints
`authorised by UX-NNN, red until committed`. Once committed they are
identical, and the same command says:

```console
$ python3 tools/dev_baseline.py --check
clean: 293 finding(s) match tests/quality_baseline.json
```

Round 105 walked into it. `UX-762`'s track ran `--force --reason
UX-762` for two `S607` entries and committed them; `make lint` is
green and silent, and its verifier found the growth only by reading
`git diff tests/quality_baseline.json` by hand. `UX-745`'s own
motivating example is a track doing exactly this.

So the safeguard works for the author, in the minutes before they
commit, and for nobody afterwards — not the reviewer, not CI, not the
next round. The one reader it was built for is the one it does not
reach.

## Required Fix

Make an authorised growth legible **after** it lands. The baseline
already records `forced` and `forced_by`; nothing reads them back. The
cheapest honest route is a guard that reports every forced entry still
present, so a session sees the standing count rather than a silence —
the shape `UX-745` chose, extended past the commit boundary.

Then decide the follow-through `UX-745` deferred: whether a forced
entry that outlives its own row's close is a debt with a name, or
stays indefinitely.

## Out of Scope

- Refusing a track the ability to force — `UX-745` considered and
  declined that ("Route two ... was **declined**"), and this row does
  not reopen the decision, only its stated visibility.
- The two `S607` entries `UX-762` added — they are the same
  `subprocess.run(["git", ...])` shape already baselined for six other
  tools, and correct on their merits.

## Acceptance Test

A committed forced growth is visible in the output a session reads,
not only in a hand-read diff. Mutation: force an entry, commit it, and
confirm the check names it where today it prints `clean`.

## Outcome

_Not started._
