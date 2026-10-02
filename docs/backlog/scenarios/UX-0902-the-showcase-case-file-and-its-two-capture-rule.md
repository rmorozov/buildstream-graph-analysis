# UX-902: a showcase case is two captures, and there is nowhere to put one

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-891 (the CPU floor, which the first case reads), UX-172 (blast) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 7) — adoption needs stories that can be shown, and the owner named the first two | **Serves:** R1 and R2 (the developers being asked to adopt it), R8 (the manager being asked to fund the time) | **Topic:** docs | **Area:** unassigned | **Shape:** mechanical

**Guard:** test_a_case_carries_both_captures.py

## Motivation

The repository documents what the tool *can* answer in fifteen guides
and ninety audit rounds, and holds no document of the form *a real
build was slow, bga said this, we changed that, and here is the
re-measured result*. That is the document adoption runs on, and its
absence is why the tool is currently sold by reading its own manual.

Two cases are in hand and neither is hypothetical:

- **The lone element capped at the default jobs.** An LLVM element
  builds alone for about forty minutes on an agent with far more cores
  than BuildStream's default `max-jobs` gives it. This is the axis
  argued in [`in-step-parallelism.md`](../../design/in-step-parallelism.md),
  whose first increment is `UX-891`, with the jobserver as the
  intervention half — the strongest before/after the tool can currently
  show.
- **Redundant rebuilds.** `bga blast` answers what a change to a
  repository, a path or an element rebuilds; the usual cause is source
  keying (a `git` source keys on its ref, a `local` source on content).
  A developer-scenario case that needs no new code.

## Required Fix

A case-file shape, and the first case written in it. The shape is the
rule this row exists to hold:

> A showcase case carries **both captures** — the before, the change,
> and the after, each with the command that produced it and the run it
> came from. A case that names a saving without the second capture is a
> projection, and `whatif` is where projections live.

Each case: the symptom as the owner saw it, the command, the finding
verbatim, the change made, the re-capture, and the delta with its noise
band (`UX-899`'s band where a band exists). Where a case is projected
rather than re-measured, it says so in its own first line.

## Out of Scope

Marketing copy, benchmarks against other tools, and any case whose
second capture does not exist yet — those wait rather than shipping as
projections dressed as results.

## Acceptance Test

`docs/audits/` or a new `docs/cases/` holds at least one case in the
shape above, and a guard reads every case file for two capture
references and a delta, reddening on a case that has only one. The
README's case link resolves. Mutation: remove the after-capture
reference from a case (the guard names that file).

## Decision

```text
Route:     a new tree, docs/cases/, one file per case. Its first case is docs/cases/serial-giant-jobserver.md, built from examples/11-serial-giant on CodSpeed Graviton (16 Cortex-A72, 31 GB, bst 2.8.1), runs from bga-bench.
  Headline leg (cap3, max-jobs 3, the 8-of-40 server shape): off 261.4 s (263.10/260.75/260.34) to auto 112.3 s (112.85/111.90/112.13), -57.0 %, run 36095261434. Reproduced at -57.0 % in run 36103304381.
  Second leg (pairs, bst's own default max-jobs 8): off 139.27 s (spread 0.9 %) to auto 112.56 s (spread 1.0 %), -19.2 %, run 36086044196. Reproduced at -19.5 % in run 36103304381.
  Its first line says it is a stand-in: the owner's LLVM element is the symptom, and the build actually measured is the example.
  Case-file shape, in order: Symptom · Command · Finding (verbatim) · Change · **Before:** · **After:** · **Delta:**.
  Capture reference: one **Before:** line and one **After:** line. Each holds `run <id>` (5+ digits, a bga-bench Actions run), the arm in backticks (`off` | `auto`), the leg, and the in-tree reproducer paths (examples/11-serial-giant/graviton_arms.sh, .github/workflows/codspeed-probe.yml). Each path must exist.
  **Delta:** a signed % with its band: the 3-repeat spread, or UX-899's band where one exists. Projected cases are not allowed in docs/cases/.
Rejected:  docs/audits/ (that tree is "what was found, and when"; every named doc there needs a README audits row and a filename regex would be needed to tell cases from rounds); a projected-case header line (Out of Scope: projections wait, `whatif` holds them); blast radius as the first case (no real second capture yet, its own row); 15-wide-chain in the same file (a different story, a later case); a committed capture as the reference (the Graviton runs are not fixtures, as UX-905's guard reasons).
Files:     docs/cases/serial-giant-jobserver.md (new); docs/README.md ("### Case studies" table, one row); README.md ("## Documentation", one link line); tests/unit/test_a_case_carries_both_captures.py (new)
Guard:     tests/unit/test_a_case_carries_both_captures.py lists case files with `git ls-files docs/cases/*.md`, never a glob (UX-583). Every file has >= 1 case with **Before:** and **After:** (each with `run \d{5,}`, an arm, and reproducer paths that exist) and **Delta:** (a signed % and a band). A failure names the file.
Mutation:  M1 delete the **After:** line -> red naming the file; M2 strip the run id from **Before:** -> red; M3 rename a cited reproducer path -> red; M4 remove the case file -> red (population empty)
Reading:   no new registry: PyMarkdown's "docs/*.md" pathspec covers docs/cases/; the link check resolves both README links; the docs lane finds the guard from "docs/cases"; docs/cases/ is outside the parse sweeps.
```

## Outcome

### The gap, measured

```text
$ git ls-tree origin/main docs/cases          # 42a1badf
(empty)
$ git grep -lE '^\*\*(Before|After):\*\*' origin/main -- docs | wc -l
0
```

No tracked document carried a before capture and an after capture
together; UX-905's Graviton numbers lived only in a direction status
block and the jobserver guide's table.

### The close, measured

`docs/cases/serial-giant-jobserver.md` holds two cases (`cap3`, `pairs`).
Every number was checked against UX-905's Outcome and against the
bga-bench annotations, read with `gh run view <id> --repo
bst-perf-tools/bga-bench`:

```text
36095261434 cap3 off  wall 263.10s cpu 736s; 260.75s 728s; 260.34s 724s  -> 261.4 s
36095261434 cap3 auto wall 112.85s cpu 845s; 111.90s 838s; 112.13s 841s  -> 112.3 s, -57.0 %
36103304381 cap3      off 261.95/260.49/260.77  auto 112.59/112.09/112.52 -> -57.0 %
36103304381 pairs     off 139.72/139.22/139.08  auto 112.49/111.86/112.11 -> -19.5 %
```

`pairs` in run 36086044196 (139.27 s to 112.56 s, -19.2 %) comes from
UX-905's pasted rows. Band: the 3-repeat spread, (max - min) / mean:
cap3 1.1 % / 0.8 %, pairs 0.9 % / 1.0 %.

```text
$ PYTHONPATH=. python3 -m pytest -q -n 0 tests/unit/test_a_case_carries_both_captures.py
2 passed in 0.21s
```

**Deviation, the Finding.** It is not a line from the Graviton capture.
`graviton_arms.sh` never runs `bga analyze`, `gh run view --log` was
refused (403 from the results receiver), and this container has no
BuildStream. So the case quotes the output of
`_builder_pool_text_lines(compute_builder_pool_recommendation(3, 16, MJ))`
for MJ 3 and 8, prints that command, and gives its inputs. The
ready-set width of 3 came from a hand-built replay that leaves out
`switch-4-4`/`switch-4-2`. The case marks the CLI's hard-coded
`13-mixed-graph` parenthesis as belonging to another example. No UX-899
band exists, because there is no baseline store of Graviton runs; the
case says that too.

Verifier pass (second commit): the guard now also requires `off` on
**Before:**, `auto` on **After:**, the same leg on both, and a Delta
within 0.1 pp of the two means. The idle-core symptoms are marked as
inferred from the giant's peak.

### Mutations

Run from a scratch copy of the case file, then restored with `cp`.
After the restore, `cmp` was clean and the test passed 2 of 2.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | delete Case 1's **After:** paragraph | `...: Case 1: ...: no **After:** line` | 1 failed |
| M2 | strip `run 36095261434` from Case 1's **Before:** | `**Before:** names no \`run <id>\`` | 1 failed |
| M3 | `graviton_arms.sh` cited as `graviton_arm.sh` | `cites examples/11-serial-giant/graviton_arm.sh, which does not exist` | 1 failed |
| M4 | `git rm --cached` + move the case file | `docs/cases/ tracks no case file` | 1 failed, 1 skipped |
| M5 | Case 1's **After:** names arm `off` | `**After:** names no arm \`auto\`` | 1 failed |
| M6 | `leg \`cap3\`` removed from Case 1's **Before:** | `**Before:** names no leg` | 1 failed |
| M7 | Case 1's Delta `-57.0 %` changed to `-50.0 %` | `**Delta:** -50.0 % but the means give -57.04 %` | 1 failed |
