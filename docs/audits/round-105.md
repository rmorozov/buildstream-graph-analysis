# Round 105 — the two rules the pipeline never wrote down

Run on 2026-09-07. Two rows, both from round 104's pipeline review,
both `judgement`, both held by their verifier before merge. Three
rows filed, two of them found by closing the round itself.

## What closed

`UX-761` moved the verifier mandate out of `.claude/skills/decompose/
SKILL.md` — its only statement anywhere — into `fixing-guide.md` §3,
beside the sentence a track satisfies alone. The guide outranks skills
by its own rule (`:21`) and is the mandatory entry point (`:1`), and
it had **zero** occurrences of the word:

```console
$ grep -c verifier docs/contributing/fixing-guide.md docs/contributing/rules.md
docs/contributing/fixing-guide.md:1
docs/contributing/rules.md:1
```

(one each, after the change). What a hold obliges is now stated: the
row does not merge until the finding is answered or the decline is
recorded in the task file. A guard reads the ledger — every merged
`implementer` row from round 104 on has a paired `verifier` row naming
the same id.

`UX-762` bound the gate to the commit that gets pushed. `make test`
writes the sha it covered, on success only; a `PreToolUse` hook
compares `HEAD` to it and refuses, naming both shas, with an escape
hatch that must name a row and shouts on stderr when it fires.

## What the verifiers found

Both rows were held, and neither finding was visible without re-running
the track's own work.

`UX-761` pasted a measurement that does not reproduce. Its Outcome
claimed `grep -c verifier` returned `6` and `2`; the real answer is `1`
and `1`. It also left `decompose/SKILL.md:97` restating the rule
verbatim while its commit message asserted the opposite, and excluded
two ledger rows **by name** on a narrative sentence the ledger's own
schema contradicts. The floor moved to round 104 and the exclusion list
went.

`UX-762` shipped a hook that an ordinary command walked straight past:

```console
$ echo '{"tool_input":{"command":"git status && git push origin master"}}' | gate-covers-push.sh; echo $?
0
```

Uncovered `HEAD`, no escape variable, silent exit 0. `is_real_push`
returned at the first `git` invocation instead of scanning on — the
opposite of `no_bulk_add.is_bulk_add`, the sibling its own docstring
cited as the pattern. Its four mutations all passed because none of
them used a compound command. Rewritten, it now catches nine
adversarial forms and falsely fires on none.

The escape hatch was a silent, permanent off-switch: exported once, it
disabled the gate for the shell's life with nothing printed or written.
It now must name a row and prints a loud line on the path that actually
bypasses.

## What closing the round found

**The pipeline's own order defeats the new gate.** `CLAUDE.md:28` reads
`tracks → verifier → merge, one make test, close` — with *close* after
the gate, and close means the row moves, the derived counts, the ledger
and this document. Every one is a commit, so on that order the hook
reds on the final push of every round and the reflex becomes the escape
hatch. This round closed the other way round — gate **last**, after
everything above — and pushed with no bypass. Recorded in `UX-763`,
which owns what closing a round owes.

**The gate sees one channel.** `d580122` — the merge of both rows —
reached origin with no marker in the checkout at all, and nothing
refused: the session issued no `git push`, the harness's automation did,
between turns. A `PreToolUse` hook intercepts Bash tool calls; every
other route to the remote is invisible to it. Filed as `UX-767`, with
the measurement.

**`UX-745`'s safeguard does not survive its own commit.** `UX-762`'s
track forced two `S607` baseline entries. `UX-745` chose visibility
over refusal — "loud in the output the session reads" — but
`gained_since_head` compares the tree to `HEAD`, so the growth is loud
while uncommitted and silent forever after. Its verifier found it by
reading `git diff tests/quality_baseline.json` by hand. Filed as
`UX-766`.

**The closing note is argv, and its backticks ran.** `UX-762`'s note
quoted the command form its first parser walked past. Passed through
`--note "…"` the backticks were command substitution: `git status`'s
stdout landed in `closed.md:752` and split the row across seventeen
lines, and `git push origin master` was attempted, failing only because
no local `master` exists. The cell-count guard caught the garbling at
the gate; nothing was watching the execution. Filed as `UX-768` —
the note belongs in a file, not in a shell word.

## Agents

Four runs, 1,367k, two implementer and two verifier, all on `sonnet`.

| | |
|---|---|
| implementer | 2 runs, 929k — both reworked twice |
| verifier | 2 runs, 438k — 47% of the implementer spend, and it held both rows |

Two rows, four holds between them. Every hold was on something the
track's own report asserted and its own commands disproved: a grep that
did not reproduce, a commit message that described a diff it had not
made, a mutation table that never met the input that broke the feature.
Rows in [`agent-runs.md`](agent-runs.md), derived by
`dev_track_cost.py --ledger`.

Merging cost **1.0 commits per item**, no conflicts, against the
1.46-1.83 the `decompose` skill prices.
