# UX-898: a comparison class is the host class and the build type together

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-234 (host classes), UX-250 (the contract-move refusal) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — CI will keep bundles under build numbers whose form already separates nightly (`27.0.0.<seq>`) from review (`27.0.999.<seq>`) | **Serves:** R4 (a gate that compares like with like), R5 and R7 (an aggregate that is not two populations averaged) | **Topic:** contracts | **Area:** bga | **Shape:** judgement

## Motivation

`bga` already refuses to blend host classes: a store spanning two of
them exits rather than averaging them, because a queue over two service
times is two queues. A nightly and a review build differ at least as
much — different targets, a different cache state, often a different
agent — and the tool has no vocabulary for that difference at all. A
store holding both produces one median that describes neither, and the
seconds-slower gate `UX-899` asks for would compare a review build
against whichever run happened to be previous.

The rollout supplies the missing key rather than asking bga to infer it:
the build number's own form carries the type. What the tool lacks is a
place to put it and a rule about what it forbids.

## Required Fix

A declared **build type** on a run, recorded at capture time and carried
in the run's identity beside the host class, with the same three
properties the host class already has: it is recorded rather than
guessed; it is part of what makes two runs comparable; and a mixed
population is refused with its own exit code rather than averaged.
`--blend` is the existing escape hatch and keeps its meaning.

Where the type is absent — every capture taken before this row — the
behaviour is today's, so an old store still compares.

## Decomposition

surfaces: `tools/bst_run_context.py` and `bga/hostinfo.py` (the declared value), `bga/compare.py` (`_check_comparability`), `bga/store_aggregate.py` (the population), the run-context contract in Part 32, and the CLI flag that declares it
guards: two runs of different declared types (refused), two of the same type (compared), one run with no type against one with (today's behaviour), and an aggregate over a mixed store (refused, exit as for host classes)
gap: whether the type is free text the user declares or an enum; free text risks a typo becoming a third class, an enum risks not fitting a pipeline nobody has seen yet
track: session's own — the refusal semantics are a contract decision
gate: before `UX-899`, which depends on the class being real

## Out of Scope

Parsing the owner's build-number format inside bga. The number is the
pipeline's; the type is declared on the command line or in the capture's
environment. Anything about where bundles are stored (`UX-900`).

## Acceptance Test

Two runs declaring different types are refused by `compare` with the
host-class refusal's exit code and a message naming the types; the same
two with `--blend` compare. `snapshot --aggregate` over a store holding
both refuses and names the two populations. A store of untyped runs
behaves exactly as today, byte-identically. Mutations: make the type
comparison case-insensitive (the refusal for `Nightly` vs `nightly`
should be argued, not accidental); drop the type from the refusal
message (the guard names it); treat absent as equal to present (two runs
one of which is typed must not be refused).

## Outcome
