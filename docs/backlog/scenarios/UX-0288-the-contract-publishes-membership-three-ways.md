# UX-288: the contract publishes membership three ways

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-268 | **Serves:** R5 and R7 — the payload consumers — and every reader of the page | **Topic:** contracts

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
