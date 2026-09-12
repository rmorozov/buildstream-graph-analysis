# What a projection is, and why it is a bound (`UX-230`, `UX-74`)

Moved from [`docs/design/architecture.md`](../architecture.md)'s "What
a projection is, and why it is a bound" chapter (`UX-807`); the
non-summing arithmetic worked example (the freedesktop-sdk table)
stays there, where its guard reads it.

`bga whatif` and the page's what-if panel answer one question — *what
would the build drop to if these were fixed together* — and the answer
is a **bound**, not a forecast. Two things make it one, and both are
stated in every `whatif/v1` answer (`bga/whatif.py`'s `CONVENTION`) and
in [`../../guides/cli.md`](../../guides/cli.md); this is where the reasoning
behind them lives.

**"Fixed" means instant.** The projection zeroes each chosen element's
measured duration and recomputes the longest path. A real fix that
makes an element *faster* rather than instant lands under the figure; a
fix that changes the graph — splitting an element, moving a dependency,
caching a source — is not modelled at all. So the number is a ceiling
on what the selection can be worth over this run's durations. A
re-capture is still the ground truth.

Being in **series** is what makes savings compose — shortening two
links of one chain shortens the chain by both. Being **parallel** is
what makes them not — the other chain was never binding.

And summing is not merely optimistic: it is wrong in **both**
directions. On the committed `examples/06` run, `codegen.bst` is worth
**nothing** alone and the pair is worth more than either:

```text
$ bga whatif examples/06-…/run --element core.bst --element codegen.bst
  Makespan 43.200s -> 24.150s (saves 19.050s)
  Their individual savings add up to 12.050s, which is not what they are
  worth together (19.050s) - what one fix is worth depends on the others.
```

`codegen.bst` sits on the chain that becomes binding the moment
`core.bst` is fixed, so an element a reader would strike off the list
today is worth seven seconds tomorrow. That is the same effect the
optimization horizon (`UX-74`) projects forward, seen from one
selection: what a fix is worth is a property of the set it is in, and
no per-element table can carry it.

`compute_joint_saving` (`bga/graph/edg.py`) is the one recompute, and
`whatif/v1` publishes `sum_of_individual_us` **beside**
`joint_saving_us` rather than instead of it, so the difference is
visible in the payload rather than reproduced by the consumer.
