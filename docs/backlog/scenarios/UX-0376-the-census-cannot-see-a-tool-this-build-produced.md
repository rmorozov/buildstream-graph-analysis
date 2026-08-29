# UX-376: the census cannot see a tool this build produced, and the spine policy believes it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-105 (measure the static-binary blind spot), UX-113 (--trace-spine=auto, guided by the census) | **Serves:** anyone whose project builds its own host tools | **Topic:** capture

## Motivation

`bga snapshot` runs `--trace-spine=auto`. `auto` asks the census whether
any element stages a statically-linked executable, and turns the ptrace
spine on only where the answer is yes. `census_project`'s own docstring
says what it reads: "the project's own `local` sources — the files on
disk before anything runs … a binary produced by the build" is not
visible to it.

That is the shape of a very ordinary BuildStream project: one element
builds a code generator, later elements build-depend on it and run it.
A fixture for exactly that — `hosttool.bst` produces one `-static`
executable, `consumer.bst` build-depends on it and runs it 200 times —
captured twice on the same tree:

```text
                              auto (the default)    --trace-spine=on
processes traced                              21                 221
consumer.bst                                   7                 207
codegen (the tool it ran)                 absent                 200
```

The default capture saw **7 of 207** processes in that element and none
of the 200 executions of the tool. What it printed while deciding:

```text
Census: 4 of 4 element(s) assessed, none with static binaries
        (the spine is not needed)
```

"The spine is not needed" is an unqualified sentence about a run in
which the spine was the difference between 21 processes and 221. The
report's own footnote does carry the caveat — "Binaries … produced by
the build are outside what this census can see (UX-105)" — but it is
printed under a heading that says nothing was missed, and the *policy*
acted on the census as though it were complete.

**The cost of the other answer is small, and measured.** The same
10-element, 6,090-process, fully dynamically-linked build, five paired
captures alternating:

```text
        wall (s)                        mean    processes
off     17.1  19.0  18.8  20.0  18.3    18.6        6,090
on      19.7  18.3  19.5  19.4  19.1    19.2        6,090
```

+3.2% at the mean, with ranges that overlap almost entirely (off
17.1–20.0, on 18.3–19.7), and an identical process count — the merge
correctly refuses to double-count a process both mechanisms saw. This
is one shape on one 4-core host at n=5 and is not a replacement for
`UX-112`'s factorial; it is enough to say the default is not being
bought with a large saving.

## Required Fix

The policy stops resting on a premise the census cannot check.

- **The census reports what it could not look at**, not only what it
  found. An element whose build-dependency closure includes an element
  this run *builds* has an unassessable sandbox, and `auto` treats
  unassessable as "turn the spine on" rather than as "no".
- **The capture-time sentence matches the verdict it can support.**
  "None with static binaries" becomes "none among what this census can
  read", and where an element is unassessable it says which and why.
- **A capture can detect the miss after the fact.** An element's own
  `build-commands` name the binaries it invokes; a name that appears in
  the commands and in no record for that element is the hook detecting
  its own absence, which `UX-105` said it could not do — and here it
  can, because the commands are in the graph the same snapshot holds.

Whether `auto` should simply become `on` is a separate call and is not
what this asks for: the measurement above is one workload, and the
honest fix is to stop the policy claiming a completeness it does not
have.

## Falsification

The fixture is the falsification: a project where one element produces
a `-static` executable and a later element runs it. Under the default
policy, assert that the capture either traces the tool's processes or
says in its own output that this element could not be assessed. Today
it does neither — it says the spine is not needed and misses 200 of 207
processes.

The other direction, so the fix is not "always on": a project whose
elements are all dynamically linked and stage no static binary still
gets `spine_traced: 0` under `auto`, and its capture-time sentence is
unchanged.

## Out of Scope

- The spine's price at scale (`UX-112`, `UX-129`). The five pairs above
  are context for the decision, not a restatement of those figures.
- Binaries arriving from a remote artifact cache, which is the other
  half of `UX-105`'s limit and needs a different instrument.
