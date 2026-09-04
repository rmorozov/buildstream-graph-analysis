# UX-661: the second copy of the topic set orders a release body

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-658 (which made the first three copies one), UX-634 (which built the release body) | **Serves:** anyone adding a topic and expecting the release notes to know about it | **Found by:** round 89, track X, counting the copies UX-658 was about | **Topic:** guards

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
