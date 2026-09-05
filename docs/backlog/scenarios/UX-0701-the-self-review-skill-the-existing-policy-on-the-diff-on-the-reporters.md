# UX-701: the `self-review` skill — the existing policy on the diff, on the reporters' model

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-687 (the impact set that routes it), UX-663 (the run ledger) | **Serves:** the implementing session before it reports done, and R8 who then reads a finding list instead of a diff | **Topic:** docs | **Area:** tools | **Shape:** judgement

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

## Outcome

🟢 Done. `.claude/skills/self-review/SKILL.md` is the **procedure**;
the policy stays in `REVIEW.md` and `rules.md`, and the skill carries
no second copy of either. `verify` §6 calls it last.

### The routing rule is run, not remembered

`dev_impact.route()` (`UX-687`'s tool) decides, so a guard can mutate
it:

```console
$ echo bga/schemas.py | python3 tools/dev_impact.py - --route
design-review  (a contract)
$ echo docs/guides/cli.md | python3 tools/dev_impact.py - --route
self-review
```

Four surfaces send a diff on — a contract, the spec, a hook, a skill —
each one whose reader is somebody other than the diff's author.

### The acceptance run

**The sha in the Acceptance Test is not an object in this repository.**

```console
$ git cat-file -t 737bf4f8
fatal: Not a valid object name 737bf4f8
$ git log --oneline --all | grep -i "round 92"
523dd7d Design round 92: …  (UX-685..UX-692)
```

`UX-626`'s shape exactly: an id written from memory rather than
resolved. Run on `523dd7d` instead.

It routes to **`self-review`** — fourteen files, all `docs/` plus one
test — which is the *docs-only* half of the row's own mutation,
observed rather than constructed.

One finding survives the passes:

> **nit · Evidence** — `test_every_direction_names_its_reader.py:229`
> asserts `numbered == set(range(1, 19))`, a count the document owns.
> `git log -G "set\(range\(1, [0-9]+\)\)"` names **four** commits:
> `UX-581` wrote it, and rounds 91, 92 and 93 each bumped it. It reads
> `range(1, 20)` today. Contiguity against `max(numbered)` would hold
> the same property without a literal a round must remember.

Nothing reported that `make lint`, `check-clean`, the baseline or the
suite already holds — the eight filings and `round-92.md` are prose
those gates cover.

### Mutations

| mutation | guard |
|---|---|
| the contract surface dropped (the row's own) | contract → design-review |
| every diff routes to design-review | docs-only stops at self-review |
| spec, hook and skill surfaces dropped | every named surface routes |
| the skill restates `REVIEW.md`'s nit cap | it carries no second copy |
| the skill stops naming `sonnet` | the reporters' model |
| the wrong-layer rule dropped | do not report what the gate holds |

### Deviation

Three, all recorded rather than worked around. The Acceptance Test's
sha does not resolve, so `523dd7d` stands in. The 40k-token target is
written into the skill but **not measured**: this run was the
session's own, not a `sonnet` subagent, so there is no ledger row to
compare and `UX-663`'s ledger gets its first real row when a track
next calls the skill. And the skill's first draft restated the nit
cap — the defect the guard now holds was mine, caught by writing the
guard before believing the file.
