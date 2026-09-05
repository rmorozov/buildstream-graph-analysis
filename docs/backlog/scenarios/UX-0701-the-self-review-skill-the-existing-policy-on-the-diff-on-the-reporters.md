# UX-701: the `self-review` skill — the existing policy on the diff, on the reporters' model

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-687 (the impact set that routes it), UX-663 (the run ledger) | **Serves:** the implementing session before it reports done, and R8 who then reads a finding list instead of a diff | **Topic:** docs

## Motivation

`REVIEW.md` has four passes, a finding shape, a nit cap and a "do not
report what the gate enforces" rule; the rules card has the rules.
Nothing runs them before a pull request opens, so the session's own
model reads its own diff, or nobody does. Two checklists would drift;
the skill must read the two that exist.

## Required Fix

`.claude/skills/self-review/SKILL.md`, run on the reporters' model
(`sonnet`, the round-90 advisory): input is `git diff <base>`, the
task file, `REVIEW.md` and `docs/contributing/rules.md`; output is
`REVIEW.md`'s finding shape, tagged by pass, Important/nit, at most
five nits; it does not report what `make lint`, the ledger or the
suite holds. **Routing**: the skill first runs `dev_impact.py` on the
diff — a set touching a contract, a spec Part, a hook or a skill is
sent to the `design-review` skill on the session's model as well; any
other diff stops at self-review and the gate. One row per run in the
run ledger; target under 40k tokens. `verify` calls it last.

## Out of Scope

- Approving — `REVIEW.md`'s threshold stands; a human approves through
  branch protection.
- A GitHub Action that runs the skill on every pull request — a second
  runner of the same policy; first measure what the local run costs
  and finds, then decide (`UX-663`'s ledger is the evidence).

## Acceptance Test

Run on the round-92 diff (`737bf4f8`): findings tagged by pass, none
about anything `make lint` reports, one ledger row under 40k; mutation:
a diff that touches `bga/schemas.py` — the report names the
design-review route; a diff touching only `docs/` — it does not.
