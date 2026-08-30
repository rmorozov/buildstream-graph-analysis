# UX-426: the sessions' loop does not know that CI is sometimes the only instrument

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 68, working UX-421..UX-425 | **Serves:** the next session, before it spends an hour proving something its machine cannot prove | **Topic:** docs

## Motivation

The `verify` skill's Definition of Done is a sequence of things to run
**here**: the acceptance test, `make test-touching`, the tier, the
suite, lint. It has no entry for a claim this container cannot check at
all, and three of round 68's five items were exactly that:

- `UX-421`'s acceptance test is *"fails on the fastest runner seen and
  on the slowest"*. One machine cannot produce two runners.
- `UX-422`'s failure was a loaded runner. Eight CPU spinners on four
  cores did not reproduce it — the floor probe read 0.00 ms in all ten
  runs, idle and loaded.
- `UX-423`'s reference is CI's own clock, and `UX-418` established that
  a local report cannot be read against it in any form.

For those, CI is not a slower copy of `make test`; it is the only
instrument that exists. A session that does not know this spends its
budget trying to build a local proof that cannot be built.

**And there is a mechanism that makes the omission expensive:**

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

A branch with no PR collects **no runs at all**, however many times it
is pushed. A session that pushes five commits and opens the PR at the
end gets one round of CI feedback instead of five, after every design
decision is already made.

## Required Fix

Write down the fact and the loop it implies, in the place a session
reads before it starts verifying:

- **`verify` skill, a new section.** It owns the Definition-of-Done
  sequence, so the case "this cannot be checked here" belongs beside
  the cases that can.
- **`docs/contributing/fixing-guide.md` §3**, one paragraph pointing at
  it, because §3 is where the mandatory verification lives.
- **A guard on the trigger fact.** It is two copies of one fact, and
  this repository has watched that shape drift three separate times. If
  CI is ever changed to run on every push, the advice becomes both
  wrong and unnecessary and nothing else would say so.

## Out of Scope

- **Promoting any of it to a §5 hard rule**: one round is not a
  baseline. `UX-420` sized a threshold on one sample and its first
  armed run named thirty-one files on an unchanged suite; the Outcome
  below says what would have to be measured to change this.
- **Changing `ci.yml`'s triggers**: running CI on every branch push
  would remove the need for the advice, and it is a cost decision for
  the repository's owner rather than a fix to make in passing.
- **Automating the loop** — a hook that opens a PR, or a check-in
  scheduler. The loop is a judgement about what kind of claim is being
  made; `UX-425` is the record of why this class is not decidable from
  a payload.

## Acceptance Test

- `tests/unit/test_the_agent_configuration_holds.py` reddens when
  `ci.yml`'s triggers stop matching what the skill says.
- It also reddens when the skill drops the fact, when it stops
  admitting the loop is unmeasured, and when the loop is promoted into
  the hard rules.

## Outcome (round 68, 2026-08-30) — 🟢 Done

### The gap, measured

```console
$ sed -n '3,8p' .github/workflows/ci.yml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

$ grep -c "pull_request\|draft" .claude/skills/verify/SKILL.md
0
```

The skill that owns verification said nothing about the one trigger
fact that decides whether verification happens at all.

### After

Three placements, and one of them is a refusal:

- **`verify` skill §7** — the three items CI alone could check, the
  trigger fact, and the three-step loop (per item: implement,
  `test-touching`, mutate, commit, push; between items: read the check
  runs; at the end: `make test` plus whatever CI batched).
- **Fixing guide §3** — one paragraph, pointing at §7.
- **Not §5.** The hard rules do not carry it, and
  `test_it_is_guidance_and_says_so` fails if a later round puts it
  there.

### What is a fact and what is a preference

Separated on purpose, because this round's own subject was instruments
that read a proxy:

| | status |
|---|---|
| CI runs on `pull_request` and pushes to `main` only | **fact**, guarded |
| three of five items had no local instrument | **fact**, each named with its reason |
| batch what is cheap to fix late, never a design decision | argued from round 66's three red CI rounds |
| the per-item loop is cheaper than the alternative | **not measured** — see below |

### The claim this item deliberately does not make

**Nobody measured whether any of this is faster or cheaper.** No
wall-clock figure, no context figure, and no comparison against a
session that did it the other way. The round felt smoother; that is not
a number, and *"roughly 5% run-to-run noise"* is the kind of sentence
this repository has already been wrong with.

So §7 states its own status in the text, and a clause holds it there.
`UX-420` sized a threshold on one sample and its first armed run named
thirty-one files on an unchanged suite; asserting a process rule on one
round is the same shape one level up, and
`tools/dev_process_bands.py` says in its own output that a band needs a
baseline and one reading is not one.

What would change it: two or three rounds run this way with the wall
clock and the context cost recorded in each Outcome, against rounds
that were not. Then it is a measurement and §5 can have it.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| S1 | `ci.yml` starts running on every push | 1 failed, 70 passed |
| S2 | the skill drops the fact it rests on | 1 failed, 70 passed |
| S3 | the skill stops admitting it is unmeasured | 1 failed, 70 passed |
| S4 | the loop is promoted into the hard rules | 1 failed, 70 passed |

S3 and S4 are the pair worth having. Together they are the only thing
stopping a later round from reading §7 as settled practice, which is
the failure this item is most likely to have.

```text
baseline    71 passed in 0.93s
reverted    71 passed in 0.99s
```

### Deviation from the Required Fix

- **None.** All three placements landed, the trigger fact is guarded,
  and the refusal to promote it is guarded too.
