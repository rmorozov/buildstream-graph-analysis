# UX-596: build time in the team's units

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-230 (a price on a chosen set), UX-581 | **Serves:** R8, the engineering lead funding infrastructure | **Topic:** analysis

## Motivation

Direction 9's third argued step, and R8's half of it. Headline and
what-if price a fix in *build seconds*, for one project. `UX-580`
measured that nothing converts to anything a budget speaks, and
`git grep "cost translation" -- docs/backlog/scenarios` reaches only
`UX-234`.

## Required Fix

An opt-in rate — engineer-hours per build-hour, or a currency per
machine-hour — that converts a priced fix into the unit the lead
argues in, with the rate stated as an input the reader supplied and
never as a measurement.

## Out of Scope

- Choosing a default rate — declined: a made-up rate presented as a
  figure is the anecdote this item exists to replace.

## Acceptance Test

With no rate the output is unchanged; with one, every converted
figure names the rate that converted it. Mutation: print a converted
figure without its rate — red.

## Outcome (round 84)

### The Motivation re-measured, and one clause falsified

```text
git grep -l "cost translation" -- docs/backlog/scenarios  4, not "only UX-234"
  UX-234, UX-581, UX-595, this file
```

Three of the four postdate the sentence, so what it stood for holds for
closed work; as written it is wrong. The rest reproduced, on
`tests/fixtures/macro_micro/run`:

```text
core.bst  19.1s (44.1% of path)  -> fixing it saves 12.1s (26.1% of the build)
Together, the top 3 are worth 23.1s (50% of the build)
```

Build seconds, for one project, converting to nothing — `roles.md`'s R8
row, unchanged.

### The close

```text
$ BGA_RATE="90 USD/machine-hour" bga analyze tests/fixtures/macro_micro/run
In Your Units:
  rate: 90 USD/machine-hour - an input you supplied (BGA_RATE), not anything this run measured
  core.bst            12.05s = 0.30 USD at 90 USD/machine-hour
  lib-b.bst            4.00s = 0.10 USD at 90 USD/machine-hour
  lib-d.bst            4.00s = 0.10 USD at 90 USD/machine-hour
  the top 3 together  23.05s = 0.58 USD at 90 USD/machine-hour

$ BGA_RATE="cheap"  ->  not applied: BGA_RATE='cheap' is not
    `<amount> <unit>/<machine-hour|build-hour>` …
$ diff (report before this commit) (report after, no rate set)  ->  IDENTICAL
```

**Three refusals, each because the alternative is the anecdote.** No
default rate, so nothing converts unless a reader supplied one. Every
converted figure carries `at <rate>` on its own line, welded on by one
function, because a converted figure travels alone — pasted into an
issue, screenshotted into a deck. And the together row is
`joint-saving`'s published number, never the sum of the rows above it
(`UX-230`: two fixes on one chain do not add — 23.05s here against a sum
of 20.05s). A rate that cannot be parsed is **named**, because silence
would be indistinguishable from having supplied none.

**Supplied through the environment, not a flag:** `bga analyze --help`
renders **45** lines against `test_help_is_short.py`'s cap of **45**.

**Not in the payload,** by design rather than by constraint: the seconds
are what the run measured and `analyze/v5` publishes them; the rate is
the reader's input, and a schema-described record of what was observed
is not where an input goes. Guarded by running the real CLI with the
rate set and asserting the JSON carries neither.

### Mutations verified red and reverted (13)

| mutation | reddened |
|---|---|
| fall back to a default rate when none was supplied | 3 |
| print the converted figure without its rate | 3 |
| drop the seconds and print only the conversion | 2 |
| sum the individual savings for the together row | 1 |
| swallow an unparseable rate instead of naming it | 1 |
| accept any denominator / a non-positive amount | 1 / 2 |
| loosen the grammar to a permissive regex | 1 |
| convert per minute rather than per hour | 2 |
| stay silent when the run prices no fix | 1 |
| write the rate into `analyze/v5` | 1 |
| drop "not anything this run measured" from the preamble | 1 |
| forget which denominator was written | 1 |

All 13 anchors grepped back and landed; no guard failed to discriminate.

**Deviation from the Required Fix:** two, both named above. The rate
arrives through `BGA_RATE` rather than a flag, because `--help` is at its
measured cap. And `bga whatif`'s projected saving is **not** converted —
its renderer is `bga/whatif.py`, outside this track's surface — so the
headline's prices convert and the what-if's do not. Filing.
