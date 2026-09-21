# UX-903: a variant is a second axis under the build type, and nothing records it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-898 (the type) | **Found by:** the 2026-09-20 rollout thread — the owner's pipeline builds per instruction set, release-with-symbols, address sanitizer and coverage, and every one of those is a different build of the same tree | **Serves:** R4 (a gate that does not compare a sanitizer build against a release one), R5 and R7 (a population that is one thing), R2 (whose element's cost is a different number per variant) | **Topic:** contracts | **Area:** bga | **Shape:** judgement

## Motivation

`UX-898` makes the build *type* — night, review, guard — part of what
makes two runs comparable. Underneath it sits a second axis the field
already has and the tool has no word for: the **variant**. The owner's
pipeline builds per instruction set, and separately as
release-with-symbols, under an address sanitizer, and for coverage.

These are not the same build measured twice. A sanitizer build's
elements are slower by a factor that belongs to the sanitizer, a
coverage build's are slower by a different one, and a second
instruction set is a different toolchain doing different work. Pooled
into one population they produce a median that describes no build
anyone runs, and a gate reading it reports a regression every time the
mix shifts.

The two axes are genuinely different: a **type** says when and why a
build ran, a **variant** says what it did. A nightly sanitizer build and
a review sanitizer build share a variant; a review sanitizer build and a
review coverage build share a type. Both halves have to be declared for
either to mean anything.

## Required Fix

A declared variant beside `UX-898`'s type, with the same three
properties — recorded rather than guessed, part of comparability, and
refused when mixed rather than averaged — and the class becoming the
pair `(type, variant)`. Absent stays today's behaviour, so an old store
still compares.

Then one thing the pair buys that neither half does alone: a report
that names its own variant, so a reader who opens a capture knows
whether the durations in front of them are a sanitizer's.

## Decomposition

surfaces: the same set `UX-898` names — the run context, the host manifest's identity block, `bga/compare.py`, `bga/store_aggregate.py`, the contract in Part 32 — plus the report header that prints the class
guards: two runs of one type and different variants (refused), two matching (compared), one declaring neither (today's behaviour), and an aggregate over a mixed-variant store (refused, naming both populations)
gap: whether the variant is one free-text field or a small set of named dimensions (instruction set, sanitizer, coverage can all be true at once); one field is cheaper, several are what the owner's matrix actually is
track: with `UX-898`, one contract move rather than two
gate: with `UX-898`

## Out of Scope

Modelling what a variant costs — "a sanitizer build is 2.3x" is a
finding some later row may earn from a real population, and it is not
this one. Any inference of the variant from the element set.

## Acceptance Test

Two runs with the same type and different variants are refused with the
class refusal's exit code and a message naming both; the same two with
`--blend` compare; an aggregate over a mixed store refuses. The report
header prints the class when it is declared and is byte-identical to
today when it is not. Mutations: compare only the type (the
different-variant pair must still be refused), drop the variant from the
message (the guard names it), treat absent as matching declared (must
not).

## Outcome

Landed with `UX-898` in one commit — the Decomposition of both rows
said one contract move rather than two, and the class is the pair, so
half of it is not a shippable state.

**The open question, answered.** *One free-text field or several named
dimensions?* **Several named dimensions**, because the owner's matrix
is per instruction set *and* release-with-symbols *and* sanitizer *and*
coverage: `arch=aarch64` with `sanitizer=address` is one build, and an
opaque `aarch64-asan` string cannot answer "every sanitizer build,
whatever the arch" without `bga` parsing a convention it did not
define. Dimension names are free text the pipeline picks, so no enum
is maintained here either. `--variant arch=aarch64 --variant
sanitizer=address`, repeatable; `$BGA_BUILD_VARIANT` takes the same
pairs comma-separated. A `--variant` with no `=` is refused naming the
entry: inventing the dimension name is how `asan` and `sanitizer=asan`
become two classes.

**The gap, measured.** At `395ebdc` the word "variant" appears nowhere
in `bga/` or `tools/`; a sanitizer review build and a coverage review
build were one population with no way to say otherwise.

**The close, measured.**

```text
$ bga compare asan-run coverage-run --fail-on-regression
Mixed build class gate FAILED: baseline declares review · arch=x86_64 ·
sanitizer=address and candidate declares review · arch=x86_64 ·
coverage=on. ...
exit 6
$ ... --blend                                    exit 0
$ aggregate over a mixed-variant store  refusal check mixed_class_aggregate,
                                        naming sanitizer=address and coverage=on
```

The report header prints `Build class: review · arch=x86_64 ·
sanitizer=address` when declared, and nothing at all when not — the
reader who opens a capture now knows whether the durations in front of
them are a sanitizer's.

**The mutation table.** Applied, confirmed landed, guard watched red,
reverted, watched green:

| mutation | guard |
|---|---|
| only the type is compared | red — `test_one_type_and_two_variants_is_a_difference` |
| the message drops the variant | red — `test_the_sentence_names_the_dimension_and_both_values` |
| an absent dimension matches a declared one | red — `test_a_dimension_present_on_one_side_only_is_a_difference` |

`UX-898`'s three mutations are in its own Outcome; two of them
(case-insensitivity, the dropped type) redden guards in this file too,
because the class is the pair.

**The deviation.** The filing's Required Fix asked for "a report that
names its own variant". It names the whole class — type and variant
together — because a header that said `sanitizer=address` while
withholding `review` would be the same half-a-class the rest of this
row rejects. `_format_build_class` returns `None` rather than
"undeclared" for a capture that declared nothing, which is what keeps
the byte-identity clause of the Acceptance Test literally true.
