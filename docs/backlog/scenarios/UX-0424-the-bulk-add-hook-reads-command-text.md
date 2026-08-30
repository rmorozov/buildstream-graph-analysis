# UX-424: the bulk-add hook matches command text, not command effect

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 67, while writing the hook — recorded in commit `af209a7`'s message and nowhere else | **Serves:** every contributor, at the point a hook blocks them | **Topic:** guards

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
