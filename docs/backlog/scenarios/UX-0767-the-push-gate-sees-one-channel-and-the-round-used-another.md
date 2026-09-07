# UX-767: the push gate sees one channel, and the round used another

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-762 (the gate it limits) | **Serves:** the session that trusts the push gate to cover its branch | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-762` binds the gate to the pushed commit with a Claude Code
`PreToolUse` hook that intercepts `git push`. It works, and its
verifier proved it against nine adversarial command forms.

It covers one channel. The hook fires on a **Bash tool call in a
session**; a push that reaches the remote by any other route never
meets it. Round 105 demonstrated that on the commit that added it:

```console
$ git log --oneline -1                 # the merge of UX-761 and UX-762
d580122 UX-762: the gate binds to the commit you push, not the branch
$ git log --oneline -1 origin/claude/build-optimization-audit-hk2xne
d580122
$ ls .gate-covered
ls: cannot access '.gate-covered': No such file or directory
```

`d580122` reached origin with no marker in the checkout at all — no
suite had covered it — and nothing refused. The session issued no
`git push`; the harness's own automation did, between turns. The
repository's other hooks share the shape and the exposure: CI pushes,
a person at a terminal, an editor's git integration, a `--no-verify`
equivalent — none of them route through a Bash tool call.

This does not make `UX-762` wrong. It makes its coverage a property of
the channel rather than of the branch, and the row does not say so.

## Required Fix

1. State the boundary where the gate is described — `fixing-guide.md`
   §3's item and the hook's own message — so a reader knows what the
   gate does *not* see. A guard whose coverage is unstated is read as
   total.
2. Decide whether a second, channel-independent check is worth it. The
   honest candidates: CI already re-runs the suite on the pushed
   commit and is the real backstop, in which case the hook's job is to
   catch the mistake *earlier* and its channel limit is acceptable; or
   a `pre-push` git hook, which covers every local route but must be
   installed per clone and cannot be enforced by a committed file.
   Measure the gap before building: how many pushes in rounds 103-105
   came from a channel the hook cannot see?

## Out of Scope

- The command-form gaps (`git -C x push`, `VAR=1 git push`,
  `command git push`) — `UX-762`'s verifier established those are
  shared with `no_bulk_add` and pre-existing, a different row.
- Making CI stricter (`UX-755`'s Out of Scope stands: CI is the side
  that is right).

## Acceptance Test

The documented gate says which channel it covers, and the measurement
of channel-external pushes over three rounds is recorded. Mutation: if
a second check is built, a push from outside a Bash tool call reds it
where today it lands silently.

## Outcome

**The gap, measured.** Round 102 closed with `af56022`
(reflog push 2026-09-06T18:08:31+00:00) and round 105 with `e513c31`
(reflog push 2026-09-07T13:57:44+00:00, its round-close commit). Every
ref update to `origin/claude/build-optimization-audit-hk2xne` strictly
after the first and up to and including the second (naive string
comparison on the timestamp drops the trailing `+00:00` and silently
miscounts by one at each end - counted with `datetime.fromisoformat`
instead):

```console
$ git reflog show --date=iso-strict origin/claude/build-optimization-audit-hk2xne > /tmp/r.txt
$ python3 -c "import re
from datetime import datetime as D
lo, hi = D.fromisoformat('2026-09-06T18:08:31+00:00'), D.fromisoformat('2026-09-07T13:57:44+00:00')
print(sum(1 for l in open('/tmp/r.txt') if (m := re.match(r'^\S+ refs/remotes/\S+@\{([^}]+)\}: ', l)) and lo < D.fromisoformat(m.group(1)) <= hi))"
41
```

41 push events landed in rounds 103-105. **Corrected by verification:**
the first cut read `docs/audits/agent-runs.md` for a `git push` row and,
finding none, called all 41 channel-external — but that ledger
structurally never carries a row for the session's own merging and
closing (`CLAUDE.md`: the session "judges, briefs and merges", it is
not a ledger row), so absence there is not evidence of absence -
fixing guide §5's proxy trap, the same shape as round 103's contention
misdiagnosis. `e513c31` (the round-105 close itself, inside the
window) is known to have been pushed by an explicit `git push -u
origin claude/build-optimization-audit-hk2xne` Bash call, so **at
least one** of the 41 went through the covered channel. The mix behind
the rest is not recoverable from committed material - `.gate-covered`
is gitignored and carries no history.

**The decision.** Unchanged, and it never needed the count to be zero:
CI on the pushed commit is the backstop; build nothing further. Partial
coverage still leaves a channel-independent check doing the work CI
already does, and a `pre-push` hook cannot be enforced by a committed
file (Required Fix's own framing).

**The close, measured.** The boundary is now stated in three places,
naming what is actually knowable rather than a false absolute:

```console
$ grep -c UX-767 .claude/hooks/gate_covers_push.py docs/contributing/fixing-guide.md \
  tests/unit/test_the_push_gate_states_its_channel.py
.claude/hooks/gate_covers_push.py:1
docs/contributing/fixing-guide.md:1
tests/unit/test_the_push_gate_states_its_channel.py:5
```

**Guard limit, stated plainly.** A text guard confirms a sentence's
substantive terms are present; it cannot confirm the sentence is
*true*. The first cut's guards checked only for the `UX-767` citation,
which a rewrite reversing the meaning ("this hook catches every push
on every channel") could keep - both passed it. The guards now check
the substantive terms (`SUBSTANTIVE_TERMS`) instead of the citation.

### Mutations verified red and reverted (4)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | drop `PreToolUse`/the substantive terms from the hook's docstring | `test_the_hook_docstring_states_the_boundary` | 1 of 4 failed |
| M2 | drop `Bash tool call`/the substantive terms from the fixing-guide sentence | `test_the_fixing_guide_states_the_boundary` | 1 of 4 failed |
| M3 | replace the hook's boundary paragraph with "catches every push on every channel", `UX-767` kept | `test_the_hook_docstring_states_the_boundary` | 1 of 4 failed |
| M4 | same reversal on the fixing-guide sentence, `UX-767` kept | `test_the_fixing_guide_states_the_boundary` | 1 of 4 failed |

All four applied to the real files (not an in-memory copy) and
reverted from the scratchpad copy, then re-verified green (4 passed).
No second, channel-independent guard exists to mutate per the
Acceptance Test's own conditional ("if a second check is built") — the
decision above is that none is built.

**`BGA_SKIP_SELECTOR=1`** on the commit: this row's new test file also
moves `fixing-guide.md`'s derived test-file count (same guard UX-766
hit); regenerating it is the orchestrator's, once, after every track's
new files land this round.
