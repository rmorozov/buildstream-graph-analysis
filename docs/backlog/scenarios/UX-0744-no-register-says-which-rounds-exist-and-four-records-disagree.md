# UX-744: no register says which rounds exist, and four records disagree

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-666 (the runs ledger, and the guard that stops at the documents which exist) | **Serves:** the session opening a round, which cannot number it from any record | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-666` wanted a guard over "every round document from 90 on". Its
population was measured before the guard was written, and there is no
list to run it over. Four records disagree, and none is authoritative:

```console
$ ls docs/audits/round-*.md | sed 's/.*round-//;s/.md//' | sort -n | tail -1
95
$ grep -o "^## UX-[0-9. ]*: the [a-z-]* round" docs/backlog/scenarios/README.md | head -1
## UX-706..UX-711: the ninety-fourth round
$ python3 -c "import sys; sys.path.insert(0,'.'); from tools import dev_process_bands as b; print(sorted({r['round'] for r in b.ledger_runs()}, key=int))"
['64', '77', '82', '90', '91', '92', '93', '94', '95', '100', '102', '103']
$ git log --oneline --format=%s | grep -ci "^round 9[0-9]\|^round 10[0-2]"
9
```

So: **96, 97 and 98 never existed** — the only matches in the tree are
two synthetic fixture strings (`test_a_release_records_a_contract
_state.py`, `test_a_scenario_is_named_by_its_seed.py`). **99, 100, 101
and 102 are real** — each has a commit closing real ids, and `UX-728`,
`UX-729`, `UX-732`, `UX-733`, `UX-738` are 🟢 Done rows in `closed.md`
— and none of the four has a round document, a README heading or a
`closed.md` heading. **103** appears only in the runs ledger.

The consequence is not untidiness. It is that no guard can say *round
N is missing its document*, because no record says round N happened.
`UX-666`'s guard reads the documents that exist, so a round that
skipped its document passes it silently — the shape `CLAUDE.md` names
under "writes a guard whose setup another gate already excludes".

## Required Fix

One register, derived rather than typed, that says which rounds
happened: the round number, its date, and the ids it closed. The
material is already committed — `closed.md`'s rows, the commit whose
subject names the round, and the ledger's own round column — so the
register is a derivation like `dev_close_task.py --check --write`'s
counts, not a hand-kept list that drifts a fifth way.

Then `UX-666`'s guard reads the register instead of the glob: every
round in it, except the newest, has a document that prices its agents.
Rounds 99..102 red until their documents are written, which is the
point.

## Out of Scope

- Retro-writing the four missing round documents. That is archaeology
  with its own cost, and it is what this row's guard would demand
  rather than what it builds. File it when the register exists and the
  guard names the four.
- Renumbering anything. 96..98 not existing is a fact about the record,
  not a hole to fill.

## Acceptance Test

The register names 99..103; `dev_process_bands.py --runs`' round
column is a subset of it; the extended `UX-666` guard reds naming
rounds 99, 100, 101 and 102 as undocumented. Mutation: delete a round
document that the register names — the guard reds with that round's
number, where today it cannot see the absence at all.

## Outcome

Reopened twice. Round 104's attempt shipped a self-referencing file,
fixed by construction (fixing-guide.md §7a): `written_rounds()` drops
`rounds()`'s own newest number. Its verifier then found the ids-closed
column wrong on four of five demonstrated rounds - `commit_signal()`
cannot tell a commit that *documents* an earlier round from one that
is *in* it, and `UX-757`'s retroactive documentation of rounds 99-102
legitimately names them in prose while writing their history.

**The column: dropped, not fixed.** A "## What closed" paragraph
extraction was tried against the four flagged rounds and failed on
its own evidence: round 100's document opens a paragraph naming
`UX-737`/`UX-738`, then says two sentences later "not closed... both
close in round 101" - a heuristic reading the paragraph's first id
cannot tell that apart from a real close. The register is `{round,
date}`; `docs/README.md`'s row and the module docstring say so.

**The date, tested against the round's own document**, per the hold's
requirement: `document_date()` reads the round's own text (its first
stated date, or the file's own first-commit date if it states none),
compared for every `FIRST_PRICED_ROUND`-on round with a document:

```console
$ python3 -m pytest tests/unit/test_a_run_is_priced.py \
    -k TestARegisteredRoundsDateMatchesItsDocument -q
15 passed   # 14 rounds (90-95, 99-106) + the population check
```

Round 101 is the same contamination the hold named (register said
2026-09-07; its own document's "Opens at" says 2026-09-06), now
caught and pinned (`DATE_MISMATCH_WAIVER`), not silent.
Below `FIRST_PRICED_ROUND`, rounds 76 and 85 also mismatch, and
verification falsified the multi-day reading first offered here: both
are the *same* contamination. `_first_date_in_text` takes the file's
first `YYYY-MM-DD` whatever it means - for 76 that is `UX-96`'s cron
firing `2026-09-01`, for 85 a status-word note dated `2026-09-03` -
and no commit touching either round's rows exists on the earlier day.
They are outside the population only because `UX-666` set
`FIRST_PRICED_ROUND` at 90, not because they are a different
phenomenon. `UX-772` carries the dateline fix.

**The exclusion rule** no longer drops "whichever round is highest so
far" unconditionally: `written_rounds()` drops the newest only if that
round has no document yet. A documented round is never held back
waiting for a strictly higher round the naming convention might stop
producing.

**Mutation table**, this hold's fixes (the earlier table - the
self-reference fix, phantom rounds from prose, the deletion mutation,
the ledger-`setdefault` check - is unchanged and still green):

| mutation | reddened |
|---|---|
| `_first_date_in_text()` never finds a stated date | 5/63: the fixture, and rounds 99, 100, 101 (the pin itself), 102 against the real documents |
| `written_rounds()` reverts to "always drop the max" | 2/63: the fixture permanence pin, and `check()` against round 106's now-documented row |

`UX-759` still owns reading a round's own document as a *correct* ids
source; this row tried exactly that within its own scope and found it
unreliable, which is now evidence for that row rather than motivation
alone.

### The second verifier held, and the row merged anyway

The re-verification of `17bf0b8` returned `## Verdict: HOLD`: the
population claim for rounds 76 and 85 was not supported by the
evidence given for it. The row merged 26 seconds later.

The finding was **accepted, not declined** — the Outcome above was
corrected and `UX-772` filed against `document_date()`. But `UX-761`
says a row does not merge until the track has answered the finding or
the session records here why it is declined, and neither happened
before the merge. Recorded now because a reader of this file would
otherwise learn only the corrected conclusion and not that a verifier
reached it first.

`UX-759`'s premise did not survive this row: the register that shipped
has no ids column, so that row closed as a decline. That annotation
was owed by this commit under the fixing guide's item 6.
**Deviation (round 110).** Closed by the session on a verifier's reading of the tree at `c13297cf`: every Required Fix clause present (`cbe1ccfa`, `17bf0b8d`, `867c8b29`), the HOLD answered by `UX-772` — `document_date()` reads `None` for rounds 76 and 85 and both are waived by name — and the owed annotation above in place. Two corrections: round 107's "26 seconds" has no commit behind it (`17bf0b8d` to `51742474` is 11 m 48 s); and the Acceptance Test's "99–102 undocumented" clause is moot since `UX-757` documented them — the guard's power was shown by deleting `round-100.md` instead.
