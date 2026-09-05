# UX-376: the census cannot see a tool this build produced, and the spine policy believes it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-105 (measure the static-binary blind spot), UX-113 (--trace-spine=auto, guided by the census) | **Serves:** anyone whose project builds its own host tools | **Topic:** capture | **Area:** tools

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

## Outcome

Round 61. The census now answers for what it could look at, and `auto`
treats what it could not as needing the spine — which is the rule
`census_spine_verdicts` was *already* written to, and had no
unassessable elements to apply.

**The rule.** An `import` element stages its sources verbatim, so the
census sees exactly what its sandbox will hold. Every other kind runs
commands and produces something new. An element whose declared build
closure contains a non-`import` element therefore has a sandbox that
cannot be assessed before the build; `census_project` publishes
`assessable`, `unassessable_because` (naming which dependency) and
`elements_unassessable`, kept apart from `elements_at_risk` because the
two are different facts a reader acts on differently.

**Measured on the fixture, through the real tool, with no flag:**

```text
                          before, auto   --trace-spine=on   after, auto
processes traced                    21                221           207
consumer.bst                         7                207           207
codegen (the tool it ran)       absent                200           200
```

and the sentence the capture prints while deciding:

```text
before  Census: 4 of 4 element(s) assessed, none with static binaries
        (the spine is not needed)
after   Census: 2 of 4 element(s) assessed, none of those staged a static
        binary; 2 stage what this build produces and cannot be assessed
        before it runs - those get the spine
```

"The spine is not needed" was an unqualified claim about a run in which
the spine was the difference between 21 processes and 221.

**Not "always on".** A project whose elements stage only imports keeps
`spine_traced: 0` and keeps `UX-160`'s original sentence — the clause
holding that is what makes this a policy fix rather than a surrender.
In a deep project most elements do become unassessable, which is the
honest consequence: the census reads local sources, and in a project
that builds its own tools most sandboxes are mostly built. The five
paired captures in the filing put the price of that at +3.2% of the
mean with overlapping ranges.

**The third Required Fix bullet is deferred.** "A capture can detect the
miss after the fact" — comparing an element's own `build-commands`
against the binaries its records name — is a second instrument with its
own failure modes, and the Falsification does not test it. Filed as
`UX-385` rather than half-built here.

### Falsification run

Six mutations against the committed tree. All six caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | every element is assessable again — the defect | 6 clauses |
| M2 | an `import` dependency also counts as produced | 6 clauses, including the not-always-on one |
| M3 | the policy ignores assessability | `test_an_unassessable_element_gets_the_spine` |
| M4 | the sentence claims the spine is unneeded again | `test_it_does_not_claim_the_spine_is_unneeded` |
| M5 | the sentence drops the unassessable clause | 2 clauses |
| M6 | unassessable is folded into `elements_at_risk` | `test_unassessable_is_not_folded_into_at_risk` |

M1 and M2 redden the same six clauses from opposite directions —
nothing unassessable, and everything unassessable — which is what makes
the pair worth having: a rule that fires always is as wrong as one that
never fires, and the second is the one a "just turn the spine on" fix
would produce.

### Verification Log

```text
$ python3 -m pytest tests/unit/test_the_census_says_what_it_could_not_see.py -q
9 passed in 0.23s

$ cd <hosttool fixture> && bga snapshot -- bst build all.bst
Census: 2 of 4 element(s) assessed, none of those staged a static binary;
2 stage what this build produces and cannot be assessed before it runs -
those get the spine
...
process_count  207
by_element     {'consumer.bst': 207}
by_binary      codegen: 200
```

Tiered small on landing at 0.23s.
