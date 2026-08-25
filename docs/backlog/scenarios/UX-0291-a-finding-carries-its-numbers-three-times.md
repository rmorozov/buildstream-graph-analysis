# UX-291: a finding carries its numbers three times

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-288 | **Serves:** R5 and R7 — the payload consumers | **Topic:** contracts

## Motivation

Found by `UX-288`'s guard, which sweeps the payload for two fields
carrying one element set and had to be told that `findings[...]` is
derived narrative rather than a second publication. That exclusion is
right for the element sets. It also hid this, which is the same
question one level down.

Measured on the committed `macro_micro` run, `analyze/v2`:

```text
finding                    evidence  prov  both  in copy_text
cache-hit-ratio                   4     4     4             4
confidence                        3     3     1             3
wait-category                     4     2     0             4
time-concentration                4     3     0             3
mesh-graph                        1     1     1             1
joint-saving                      3     4     3             3
optimization-horizon              1     3     0             0
latent-heavies                    1     1     0             0
efficiency-score                  2     2     1             2
TOTAL                            23          10            20
```

Twenty-three numbers across nine findings. Ten of them are carried a
second time in `provenance.evidence[].value`, and twenty appear a third
time inside `copy_text`.

**Each carrier has a stated reason**, which is why this is a question
and not a bug:

- `evidence` is the machine field a consumer reads.
- `provenance.evidence[].value` is `UX-229`'s "what we read, at the path
  we read it from" — the value is *how* the claim shows its work, so
  citing the path without the value would weaken it.
- `copy_text` is `UX-224`'s paste-into-a-ticket rendering, which has to
  be self-contained by definition.

And one finding restates a whole signal:

```text
signals.joint_saving  {elements, joint_saving_us, sum_of_individual_us, savings_add}
finding joint-saving  elements + evidence{joint_saving_us, sum_of_individual_us, savings_add}
values identical: True   elements identical: True
```

`findings.py` derives the finding *from* `signals.joint_saving`, so the
direction is right and the signal is the source. The question is whether
the derived copy should carry the numbers or cite them.

Nothing is currently wrong: all three carriers agree, because all three
are written from the same values in one pass. The cost is that a
consumer meeting `evidence.joint_saving_us` and
`provenance.evidence[0].value` has no rule saying they must agree, which
is exactly the gap `UX-288` closed for element sets.

## Required Fix

Decide, and write the decision down where a reader of the contract meets
it:

1. Either `evidence` becomes a projection over `provenance.evidence` —
   one carrier, the other derived at read time, the shape `UX-288` used
   for `critical_path_uids` — or the contract states that the two are
   independent by design and says which one wins if they disagree.
2. `copy_text` stays as it is either way: it is a rendering for a human
   in a ticket and self-containment is its job (`UX-224`).
3. A guard that the carriers agree, whichever answer 1 gets. That guard
   is cheap and is the one nothing currently makes.

## Out of Scope

- `signals.joint_saving` itself. It is the source the finding is derived
  from; removing it would make the narrative the only place a number
  lives, which is the opposite of what `UX-288` was for.
- The element sets. `UX-288`'s guard excludes `findings[...]`
  deliberately and with the reason; findings travel into a CI comment as
  a unit (`UX-75`) and a finding that named no elements would be the
  regression.

## Acceptance Test

For every finding on a real run, each number appears in one carrier or
in carriers a guard proves agree, and the contract document names which
one a consumer should believe.
