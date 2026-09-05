# UX-385: a capture cannot detect the binary it never saw

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-376 (the policy that made this the remaining half) | **Serves:** anyone reading a capture taken with the spine off | **Topic:** capture | **Area:** tools

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

## Outcome (round 62, 2026-08-29) — 🟢 Done

### The gap, measured

`plane2/v3` now carries `commands_not_observed`: per element, the
binaries its own commands name, the binaries its records name, and the
difference. On `UX-376`'s fixture with the spine off:

```text
consumer.bst  named             codegen, mkdir
consumer.bst  observed          mkdir, sh
consumer.bst  named_not_observed  codegen
elements_with_gap             ['consumer.bst']
```

and with the spine on, `elements_with_gap` is empty — the same fixture,
the same commands, the difference being only what the instrument saw.
That is the hook detecting its own absence from data in the same
capture, which is the half `UX-105` and `UX-376` left open.

### After

**Evidence, not a verdict**, which is the whole of the published
wording. The key is `named_not_observed` and the note names the false
positive a reader meets first — a command under a shell conditional
that did not fire is named and legitimately never ran. A clause holds
the note to it.

**What the comparison can and cannot read** is measured rather than
asserted. The leading token of each line is what it compares:

```text
codegen --out x.c                      -> codegen
cd build && make -j4                   -> make          (builtin, then)
for f in *.c; do gcc -c $f; done       -> gcc           (inside a loop)
if [ -f x ]; then codegen x; fi        -> codegen       (inside a test)
CC=clang cc -c x.c                     -> cc            (env prefix)
/usr/bin/protoc --cpp_out=. a.proto    -> protoc        (absolute path)
echo hi / set -e / cd src              -> (nothing)     (builtins)
%{make} install                        -> commands_not_read += 1
$(which codegen) x                     -> commands_not_read += 1
```

A name assembled at runtime is out of reach by construction, so it is
**counted and published** rather than guessed or silently dropped —
"named nothing" and "could not read what it named" are different facts.

The observed set comes from `Plane2Fold.observed_binaries()`, which
delegates to the binary counter that has already visited every record.
Reading `binary_cost` instead would have been wrong twice over: it is
capped at `top_n`, so a tool that ran once would look unobserved, and
`UX-297` removed the second walk this would have reintroduced.

### Falsification

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | the comparison never fires (`named_not_observed` always empty) | 2 of 18 |
| M2 | unresolvable names guessed instead of counted | 4 of 18 |
| M3 | leading keywords skipped once rather than consumed | 1 of 18 |
| M4 | the loop header is not dropped, so `for f` reports `f` | 2 of 18 |
| M5 | the observed set is empty (as if read from the capped block) | 4 of 18 |
| M6 | a missing project reads as "looked and found nothing" | 1 of 18 |
| M7 | the note drops its "not a verdict" hedge | 1 of 18 |

Baseline: 18 passed. `make lint` clean.

**M7's first run was a no-op and the sweep is what showed it** — the
search string assumed a quote boundary the implicit concatenation does
not have, so 18 passed and nothing had changed. Re-applied against the
real text it reddens one clause. A mutation that does not apply looks
exactly like a guard that does not discriminate, which is why the
applied diff is worth checking rather than the count alone.

### Deviation from the Required Fix

- The item says "published in `plane2/v2`". It is `plane2/v3`:
  `UX-384` landed earlier in this round and moved the contract, so this
  block ships in the new version rather than the one the filing named.
