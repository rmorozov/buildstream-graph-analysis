# UX-661: the second copy of the topic set orders a release body

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-658 (which made the first three copies one), UX-634 (which built the release body) | **Serves:** anyone adding a topic and expecting the release notes to know about it | **Found by:** round 89, track X, counting the copies UX-658 was about | **Topic:** guards | **Shape:** judgement

## Motivation

`UX-658` made the topic taxonomy one statement: `TOPIC_ORDER` in
`tools/dev_close_task.py`, imported by the guard rather than repeated.
It found three copies and unified them. There is a fourth, and it is
the same **set** in a different **order**:

```console
$ python3 scratchpad/copies.py
dev_close_task.TOPIC_ORDER   ('capture', 'analysis', 'contracts', 'viewer', 'cli', 'store', 'docs', 'guards')
bga_release_notes.TOPIC_ORDER ('contracts', 'cli', 'analysis', 'capture', 'viewer', 'store', 'guards', 'docs')
same set  : True
same order: False
```

`tools/bga_release_notes.py:36` carries its own eight, with a comment
that is a real argument for the order it has — *"a reader scanning for
'what changed for me' wants the contract and CLI news first and the
process news last; alphabetical would bury `contracts` under `cli`."*
So this is not a copy somebody forgot to delete. It is a second
opinion about **ordering** that happens to restate the **membership**.

And it fails the same way the index did. Line 98 is

```python
ordered = ([topic for topic in TOPIC_ORDER if topic in grouped]
           + sorted(set(grouped) - set(TOPIC_ORDER)))
```

which sorts an unlisted topic after the eight rather than refusing it —
exactly what `UX-658` found the index's table doing with `process`. A
ninth topic would have printed in a release body too, silently, in the
wrong place. The comment even names the word: *"process news last."*

`test_the_release_body_is_generated.py` reads this module and is green,
because it checks the body against the rows it was given rather than
against the taxonomy those rows may declare.

## Required Fix

Membership has one home and ordering has another. `bga_release_notes`
takes its **set** from `dev_close_task.TOPIC_ORDER` — the import
`UX-658` established — and keeps its own **sequence** as a permutation
of it, with a clause asserting that the two are the same set. A topic
added in one place is then in the release body's vocabulary the same
day, in the position its own argument asks for.

Which module owns membership is not obvious and is worth stating
rather than assuming: `dev_close_task` is where `UX-658` put it and
where the guard reads it, so this row proposes it stays there and
`bga_release_notes` becomes a consumer.

## Out of Scope

- The release body's ordering argument — it is correct and this row
  keeps it. Only the membership half moves.
- `build/lib/bga/_tools/`'s two copies — declined because they are
  build artefacts of these same two files rather than sources, so
  they follow whatever the originals do and editing them would be
  editing generated output.
- Whether an unlisted topic should refuse rather than sort last in the
  release body. Declined because `UX-658` made the taxonomy closed at
  the task file, so nothing can reach here unlisted any more; if that
  guard is ever removed this becomes live again.

## Acceptance Test

`set(bga_release_notes.TOPIC_ORDER) == set(dev_close_task.TOPIC_ORDER)`
is asserted rather than true by coincidence, and adding a topic to
`dev_close_task.TOPIC_ORDER` alone reddens a clause naming the release
module — shown by adding one.

## Outcome

🟢 Done — with a deviation from the proposed mechanism, argued below.

The membership half is now asserted rather than true by coincidence.
`test_the_release_body_is_generated.py` reads both modules and requires
the release ordering to be a **permutation** of the taxonomy: same set,
this module's own sequence, each topic named once. The failure names
the release module and the remedy rather than the sets alone.

### Acceptance

The mutation the row names — a ninth topic added to
`dev_close_task.TOPIC_ORDER` and nowhere else:

```console
E   AssertionError: tools/bga_release_notes.py states the release ordering,
E   but membership belongs to dev_close_task.TOPIC_ORDER:
E       only in the release body: []
E       only in the taxonomy: ['process']
E     Place the new topic in bga_release_notes.TOPIC_ORDER, where its
E     position is a decision rather than a default.
1 failed, 9 deselected
```

`process` is the same word `UX-658` found in the index, and the same
word this module's own comment uses when it argues for its order.

### Mutations

| mutation | guard |
|---|---|
| a ninth topic in the taxonomy alone | the permutation clause, naming the release module |
| a topic repeated in the release order | the each-named-once clause |

### Deviation

**The Required Fix asked for an import; this is a guard.** The proposal
was that `bga_release_notes` take its set from
`dev_close_task.TOPIC_ORDER` and become a consumer. It is not doing
that, and the reason is packaging rather than preference:

- `bga_release_notes` is a **shipped** module (`bga._tools`), and
  `pyproject.toml:120-126` records that the tools import each other
  *relatively* so the package works under either name. Every existing
  cross-tool import in `tools/bga_*.py` is relative **and inside a
  function** (`bga_snapshot.py:163`, `bga_doctor.py:208`), because a
  module-level relative import breaks `python3 tools/bga_release_notes.py`
  run from a checkout.
- A module-level constant needs its value at import time, so being a
  true consumer would need a `try: from .dev_close_task import ...
  except ImportError:` pair — an import mode this repository uses
  nowhere, added to a shipped module, for a Low row.

The row's own Acceptance Test is met exactly as written without it:
the equality is asserted, and adding a topic to the taxonomy alone
reddens a clause naming the release module. What is *not* achieved is
the "same day" clause — a topic added to the taxonomy reddens a guard
telling you to place it, rather than appearing in the release body by
itself. That is arguably the better behaviour, since the comment this
row preserves is an argument about *where* a topic belongs, and a
default position is what `UX-658` filed against. If a later round wants
the import anyway, it is a two-line change and this paragraph is the
argument to overturn.
