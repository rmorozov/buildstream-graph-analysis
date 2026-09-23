# UX-926: a round that leaves neither a document nor a ledger row is invisible to the register, and so to the guard whose job is to demand its document

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-666, UX-744, UX-757 | **Blocks:** — | **Found by:** round 135 — `UX-914` closed and shipped with no round document and `make test` stayed green; rounds 132 and 133 had already done the same, and round 134 was caught only because it happened to have priced an agent | **Serves:** every later round, which reads a round's record instead of its code | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-666` was filed on exactly this silence and its guard says so.
`test_a_run_is_priced.py::TestEveryRegisteredRoundPricesItsAgents`
reads `UX-744`'s register **rather than a glob**, in its own words,
because "a glob cannot see a round that skipped its document". The
guard is right about the glob and still cannot see one, because the
register it reads is itself derived from documents plus the ledger's
round column:

> Derived by `tools/dev_round_register.py --write` from the committed
> union: every `docs/audits/round-N.md` plus every round the ledger's
> round column names

So a round that wrote no document *and* launched no agent appears in
neither source, is not in the register, and is never asked for the
document it did not write. The guard holds on rounds that left a
trace and is silent on exactly the rounds it was filed for.

Measured on `main` at `326606a3`:

```text
register                      … 127, 128, 129, 130, 131
named by task files only      … 132 (UX-891..UX-894, UX-910..UX-913)
                                133 (UX-915, UX-916 `Found by`)
                                135 (UX-914 Outcome)
named by the ledger, no doc   … 134
make test                     … 9180 passed, 172 skipped
```

Three rounds of work absent from the repository's own index of its
rounds, with the whole suite green. The register is not wrong — it
derives exactly as its header says — so **the handle stays
well-formed while the thing it handles is not**, which is `UX-920`'s
shape one level up: there an id looked unique and was unread, here a
register is complete over a set that silently lost members.

Round 134 is the demonstration. It left a ledger row, so it *was*
derivable, and it escaped only under the register's "a round still in
progress — the newest number" exemption. The moment round 135's
document registered 135, round 134 stopped being newest and the guard
reddened on the same commit. The mechanism works; its input does not
reach far enough.

## Required Fix

Widen the register's derivation to the third place this repository
already names rounds: the task files. Every closed row's Outcome
carries `**Round N, <date>**` and many `Found by` lines carry `round
N`; `dev_close_task.py` already parses those headers for other
properties. A round named by a task file is a round claimed, and a
round claimed is a round owed a document.

**The exemption is the whole difficulty, and it is where this fix can
quietly become a no-op.** A round cannot write its document before it
has one, so the newest round must stay exempt — and an exemption
written as a range, or as "any round with no document yet", passes
whatever any round does. That is the failure `CLAUDE.md` names: a
guard whose setup another gate already excludes. The exemption is at
most the single highest round number, and a mutation that widens it
to two must red.

Rounds 132 and 133 are not this row's to write — they are
`docs/audits/` history and belong to whoever holds it. The fix
carries them as a named waiver with their numbers and the reason, the
way `UNPRICEABLE_ROUND_WAIVER` names round 101, so the gap is
recorded rather than grandfathered silently.

## Out of Scope

Writing rounds 132 and 133's documents, or reconstructing any round
from `git log` — `UX-782` is why reachability is not a record. Rounds
134 and 135's documents, written by round 135 from committed material.
What a round document must contain, and the §7a ritual's other six
steps. The round-numbering scheme itself: that concurrent threads pick
overlapping numbers is a separate question, and this row asks only
that whatever number a round claims, it leaves a document behind.

## Acceptance Test

`tools/dev_round_register.py --write` lists every round a task file
names, and `make test` reds on a tree where such a round has no
`docs/audits/round-N.md`.

Three mutations, each applied, reddened, reverted:

- add a task file whose Outcome states round 200, with no document —
  the register lists 200 and the pricing guard reds. Today it does
  neither;
- delete `docs/audits/round-134.md` — the guard reds, proving the
  waiver added for rounds 132 and 133 does not cover a round that
  *is* derivable from the ledger;
- widen the in-progress exemption from the highest round to the
  highest two — the guard must still red, or the exemption is what is
  passing and not the check.

Removing either of rounds 132 and 133 from the waiver reddens, and
the register's own `--check` stays clean throughout: the derivation
and the written table never disagree.

## Outcome

**Round 138, 2026-09-23**

**Premise:** held, and one round wider than filed - the widening also
reads round 96 (`UX-716`'s `Found by`), which the Motivation's list
did not name.

### The gap, measured

`dev_round_register.rounds()` now joins `task_file_rounds()`: the
`## Outcome (round N` heading, a `**Round N` paragraph from the first
`## Outcome` on, and `**Found by:** round N` in the 8-line header -
over `dev_close_task.SCENARIOS` and `_FILE_ID`. Before the waiver:

```text
$ grep -c '^| [0-9]' docs/audits/round-register.md    # HEAD, then --write
91
120      # +25 26 28 29 47-54 56-59 62 65-73 96 132 133
$ python3 -m pytest tests/unit/test_a_run_is_priced.py -q
FAILED ...test_it_carries_a_document_or_is_waived[96]
FAILED ...test_it_carries_a_document_or_is_waived[132]
FAILED ...test_it_carries_a_document_or_is_waived[133]
```

### The close, measured

`NO_DOCUMENT_WAIVER` names 96, 132 and 133 with the reason, the way
`UNPRICEABLE_ROUND_WAIVER` names 101; a waived round the register stops
listing, or that gains a document, reds. `in_progress()` holds back
at most the newest number, and only when it is the one after the
newest document, so a claimed 200 is owed, not exempt. Ten
`GIT_ONLY_ROUNDS` entries a task file now names are dropped (13 -> 3:
31, 55, 60), or `--check` reds naming each. With a task file naming
round 138 planted on this tree: `--check` exit 0, the two guard files
195 passed - 138 is held, 137 has its document.

```text
$ python3 tools/dev_round_register.py --check; echo $?
0
$ make test-touching
65 file(s) selected (21 census + 44 naming the change) · 2179 passed, 3 skipped
```

### Mutations verified red and reverted (8)

`mutate.py` in the scratchpad: apply, run, restore the copy, re-run green.

| # | mutation | reddened |
|---|---|---|
| M1 | a task file whose Outcome states round 200, no document | register lists 200 (`--write`, `--check` 0); `test_it_carries...[200]` |
| M2 | `docs/audits/round-134.md` deleted | `test_it_carries...[134]` |
| M3a | exemption = the highest two numbers, when undocumented | `...OneNextRound`, 2 |
| M3b | exemption = the highest two undocumented numbers | `test_at_most_the_newest_round_is_held_back`, `..._still_owed_...`, `...OneNextRound` 2 |
| M4 | 132, then 133, dropped from `NO_DOCUMENT_WAIVER` | `test_it_carries...[132]`; `[133]` |
| M5 | the one-after-the-newest-document bound removed | `...OneNextRound`, 2 |
| M6 | `GIT_ONLY_ROUNDS` back to 13 entries | `--check` exit 1, rounds 26 29 47 48 50 52 53 58 67 69 "at a task file" |
| M7 | `task_file_rounds()` returns `set()` | `test_a_waived_round_is_still_owed_its_document` |

M3a reddens only the fixture class: on this tree 136 and 137 both have
documents, so a real-tree reading cannot see it. M3b reddens the
real tree too, because 132 and 133 are the two highest undocumented.

### Deviation

- **The one-next bound is new.** The Acceptance Test's round 200 is
  the highest number, so "the newest round is exempt" alone holds it
  back and M1 stays green; bounding the exemption to max(documented)+1
  is what makes M1 red. Still at most one round.
- **Round 96 is waived, not written**: a real round (`UX-716` filed
  2026-09-05, `architecture-review.md:1285` names its four closes)
  with no document. Rounds 97 and 98 have none either, but only prose
  names them (`walk-seed-1.md`, `UX-728`), so no marker reads them.
- 135-137 each have a document; no task file on any `origin/` branch
  names 139 or above.
- `dev_sizes.py --check` held the tool at 292 lines (first cut 341):
  older docstrings lost their history, which their rows keep - 291.
