# UX-385: a capture cannot detect the binary it never saw

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-376 (the policy that made this the remaining half) | **Serves:** anyone reading a capture taken with the spine off | **Topic:** capture

## Motivation

`UX-105` established that the LD_PRELOAD hook "cannot detect its own
absence" and `UX-376` made `--trace-spine=auto` stop *assuming* it
could. Neither closes the case where the spine is off — by policy, by
`--trace-spine=off`, or on an older capture — and a statically-linked
binary ran anyway.

It is detectable, and the snapshot already holds both halves. An
element's `build-commands` name the binaries it invokes; `binary_cost`
names the binaries its records show. On the fixture `UX-376` was built
from, with the spine off:

```text
consumer.bst build-commands name   codegen
consumer.bst records name          sh, mkdir
```

`codegen` appears in the commands and in no record for that element.
That is the hook detecting its own absence — from data in the same
capture, and only for the element it happened to.

## Required Fix

A per-element check comparing the leading binaries of each
`build-commands` line against the binaries that element's records
carry, published in `plane2/v2` as evidence rather than as a verdict —
a command that ran under a shell conditional, or one the element
inherits from a `.bst` include, is a false positive and must read as
"named and not observed" rather than "missed".

## Falsification

The `UX-376` fixture captured with `--trace-spine=off` publishes
`codegen` as named-and-not-observed for `consumer.bst`, and the same
fixture with the spine on publishes nothing.

## Out of Scope

- The spine policy. `UX-376` decided when the spine runs; this is about
  what a capture can say once it has not.
- Parsing shell. The leading token of each command line is what this
  compares, and a command assembled at runtime is out of reach by
  construction — which the published wording has to admit.
