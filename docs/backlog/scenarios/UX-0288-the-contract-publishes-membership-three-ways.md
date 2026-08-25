# UX-288: the contract publishes membership three ways

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-268 | **Serves:** R5 and R7 — the payload consumers — and every reader of the page | **Topic:** contracts

## Motivation

Filed from Direction 14. Measured on the 1,202-element synthetic run,
in `analyze/v1` itself rather than in the page:

```text
signals.leaf_analysis.leaves                 135 uids
signals.leaf_analysis.leaves_detail          135 uids   identical to leaves: True
structural.deferrability.{deferrable,non_}   135 uids   identical to leaves: True

signals.critical_path                         14 uids
signals.critical_path_detail                  14 uids   identical: True

signals.element_durations                  1,202 uids
   critical path is a subset of it: True
   leaves       is a subset of it: True
```

The same element membership is published **three times** for leaves and
**twice** for the critical path, and every one of those populations is a
subset of the single element table the run already carries.

The page renders every copy, which is correct of it and is how the
duplication became visible: 19 tables drawing 13 distinct populations,
with seven pairs at 100% overlap.

**A consumer cannot tell which copy is authoritative.** If `leaves` and
`Object.keys(leaves_detail)` ever disagree, `analyze/v1` says nothing
about which one a reader should believe, and nothing in the tool would
notice — there is no guard that they match, because nothing says they
must.

The pattern that is right already exists in the same payload:
`signals.blast_radius` carries `is_leaf` **per element**. Membership as
a field on the element record, rather than as a list beside it.

## Required Fix

1. The two exact duplicates go: `signals.critical_path` (identical to
   `critical_path_detail`'s uids, in order) and `leaf_analysis.leaves`
   (identical to `leaves_detail`'s keys). Each is a list whose content
   is already published beside it.
2. `structural.deferrability`'s two uid lists are **not** an exact
   duplicate — measured, they partition the leaves by a duration-risk
   rule that disagrees with `is_potentially_deferrable` by design (8
   against 134 on the 1,202-element run). The dedup there is to publish
   the **per-leaf `deferral_risk`** the code already computes and
   currently drops (`risk_keys=0` in the payload), so the lists become
   filters over a field rather than a third copy of the membership.
3. Membership becomes a field where a list is genuinely a predicate over
   the elements — `is_leaf`, `on_critical_path`, `path_index` — rather
   than a list published beside the records.
4. `analyze/v1`'s version moves, because fields are removed rather than
   added.
   The versioning rule is in `architecture.md`; this is exactly the case
   it was written for.
5. A guard that no two published fields carry the same element set. It
   is a cheap check and it is the one nothing currently makes.

## Out of Scope

- Changing what any of these fields *mean*. `deferrability` and
  `leaf_analysis` answer different questions about the same population;
  this is about publishing the population once.
- The page's rendering of them, which is `UX-289` and is unsafe before
  this lands: deduplicating the page while the payload still publishes
  three copies puts the two into disagreement, which the viewer axis has
  refused since `UX-193`.

## Acceptance Test

No two fields in `analyze/v1` carry identical element sets, asserted by
a guard on a real run. The critical path and the leaves are each
reachable as a filter over the element records, and the text report and
the page name the same elements as before.

## Outcome

🟢 Done (round 38). `analyze/v2` publishes each element selection once.

**The acceptance test, run for real.** The guard discovers populations
by walking the payload, so this is its own sweep over the committed
macro/micro run, before and after — `before` is `HEAD` in a throwaway
worktree, so both numbers come from the same fixture:

```text
v1  populations >= 2 elements: 29    clashes: 2
      signals.critical_path_detail  vs  signals.critical_path   (10 elements)
      bottleneck.choke_points       vs  choke_point_impact       (9 elements)

v2  populations >= 2 elements: 27    clashes: 0
```

**What went, and what each reader uses instead:**

| removed | it duplicated | the projection |
|---|---|---|
| `signals.critical_path` | `critical_path_detail`'s uids, in order | `schemas.critical_path_uids` |
| `leaf_analysis.leaves` | `leaves_detail`'s keys | `keys(leaves_detail)` |
| `deferrability.{deferrable,non_deferrable}_leaves` | the leaf membership, a third time | `deferral_risk` per leaf |
| `bottleneck.choke_point_impact` | `choke_points`, valued | `choke_points[].downstream_count` |

**The deferrability lists were nearly removed as an exact duplicate and
are not one.** Measured before touching them, they partition the leaves
by a duration-risk rule that disagrees with `is_potentially_deferrable`
by design — 8 against 134 on the 1,202-element run. The *membership* was
the third copy; the split was information, and the tool had been
computing it and dropping it (`risk_keys=0` in the payload). It is
published now as `deferral_risk` on each leaf, so the lists become a
filter over a field rather than a third copy of the population.

**A fourth duplicate the acceptance test found**, not in the filing:
`bottleneck.choke_points` (nine ranked uids) and `choke_point_impact`
(the same nine, valued). One ordered list of records now carries the rank
*and* the value — the shape `critical_path_detail` already uses, and the
one [`UX-283`](UX-0283-the-bottleneck-view-names-elements-you-cannot-reach.md)
asks the page for. The text report prints the same names in the same
order, through `schemas.choke_point_uids`.

**`test_section_stage_gating` caught a real design defect in the fix.**
The first version joined `deferral_risk` from the structural stage into
the diagnostics leaf record, which made the answer depend on which
sections were asked for: `--section diagnostics` published `None` where
a full run published `medium`, for the same leaf of the same run. The
rule is extracted to `structural.models.deferral_risk_for`, reads only a
task's kind and duration, and both stages apply it.

**Falsification.** Six mutations, each asserted to land before the suite
was trusted, each reddening the test it was aimed at:

```text
M1 re-add signals.critical_path      -> 2 failed   (sweep + named fields)
M2 re-add leaf_analysis.leaves       -> 2 failed
M3 revert ANALYZE to analyze/v1      -> 1 failed
M4 critical_path_uids drops v1 read  -> 1 failed
M5 re-add choke_point_impact         -> 2 failed
M6 narrative exclusion returns True  -> 1 failed   (the positive control)
M7 choke points lose their rank      -> 1 failed
M8 choke_point_uids drops v1 read    -> 1 failed
```

M1 and M2 are why the guard **discovers** populations instead of reading
a list. The first draft named five fields by hand; re-adding a removed
field left the sweep green, because a re-added field was not in the list.
A guard that only sees what it was told about cannot catch the next
instance of the defect it was written for.

**Two exclusions are stated, not silent, and each has a test that it is
not a hole.** The full element population is excluded because two
*measures* over every element (`element_durations`, `blast_radius`) are
not two claims about which elements are interesting — that repetition is
real and it is [`UX-289`](UX-0289-one-element-table-many-presets.md)'s
subject. `findings[...]` is excluded because a finding restates the data
it was derived from and travels into a CI comment as a unit (`UX-75`).
M6 is the control on the second: making the exclusion universal reddens
`test_the_check_would_see_a_planted_duplicate`.

**A limitation of the committed fixture, recorded rather than hidden.**
The floor is two elements, because a one-element set matches any other
one-element set:

```text
v1 floor=1: 12 clashes      v1 floor=2: 2 clashes
v2 floor=1:  5 clashes      v2 floor=2: 0 clashes
```

All five survivors at floor 1 are coincidences of a fixture with one leaf
(`leaves_detail` against `cache.target_closure.targets`, unrelated fields
that both name `all.bst`). The cost is that the *leaves* duplication is
one element on this run and so below the floor; the 1,202-element run
sweeps it at 135, and `test_the_removed_fields_are_gone` names those
fields directly.

**Filed, not fixed here:** the exclusion for findings turned up the same
question one level down — a finding carries each of its numbers in up to
three carriers (`evidence`, `provenance.evidence[].value`, `copy_text`),
23 numbers across nine findings with 10 doubled and 20 tripled, each
carrier for a stated reason and no rule saying they must agree
([`UX-291`](UX-0291-a-finding-carries-its-numbers-three-times.md)).

Tests: 12 new (`tests/unit/test_no_two_fields_carry_the_same_elements.py`).
The `mixed_task_kinds` golden was regenerated deliberately; the diff is
the version stamp, the four removed fields, and `deferral_risk` on each
leaf, and nothing else. Full suite 3443 passed, 3 skipped (up from 3431),
`make lint` clean.
