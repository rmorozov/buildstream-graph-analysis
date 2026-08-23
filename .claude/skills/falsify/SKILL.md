---
name: falsify
description: Prove a new guard in this repository actually guards something - apply the mutation, confirm it landed, watch the guard go red, revert, watch it go green. Use after writing any test that asserts a claim about the code or the docs.
---

# falsify

A guard that has never been seen to fail is a guard nobody has tested.
The rule lives in
[`docs/contributing/fixing-guide.md`](../../../docs/contributing/fixing-guide.md)
§3; this is the procedure.

## The loop, per guard

```bash
cp <file> /tmp/<file>.bak                       # 1. keep the original
python3 - <<'PY'                                # 2. apply the mutation
import pathlib
p = pathlib.Path("<file>"); t = p.read_text()
assert "<old>" in t                             #    prove it will land
p.write_text(t.replace("<old>", "<new>"))
PY
python3 -m pytest tests/unit/<guard>.py -q -k <name>   # 3. must FAIL
cp /tmp/<file>.bak <file>                       # 4. revert
python3 -m pytest tests/unit/<guard>.py -q      # 5. must PASS
```

Step 2's `assert` matters: a `replace` that matched nothing is a
mutation that never happened, and a guard that stays green against a
mutation that never happened proves nothing at all.

One mutation per guard, and each mutation targets the *one* thing that
guard claims. If a single mutation reddens three guards, two of them
have not been falsified.

## Two failure modes this repository keeps producing

**The mutation that does not discriminate.** The guard goes red, but
for a reason unrelated to what it claims — a syntax error, a fixture
that no longer parses, a different assertion in the same test. Five
were caught this way and every one had to be redone. Read the failure
message and confirm it names the thing you broke. If it does not,
**reject the mutation and write a different one**; do not count it.

**The guard that matches its own explanation.** When a guard greps a
document for a phrase, it will find the phrase in the sentence that
argues for the phrase. Five instances in one round: the context-map
guard matched the paragraph quoting the bad map as its evidence; the
deferral guard matched the filing's own list of deferral phrases; the
round-28 guard matched a filing's Motivation citing the mechanism as
evidence. The rule that falls out: **say which part of the document is
the subject and which part is the argument, and read only the
subject** — a section, a fenced block, a named heading. Then falsify by
planting the text in the *argument* half and confirming the guard still
fails.

**The revert that resets past your own work.** `git checkout -- <file>`
throws away everything uncommitted in that file, not just the mutation.
One round lost a whole transport that way and only noticed because the
guard stayed red. Use a `/tmp` copy, or commit before you falsify.

## What goes in the Outcome section

One line naming every mutation and that it went red:

```text
**Mutations verified red and reverted (6):** a listed file that does not
exist; one file in two tiers; the collection hook stopping applying
markers; ...
```

And a paragraph for any guard of yours that did not discriminate — what
it passed on, and what it checks now. Those paragraphs are the most
re-read part of this backlog.
