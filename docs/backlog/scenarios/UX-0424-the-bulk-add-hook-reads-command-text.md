# UX-424: the bulk-add hook matches command text, not command effect

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 67, while writing the hook — recorded in commit `af209a7`'s message and nowhere else | **Serves:** every contributor, at the point a hook blocks them | **Topic:** guards

## Motivation

`.claude/hooks/no-bulk-add.sh` enforces fixing guide §4a.1 by matching
the `Bash` tool's command string:

```bash
if printf '%s' "$cmd" | grep -Eq '(^|[;&|(]\s*)git\s+add\s+(-A\b|--all\b|\.(\s|$))'; then
```

It reads the command's **text**, and a text scan cannot tell a command
from a mention of one. During round 67 it blocked its own commit three
times: the commit message and the test fixtures for the hook both
*quote* the pattern the hook looks for, and quoting it is enough. The
anchor `(^|[;&|(]\s*)` narrows this but does not close it — a heredoc
body, a `grep` argument and an `echo` all sit after a shell
metacharacter or a newline.

This was recorded as an accepted cost of a blunt deterministic control
and then **never filed**, which is the actual defect being fixed here:

```console
$ grep -rn "no-bulk-add" docs/
(no output)
```

Two rounds from now the only record of it is a commit message.

Whether it is worth fixing at all is a real question and the row exists
so somebody answers it rather than rediscovering it. The argument for
leaving it: a false block costs one retry with explicit paths, a missed
block costs a tree somebody else unpicks, and the conservative
direction is the one it already takes. The argument against: the
repository has now paid for the same shape four times (`UX-340`,
`UX-403`, `UX-420`, and this), and `UX-403`'s fix — tokenise, do not
lengthen the regex — showed the cheap structural answer exists.

## Required Fix

Decide, and record the decision where the next round reads it:

- **Either** narrow the match to a command position — split on `;`,
  `&&`, `||`, `|` and newlines and require `git` to be the first word
  of a segment, which removes the heredoc and argument cases without
  parsing the shell. Cheap, and it is the same move as `UX-403`'s.
- **Or** state in the hook's own comment that a false block is accepted
  and why, so the next contributor who trips it does not open this
  again. The hook already explains *what* it blocks; it does not
  explain that a mention counts.

A shell-grammar parser is not on the table for a hook that must run on
every `Bash` call.

## Out of Scope

- The rule itself. §4a.1 is not in question — only the instrument.
- The other two hooks. `keep-the-guards-able-to-fail.sh` matches an
  edit's `new_string`, which is the thing rather than a proxy for it,
  and `lint-edited-python.sh` runs the linter.

## Acceptance Test

In `tests/unit/test_the_agent_configuration_holds.py`, whichever branch
is taken:

- A payload whose command is `git add -A` is blocked (already guarded).
- A payload whose command is
  `git commit -m "do not use git add -A here"` is **not** blocked —
  or, if the second option is chosen, the hook's comment says in words
  that this payload is blocked on purpose, and a clause reads that
  sentence.
- A payload whose command is `git add ./bga/x.py` is not blocked
  (already guarded).

Each new clause shown red under a mutation that reverts the change it
tests, per the `falsify` skill.

## Outcome (round 68, 2026-08-30) — 🟢 Done

### The gap, measured

A probe firing the hook at twenty payloads. It could not be run from
the shell: the hook blocked the probe script itself, because the script
*mentions* the pattern inside quoted arguments. That is the defect,
demonstrated by the attempt to measure it — the fifth and sixth
sightings in this repository, both today.

```text
want   got     case
BLOCK  BLOCK   bare
BLOCK  BLOCK   bare dot
BLOCK  BLOCK   bare --all
BLOCK  BLOCK   after &&
BLOCK  BLOCK   after ;
pass   pass    a named path
pass   pass    a dot-slash path
pass   pass    two named paths
pass   pass    quoted in a commit message
pass   BLOCK   inside a heredoc, prose   <-- wrong
pass   pass    inside a heredoc, a markdown table row
pass   pass    inside a heredoc, a bullet
pass   pass    an argument to grep
pass   pass    an argument to echo, after a pipe

1 of 14 wrong
```

The anchor `(^|[;&|(]\s*)` narrowed the old regex more than expected —
a bullet and a table row both passed. What it cannot do is tell a
separator in *prose* from a separator between commands, and it cannot
see quoting at all.

### After

Six more payloads, including the two that blocked this session live and
the hole a quote-stripping fix would have opened:

```text
pass   pass    single-quoted arg holding a separator
pass   pass    a python -c whose source mentions it
BLOCK  BLOCK   the flag itself quoted
BLOCK  BLOCK   the flag in a short cluster
BLOCK  BLOCK   a second line of a script
BLOCK  BLOCK   unbalanced quote falls back to the regex

0 of 20 wrong
```

### Tokenise, do not lengthen the regex

The same move `UX-403` made for the same defect one file over: a longer
pattern chases an unbounded class of confusions, and a token stream
does not have them. Heredoc bodies are dropped, then `shlex` splits the
rest under shell quoting rules, and `git` counts only in **command
position** — first token, or straight after a separator `shlex` emits.

Two alternatives were considered and rejected in the file's docstring:

- **Strip quoted spans, re-run the regex.** `git add "-A"` then reads
  as a bare `git add` and passes — a real bulk add lost. Tokenising
  keeps it, because `shlex` removes the quotes and leaves the word.
  Both quoted forms are now clauses.
- **Accept the false blocks and document them.** Cheap, and it leaves a
  control whose failure mode is *"you may not write about the rule I
  enforce"*. That control gets switched off, which is how a control
  stops existing.

Two things the measurement changed rather than the design:

- `shlex` treats a **newline as whitespace**, so `make test\ngit add -A`
  put `git` in argument position and passed. `_as_one_line` substitutes
  `;` first. Found by writing the clause, not by reading the code.
- An **unparseable** command (an unbalanced quote is ordinary) falls
  back to the old regex. Conservative on purpose: a false block costs
  one retry with explicit paths, a missed one costs a tree somebody
  else unpicks.

`-u` was **not** added to the bulk operands. It stages every tracked
modification and is arguably a fourth, but it was never blocked, and
adding it would be a rule change wearing an instrument fix's clothes.

`make lint` now runs ruff over `.claude/hooks/` too, since the decision
is Python and was previously unlinted.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | the decision goes back to scanning raw text | 6 failed, 53 passed |
| M2 | heredoc bodies are not dropped | 1 failed, 58 passed |
| M3 | a newline is not turned into a separator | 1 failed, 58 passed |
| M4 | an unparseable command passes instead of falling back | 1 failed, 58 passed |

M1 takes out the whole new class at once, which is the point of it.
M2, M3 and M4 each redden exactly one clause, which is what says the
three parts of the fix are separately load-bearing rather than one
change described three ways.

```text
baseline    59 passed in 38.85s
reverted    59 passed in 0.86s
```

### Deviation from the Required Fix

- **The Required Fix offered two options and this took the first**,
  which the filing allowed. The second — document the acceptance —
  survives in the hook's docstring as a rejected alternative with its
  reason, so the next round does not re-open the question cold.
- The filing scoped the acceptance test to three payloads. It ships
  with twenty, because writing the three surfaced two cases neither the
  filing nor the design had (the newline, and the quoted flag).
