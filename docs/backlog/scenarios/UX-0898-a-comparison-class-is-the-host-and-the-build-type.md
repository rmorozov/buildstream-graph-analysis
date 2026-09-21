# UX-898: a comparison class is the host class and the build type together

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-234 (host classes), UX-250 (the contract-move refusal) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — CI will keep bundles under build numbers whose form already separates nightly (`27.0.0.<seq>`) from review (`27.0.999.<seq>`) | **Serves:** R4 (a gate that compares like with like), R5 and R7 (an aggregate that is not two populations averaged) | **Topic:** contracts | **Area:** bga | **Shape:** judgement

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

## What the owner answered (2026-09-20)

The types in the field are **night**, **review** and **guard** (an
asynchronous build from `main` every n hours), and there may be others,
so the value is **free text a pipeline declares** rather than an enum
this repository maintains. A typo therefore creates a third class rather
than an error, which is the cost of the choice: the refusal names both
values it saw, so a typo is visible the first time it splits a
population.

There is a second axis under it — the **variant** (per instruction set,
release-with-symbols, address sanitizer, coverage) — filed separately as
`UX-903`, because a variant changes what the build *does* and a type
changes when and why it ran. The class this row establishes is the pair,
with the variant's half landing with that row.

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

**The gap, measured.** At `395ebdc`, `grep -rc build_class bga/ tools/`
returns no hits. A review capture declaring `{"type": "review",
"variant": {"sanitizer": "address"}}` gated against an untyped nightly:

```text
$ bga compare /tmp/gapruns/review /tmp/gapruns/night --fail-on-regression
exit 0, and zero mentions of a build class in the output
```

**The close, measured.** The same pair here:

```text
Mixed build class gate FAILED: baseline declares review · sanitizer=address
and candidate declares night. ... Pass --blend to state the mixed claim
yourself.                                                          exit 6
$ ... --blend                                                      exit 0
```

The aggregate refuses the same mix (`check: mixed_class_aggregate`,
naming both populations); `--blend` publishes it with `mixes: 2`. A
store whose rows declare nothing keeps `check: cross_host_aggregate`
and today's sentence, and its class entries carry no `build_class`.

**The shape.** `bga/buildclass.py` mirrors `hostinfo`'s API and the
class is `{type, variant}` inside `run-context/v9` — a permitted
addition under Part 32's rule, so no id moved, `comparison_movement`
stays silent and every old capture still compares. Declared by
`--build-type` on either run-context producer or `$BGA_BUILD_TYPE` in
the capture's environment, which `bga snapshot` carries through without
new plumbing (the `BGA_JOBSERVER_MODE` precedent, `UX-851`).

**What is not byte-identical**, stated rather than glossed: `compare
--format json` gains one key. `build_class_comparison` is always
written — `{"status": "absent"}` where neither run declared — the shape
`host_comparison` already has, so it is in `compare/v2`'s
`bga:always_written`, not `required`. The aggregate document and the
report header, which are what the Acceptance Tests name, were diffed
against `395ebdc` for undeclared input: identical.

**The mutation table.** Each applied, confirmed landed, the guard
watched red, reverted, watched green:

| mutation | guard |
|---|---|
| the type comparison is case-insensitive | red — `test_case_is_a_difference_not_a_match` |
| the refusal message drops the type | red — `test_two_types_refuse_with_exit_6` |
| absent is treated as equal to present | red — `test_one_side_declaring_is_unknown_and_not_a_difference` |
| only the type is compared (`UX-903`) | red — `test_one_type_and_two_variants_is_a_difference` |
| the message drops the variant (`UX-903`) | red — `test_the_sentence_names_the_dimension_and_both_values` |
| an absent dimension matches a declared one (`UX-903`) | red — `test_a_dimension_present_on_one_side_only_is_a_difference` |

**The deviation.** Three:

1. **A fourth status, `absent`.** Both runs declaring nothing is every
   capture in history. `hostinfo` says "host unknown" there because a
   manifest is *collected*; a build class is *declared*, so absence is
   the norm. `absent` renders and refuses nothing, which is what makes
   the Acceptance Test's byte-identity true rather than approximate.
2. **`--blend` on `compare`**, as the Acceptance Test asked by name,
   rather than a second `--allow-*`. `--allow-cross-host` keeps its own
   gate.
3. **The aggregate's `host_class` still names the machine alone**, with
   `build_class` beside it. The grouping is on the pair; only the label
   is split, because widening a field consumers read is `UX-190`'s drift.

**Registers this move touched**, each derived and re-run: the
environment inventory (two rows), the touching spread (562 → 564 files,
max 157 → 159), the selector ceiling, Part 32's line range and the line
the fixing guide cites inside it, and the schema-walk key count (303 →
307). A contract move is six derived figures wide here.

**Tier.** This row's guard file measured 1.09s and is `medium`;
`UX-903`'s measured 0.73s and stays `small` by the floor.
