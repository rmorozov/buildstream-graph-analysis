# UX-322: the CLI table has lost the viewer

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Serves:** R2 — whoever is looking for what this tool can do | **Topic:** docs

## Motivation

`docs/design/architecture.md`'s command table is the one place a
reader goes to ask "what commands are there". It has eighteen rows.
The tool has twenty:

```text
in the table but nowhere else:  (none)
working and not in the table:   bga view
                                bga timeline
```

Both were checked by running them:

```text
bga view      --help  -> works
bga timeline  --help  -> works
```

`bga view` is the entry point for the **entire viewer axis** — every
round from `UX-193` (round 21) to `UX-320` (round 44), something like
forty closed scenarios, the export, the rail, the drawings, the visual
contract. `bga timeline` is `UX-188`'s two-plane trace and `UX-298`'s
native Perfetto emitter. A reader consulting the table to find out
whether this tool can show them anything sees neither.

They are not *absent* from the document — the prose mentions `bga view`
at four places and `bga timeline` at two. They are absent from the
**table**, which is the surface built to be read as a list.

## Why this is filed and not fixed

Found by review 4. A review that fixes what it finds is a fix session
wearing a review's name.

## Notable: this is a recurrence

`UX-245` was "the architecture's CLI table is two commands behind",
found by review 1 and closed. Three reviews later the same table is
two commands behind again, and this time the two are the axis the
project has spent the last twenty-four rounds on. The pattern is worth
a thought in the fix: a table maintained by hand against a parser that
knows the answer will drift again, and
`test_the_documents_keep_up_with_the_contracts.py` already
demonstrates the shape of a guard that would not let it.

## Required Fix

Both commands get a row, with what they report and their
not-spec-mandated marker like the other eight. And — the part worth
more than the two rows — a guard that compares the table against the
CLI's own subcommand list, so the third recurrence is a red test
rather than a fourth review.

## Out of Scope

- Rewriting the table's other rows. They were checked against the
  parser by this review and all eighteen name a real command, so
  there is nothing to fix and touching them would widen the diff
  past what the finding supports.
- The module map (`UX-294`'s subject, a different list in the same
  document).

## Acceptance Test

Every command `bga --help` lists has a row in the table and every row
names a real command; the guard reddens when a command is added to the
parser without a row, and when a row names a command that does not
exist.

## Outcome (round 46, 2026-08-26) — 🟢 Done

### A correction to this filing's own numbers

Review 4 said "the table has 18 rows; the tool has 20 commands". The
20 was wrong — it came from probing eight names by hand. Counted from
the parser and the alias table:

```text
native subcommands (bga/cli.py)          12
tools/ aliases     (TOOL_ALIASES)        19
                                         --
commands in all                          31
rows in the architecture's table         18
rows naming no real command               0
```

The finding survives the correction — `bga view` and `bga timeline`
were among the thirteen aliases reachable only through the catch-all
row — but the shape is different from what the filing described, and
that is worth having straight before the guard encodes it.

### The third gap, found while writing the rule

`bga wrap` had no row either. It *looked* like it did, because the
catch-all row was titled ``| `bga wrap` / `extract` / `rebuild-set` /
…``, and a scan for row-leading command names matched the first one.
Rewriting that title to name the converters instead made `wrap`
disappear — and the guard, written minutes earlier, caught it on its
first run. It is in the README's own quickstart, so it now has a real
row.

Three commands, then: `view`, `timeline`, `wrap`. The table is 21 rows.

### What the rule had to be

"Every command has a row" is wrong, and that mattered: eleven aliases
are format converters (`log-to-chrome`, `chrome-to-trace`,
`native-to-chrome`, `graph-from-show`) and internal plumbing
(`gen-synthetic`, `run-context`, `release-notes`, `cross-check`,
`checkout-cost`, `extract`, `rebuild-set`). A row each would bury the
eight a reader actually looks for.

So `tests/unit/test_the_command_table_is_the_cli.py` holds three
clauses that need no judgement and one that isolates the judgement:

* every **native subcommand** has a row — the parser is the list;
* every **row** names a command that exists — the direction `UX-245`
  never checked, and the one a rename breaks;
* every **promoted alias** has a row, `PROMOTED` being the eight;
* and two clauses on `PROMOTED` itself: every name in it is a real
  alias, and promotion stays a minority of the aliases — because if
  most get promoted the distinction has stopped meaning anything and
  the table is a command dump again.

A new alias defaults to *not* promoted and nothing fails. That is right
for a converter and wrong for the next `bga view`, and it is a
deliberate limit: what catches that one is still a review, but a review
arguing about one name rather than re-deriving the table.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| V1 | delete the `bga view` row — the exact `UX-322` defect | the promoted-alias clause and the by-name clause |
| V2 | rename `floors` to `floorz` in the table | the native-subcommand clause *and* the names-something-real clause, from opposite directions |

### Deviation from the Required Fix

None. Both rows landed and the guard landed. The filing's Out of Scope
said not to rewrite the table's other rows; the `wrap` row is a new
row, not a rewrite of an existing one, and it is there because the
guard demanded it rather than because the round widened.
