# UX-903: a variant is a second axis under the build type, and nothing records it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-898 (the type) | **Found by:** the 2026-09-20 rollout thread — the owner's pipeline builds per instruction set, release-with-symbols, address sanitizer and coverage, and every one of those is a different build of the same tree | **Serves:** R4 (a gate that does not compare a sanitizer build against a release one), R5 and R7 (a population that is one thing), R2 (whose element's cost is a different number per variant) | **Topic:** contracts | **Area:** bga | **Shape:** judgement

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
