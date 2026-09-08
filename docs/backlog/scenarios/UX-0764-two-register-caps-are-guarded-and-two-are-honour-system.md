# UX-764: two Register caps are guarded and two are honour-system

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-497 (the Outcome cap), UX-749 (which broke one) | **Serves:** the reader who trusts a cap because the guard reported green | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md`'s Register states four caps. `rules.md` says it is "every
rule on a page, with its guard". Two of the four have no guard, and
`tests/unit/test_the_register_is_terse.py` reports green either way —
which is the `UX-573` shape, in the file that polices the shape.

| cap | enforcement |
|---|---|
| module docstring ≤ 25 lines | guarded, but only for `tools/dev_*.py` and `.claude/hooks/*.py` (`test_the_register_is_terse.py:39-40,52-82`) |
| Outcome ≤ 80 lines | guarded — **length only** (`TestOutcomes::test_a_budgeted_outcome_fits`) |
| commit body ≤ 8 lines | guarded, and CI-enforced (`ci.yml:642`) |
| **code comment: one line of why** | **unguarded** — nothing reads code comments |

It has already been broken with the guard green. `UX-0749`'s own
Outcome records it: the verifier found a new constant's comment
running **six lines** against the one-line cap; it was *"trimmed to
two"* — still over — and the file reports
`test_the_register_is_terse.py` green, because that guard never reads
that surface.

The Outcome cap has the matching hole on the other axis: its
*content* is unguarded. `CLAUDE.md` says an Outcome carries "the gap
measured, the close measured, the mutation table, the deviation", and
only the line count is checked. `docs/audits/round-94.md:20` measured
the consequence — **55 of 60** closed tasks carried a mutation table,
so five closed without one and nothing reddened.

## Required Fix

1. Decide the code-comment cap honestly: guard it, or state the rule
   as the convention it actually is. A cap that reports green while
   being broken is worse than a cap stated as guidance — this
   repository files rows about exactly that.
2. Guard the Outcome's **content**, not just its length: a closed row
   whose Outcome names no mutation table is the defect
   `round-94.md` counted.
3. `rules.md` claims to carry every rule with its guard. Where the
   guard is a convention, say so in the row rather than leaving the
   column to imply one exists.

## Out of Scope

- The caps' values. `UX-497` set the Outcome budget and `UX-652` the
  commit body; this row is about which are enforced, not how big.
- Widening the docstring guard beyond `tools/` and the hooks. Its
  narrowness is deliberate — "older ones only shrink".

## Acceptance Test

Every Register row states its enforcement truthfully, and a closed
Outcome with no mutation table reds. Mutation: strip the mutation
table from a round-104 Outcome and confirm the new clause names it,
where today the suite is green.

## Outcome

**The gap, measured.** `grep -rn "dev_commit_bodies" tests/unit/*.py
.github/workflows/ci.yml` finds the tool unit-tested
(`test_a_commit_body_is_eight_lines.py`) and CI-invoked (`ci.yml:642`),
guarded but only there: `make test` never calls it, which is how
round 106 shipped a ten-line body invisible in the diff and the
track's own report, caught only by a verifier running the tool by
hand. `grep -rln "code comment\|one line of why" tests/` finds one
hit, a docstring naming the phrase, not a guard - the code-comment cap
is the one actually unguarded. Outcome length is guarded
(`test_a_budgeted_outcome_fits`); content is not -
`docs/audits/round-94.md:20` measured 55 of 60 mutation tables, five
missing and green throughout.

**The close, measured** (this track's share: Outcome content and the
commit-body population; the code-comment cap and `rules.md`'s honesty
are a sibling track's row). Added `TestOutcomeContentIsGuarded` to
`test_the_register_is_terse.py`: every closed, budgeted (`UX-497`+)
Outcome must mention "mutation" or be named in `NO_GUARD_OUTCOMES`
(four pre-existing exemptions, checked real by their own clause). New
`test_the_commit_body_gate_runs_before_ci.py` runs
`dev_commit_bodies.over_cap(base="origin/main")` inside `make test`, so
a track's own suite now sees what round 106 needed a verifier's manual
run to catch. Where it does **not** run: `ci.yml:642`'s call lives in
the `agent-config` job, which fetches `origin main` first; the `test`
job checks out without that fetch, so this guard skips there and adds
no enforcement inside CI (`agent-config`'s own call still runs on every
push). It earns its place on a local `make test`, where the ref
resolves. A commit already folded into `origin/main` measures an empty
range - a pre-merge gate, not a retroactive audit.

**Mutation table.**

| mutation | result | count |
|---|---|---|
| strip the Mutation table from `UX-0761`'s closed Outcome | 🔴 names the file: "closed Outcome names no mutation table" | 1 failed, 1 passed |
| add a bogus `UX-9999` to `NO_GUARD_OUTCOMES` | 🔴 `test_every_exemption_is_a_real_closed_task` names it | 1 failed |
| a real 9-line-body commit on top of `origin/main` | 🔴 names the sha, subject and count (9) | 1 failed |
| restore from a scratchpad copy after each (never `git checkout --`) | 🟢 all clauses pass; `git diff` clean | tests green

**This track's share** (the code-comment cap and `rules.md`'s honesty).
`CLAUDE.md`'s Register table's code-comment row now reads "convention,
unguarded: a comment's length is not its register (`UX-764`)" instead
of stating a cap indistinguishable from the three guarded ones;
`rules.md`'s opening paragraph — the "every rule ... with its guard"
claim `test_the_card_stays_a_card` still holds at 80 lines — now names
that row as its one exception. New
`TestEveryRegisterRowNamesItsEnforcement` in
`test_the_register_is_terse.py` reads `CLAUDE.md`'s `## Register`
table and asserts every row names an existing `tests/unit/*.py` guard
or says "convention" - the fifth-row hole the Motivation named.
`make test-touching`: 48 file(s) selected (21 census + 27 naming the
change) · 1551 passed, 4 skipped in 207.00s. `make lint`: clean.

The verifier read `27404b0a` and found two holes: the `"convention" in
detail.lower()` check ran first and short-circuited on a bogus path
next to the word "unconventional"; a row naming a real but unrelated
file (`test_cache_logs.py`) passed as a proxy. Fixed: every named
`.py` path must exist unconditionally, "convention" now matches only
as a whole word (`\bconvention\b`), and each named file's own text
must carry `CLAUDE.md` or a `rules.md#` marker or it counts as a
proxy.

| mutation | result | count |
|---|---|---|
| add a fifth row naming no guard and no "convention" | 🔴 names the row: "no existing guard file and no 'convention'" | 1 failed |
| rename a real row's guard file to one that does not exist | 🔴 same clause names the row and the bogus path | 1 failed |
| a row with "unconventional" next to a bogus `.py` path | 🔴 `missing file(s)` names the bogus path | 1 failed |
| a row naming `test_cache_logs.py` (real, never reads the register) | 🔴 "never reads CLAUDE.md or a rules.md heading" | 1 failed |
| restore from a scratchpad copy after each (never `git checkout --`) | 🟢 `test_the_register_is_terse.py` 606 passed; `git diff` clean | tests green

**Deviation.** The judgement — the code-comment cap is a convention, said so in the table and in `rules.md` — was the session's; an `implementer` on `sonnet` did the rows and the guard, and its `verifier` found the guard's "convention" substring short-circuited a bogus path and that any existing file passed as a guard; fixed before the merge: paths checked unconditionally, `convention` a whole word, a named guard must read `CLAUDE.md` or a `rules.md` heading.
