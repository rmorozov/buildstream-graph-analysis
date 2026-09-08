# UX-765: two process cross-references point at numbers that are not there

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-238 (the tiers), UX-584 (the remeasurement) | **Serves:** the session that follows a cross-reference and finds the other number | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

Two small instances of the shape `UX-750` fixed for figures, here in
the process documents.

**The tier timings disagree.** The same three targets carry different
measurements in two places, with no statement that one supersedes the
other:

```text
Makefile:30-32           small 18.2s   medium 184.0s   large 159.0s
fixing-guide.md:91-98    small 20.8s   medium 173s     large 126s
```

Up to 35% apart on `large`. The guide frames its own readings as *"the
machine's number and not the tier's"* (`:96`), which is honest but
does not reconcile them — a reader comparing the two sees two answers
and no rule for which to cite.

**A skill cites a line that does not carry what it claims.**
`.claude/skills/design-review/SKILL.md:20` says *"The orchestrator
passes the model choice on the launch (see `CLAUDE.md`'s agents
line)"*. `CLAUDE.md:30` pins `researcher` and `verifier` to `sonnet`
and names no model for `design-review` or `walk`. The reference points
at information the target does not contain, so the choice is inferred.

## Required Fix

1. Reconcile the tier figures: one owner, the other deferring, in
   `UX-756`'s pattern — or date both in `UX-511`'s, since both are
   machine-dependent readings rather than claims.
2. Either state the model for `design-review` and `walk` on
   `CLAUDE.md`'s agents line, or correct the skill to stop citing it.

## Out of Scope

- Re-measuring the tiers. Both readings are recorded with their
  provenance; this row is about which one a reader should cite, not
  about their values.
- The tier floors themselves (`tests/tiers.py`).

## Acceptance Test

A reader following either cross-reference arrives at the number it
promises. Mutation: change the owning figure and confirm the deferring
site carries no stale copy to contradict it.

## Outcome

**The gap, measured.**

```console
$ git show e8f3d58:Makefile | sed -n '30,32p'
#   small   160 files    18.2s   pure Python over in-memory fixtures
#   medium   53 files   184.0s   spawns a process or a node harness
#   large     7 files   159.0s   scale fixtures, real process trees
$ git show e8f3d58:docs/contributing/fixing-guide.md | sed -n '95,97p'
   skipped) at 1-minute load **0.13**; medium read 2m53s at load
   **1.05** and large 2m06s at load **6.02**, ...
$ git show e8f3d58:.claude/skills/design-review/SKILL.md | sed -n '19,20p'
scratchpad. The orchestrator passes the model choice on the launch
(see `CLAUDE.md`'s agents line).
$ git show e8f3d58:CLAUDE.md | sed -n '30p'
`researcher` and `verifier` read on `sonnet`; ...
```

Confirmed: `CLAUDE.md:30` names no model for `design-review`/`walk`.

```console
$ awk -F'|' 'NR>15{print $3","$4}' docs/audits/agent-runs.md | sort -u
 agent , model
 general-purpose , main
 implementer , sonnet
 researcher , main
 researcher , sonnet
 verifier , sonnet
```

`docs/audits/agent-runs.md`'s model column has no row naming
`design-review` or `walk` at all — nothing to advise from.

**The close, measured.** Both readings kept and dated rather than one
picked as owner (`UX-511`'s pattern): `fixing-guide.md`'s §3 paragraph
now names `Makefile:30-32` as `UX-238`'s 2026-08-23 reading and says
to cite its own, newer one. Neither figure claims currency past its
own date, so a future re-measurement of either does not make the
other's *text* false — only stale, which the dates already disclose.
The skill was corrected rather than the card: `CLAUDE.md`'s agents
line states no model for `design-review`/`walk` because none is
measured (`UX-666`'s ledger has no row for either), and inventing one
would be a claim with no pasted measurement behind it (`CLAUDE.md`
Conventions). `design-review/SKILL.md:17-20` now says that directly
and points to the ledger's model column instead of a line that never
answered.

**Caught by review, corrected.** Dating both readings kept the textual
device `UX-511` uses without its mechanism — `UX-511`'s own Required
Fix says "a guard reads it" and shipped one. `Makefile:30-32`'s three
numbers are static text, not a live measurement, so a guard can hold
`fixing-guide.md`'s transcription of them to the source with no tier
re-run: `TestTheGuideQuotesTheMakefilesReading` in
`test_the_process_documents_derive_their_figures.py` parses both and
asserts equality — not that the two dated *measurements* agree (they
don't, by 35%, and shouldn't have to), but that the guide's quoted
copy of `UX-238`'s reading has not drifted from what `Makefile` still
says.

**Mutation** (falsify skill; `/tmp` copy, reverted):

| mutation | guard | result |
|---|---|---|
| guide's quoted `large 159.0s` → `126.0s` | `TestTheGuideQuotesTheMakefilesReading::test_the_transcription_matches_the_source` | 1 passed → 1 failed (`Makefile:30-32 now says {'large': '159.0'}`) → reverted, 1 passed |

The skill's dead pointer (`design-review/SKILL.md`) still has no
guard — nothing reads a skill's prose citation — and none is proposed:
`CLAUDE.md`'s agents line staying silent on an unmeasured model is a
judgement call, not a derivable figure.
