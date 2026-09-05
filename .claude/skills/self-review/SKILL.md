---
name: self-review
description: Review your own diff against the policy this repository already has, before the pull request opens - four passes, the finding shape, the nit cap, and the routing decision about whether a design reader is needed too. Use after the last commit of a task and before reporting done; `verify` calls it last.
---

# self-review

The policy is **not here**. It is in
[`REVIEW.md`](../../../REVIEW.md) — four passes, what *Important*
means, the nit cap, and what not to report — and in
[`docs/contributing/rules.md`](../../../docs/contributing/rules.md).
Two copies of a checklist is how the copies disagree (`UX-240`), and
round 96 spent four rows on exactly that. So this skill is the
*procedure*: what to read, where to send it, what to write down.

Run on **`sonnet`** — the reporters' model (`UX-663`). The session's
own model reading its own diff is the thing this replaces.

## 1. Route, before reading anything

```bash
git diff --name-only <base> | python3 tools/dev_impact.py - --route
```

`design-review` means the diff reaches a surface whose reader is not
its author — a contract, the spec, a hook, a skill — and that diff
goes to the `design-review` skill **on the session's model** as well
as here. `self-review` means it stops at this skill and the gate.
The rule is `dev_impact.route()`, so it is run and not remembered.

## 2. Read exactly four things

| | |
|---|---|
| `git diff <base>` | what changed |
| the task file | Required Fix, Out of Scope, Acceptance Test |
| `REVIEW.md` | the four passes, the shape, the cap, the exclusions |
| `docs/contributing/rules.md` | the rules, each with its guard |

The impact set from step 1 without `--route` names the contracts,
guides and guards the diff reaches; read those rows, not the files.

## 3. Report in `REVIEW.md`'s shape

Tag every finding with its pass. **Important** or **nit**, and the
nit cap, by `REVIEW.md`'s own numbers — this file does not carry a
second copy of them to drift against.

Do not report what the gate already holds. `make lint`,
`make check-clean`, `dev_baseline.py --check` and the suite each fail
on their own; a finding about one of them is a finding about the
wrong layer, and it costs a reader's attention twice.

The compliance pass is the one a self-review is best placed to make
and worst placed to want: *does this diff do what the task asked, and
stay inside Out of Scope*. A diff that solved a better problem than
the one filed is still a finding.

## 4. Write the row

One row in [`docs/audits/agent-runs.md`](../../../docs/audits/agent-runs.md),
like any other agent run. Target **under 40k tokens**; a run that
needs more is a diff that wanted decomposing.
