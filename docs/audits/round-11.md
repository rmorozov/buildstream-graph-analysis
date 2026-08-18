# Audit round 11: re-verifying a round someone else fixed

Run on 2026-08-18, same 4-core / 16 GB environment as round 10 (venv,
BuildStream 2.7.0, staged gcc 13 toolchain, all round-10 captures
retained and reused). Round 10 filed `UX-77`..`UX-92`; another session
implemented all sixteen in twenty commits, plus a docs reorganization.
This round's job is the discipline the backlog's own header demands:
*don't trust a claim of "done" without independently re-verifying it* —
every acceptance test re-run for real, against the round-10 captures
where they exist and against fresh builds where they don't.

## The scoreboard

Re-verified hands-on, each against its filed acceptance test:

| item | verdict | the evidence |
|---|---|---|
| UX-77 front door | **works** | wheel → clean venv → empty cwd: `bga extract/capture --help` exit 0 (was a raw traceback) — but see UX-94 below for what the fix cost |
| UX-78 refusal | **works** | golden-vs-real: exit **6**, names `shared_elements`; `--allow-mismatch` restores the old warn-and-compare; cold-vs-incremental refuses on both checks |
| UX-79 marginal gate | **works** | on the retained grow captures: good add stretch 0.00 → passes; bad add stretch 1.00 → *"Marginal efficiency gate FAILED … unlike the whole-build efficiency gate it does not weaken as the project grows"*; the dilution claim is now a pinned two-scale test (−14.6pp at 11 elements vs **−0.5pp at 1201** for the same crime) |
| UX-80 capture default | **mechanism verified, claim not — reopened 🟡** | `--wrapped-log` implies the record (re-verified live); but the filed acceptance was never run: no `build-root`-overriding fixture exists, and the four new tests exercise flag resolution only — none can fail if the join itself breaks. The Verification Log says the plumbing was "read from" the source — the exact insufficient form the fixing guide names |
| UX-81 history | **works** | 6 capture refs (was 1): 3 same-config incrementals + 1 cold, per-run refs never force-pushed, mode+config in the ref name, weekly schedule configured; `bga analyze <checkout>/run` works untarred on the two newest refs; the live 3-run **band compare** replaced the 1% rule with a scaled-MAD band and absorbed a −0.8% delta as noise |
| UX-82 synthesis | **works — filed acceptance run by this round** | shipped verified only against a hand-built fixture (28.0s → 12.0s); round 11 ran the filed command on the named round-10 capture: *"Restructuring opportunity: 18 declared build edge(s) … finishes in 11.1s against 24.9s"*. The filed 25.05s expectation was wrong, and the measurement corrects it: the finding removes the never-read `core→lib` edges the example's `optimized/` retains, so the right expectation is `core.bst` alone — **11.05s measured, 11.1s projected**. The tool out-reasons its own gold standard |
| UX-83 arbitration | **works — filed acceptance run by this round** | shipped verified against fdsdk (`gperf.bst`, knee 2), not the capture the task named; round 11 ran the filed test on the macro-fixed capture: the hint names `core.bst`'s `-j1` pinning, the knee-5 sweep line carries "2.17 of 4 cores busy" + the pinning note, and without `--plane2` the old text is unchanged |
| UX-84 bst tier | **works** | `make test` with live bst 2.7: **1237 passed, 0 failed** (was 4 failed / 1122) |
| UX-85 shadows | **code works, record didn't exist** | only import aliases remain; guards re-pointed; the AST guard even caught a fifth shadow the task never named — but the commit never touched the task file, which still read 🔴 with no Verification Log while the status table said 🟢, the exact combination the fixing guide forbids. Round 11 wrote the missing record from its own re-verification |
| UX-86 cold capture | **works** | a real caches-off capture exists: `gcc-stage1.bst`, 18 elements, 0 cached, 34.2 min, confidence 1.00 — and its first analysis *falsified a UX-92 finding* (0% hit ratio reported as suspicious on a build told not to use caches), which was fixed with regression tests |
| UX-87 gate no-op | **works** | warning + `efficiency_gate_evaluated: false` + opt-in `--require-efficiency-signal`, with dedicated tests |
| UX-88 docs sweep | **works** | spot-checked: README quick start now shows the real three-element output; each fixed claim's verification was re-run |
| UX-89 grouping | **works** | the seven interchangeable rows are one block (`app.bst, lib-a.bst..lib-f.bst (7 elements …)`); the 0.1s `ranlib` noise is gone |
| UX-90 triggers | **works** | push trigger deleted with the 17-of-24 ledger in the comment; zero push runs since |
| UX-91 Plane 3 | **works** | `bga cache-logs` on this machine's real log tree: per-element phase splits, repeated-operations pointer with an honest "no per-command timing" hedge, floors explicitly out of reach; fdsdk log publication wired for the next capture |
| UX-92 cache report | **works, with one blind spot** | fdsdk: *"Cache hit ratio: 72% … the cache did most of the work"*; live invalidation-root test (below) exact — the blind spot is `UX-93` |

The one acceptance test that could not run yet: UX-91's fdsdk half
(element logs publish from the *next* capture on) and UX-96's
scheduled-run evidence (first firing due 2026-08-23).

## The one defect that survived contact: churn without cache continuity

UX-92's invalidation-root detection was tested here in its true-positive
direction for the first time, on real incremental builds: cold build A;
tweak `codegen`'s source → build B (4 tasks); tweak `core`'s source →
build C (12 tasks); compare B→C:

```
Invalidated at core.bst: its cache key changed (e50dfdfd -> dd012bbd)
and invalidated 10 element(s) below it, 65.9s of rebuilding in total.
Nothing it depends on changed, so the change starts here
```

Exactly right, zero false churn. (En route, a lesson worth keeping:
adding an *unreferenced* variable to an element does not change its
cache key — BuildStream hashes what reaches commands, not raw YAML —
so the first attempt at this experiment was a silent full cache hit.)

But the *churn* half indicts any rebuild whose key didn't change,
without asking whether the artifact was there to reuse: a cold pair
reads as "36.5s bought nothing", and the tool's own warm/cut fdsdk
captures read as **"4604.2s bought nothing" in every band comparison
the new weekly schedule will ever produce** — the deliberate cut
reported as waste. The same run-mode blindness was already found and
fixed once this round, in `analyze`'s hit-ratio finding; `compare`'s
churn needs the identical treatment plus one distinction the data
supports (rebuilt-in-both-runs ⇒ a cache *retention* question, not a
project one). Filed as `UX-93`, the round's one High.

## The smaller findings

- **`UX-94`** — UX-77 was fixed by shipping a top-level `tools` package
  in the wheel: the generic name is now squatted in every consumer's
  site-packages, and pip will silently interleave files with any other
  distribution shipping `tools/`. The task file's own preferred fix
  (move under `bga.`) was the right one.
- **`UX-95`** — the reports' `Run:` header prints the (deliberately
  stable) identity hash as the only identifier, so two different fdsdk
  captures 100 minutes apart display the same digest. History (UX-81)
  makes same-config runs the common case; the instance facts exist in
  `run-context` and are simply not printed.
- **`UX-96`** — assembling the band compare that UX-81 makes possible
  took a `ls-remote`, three extractions, two untars and a five-path
  command; nothing checks the baseline set's homogeneity (the three
  captures span three `bga` revisions, recorded and consulted by
  nothing); and cold captures accumulate only by manual dispatch.

## The fix round's own drift, batched as UX-97

A commit-by-commit review found five places where a *later commit in
the same range* falsified an earlier commit's shipped claim: the
findings-id table UX-88 published went stale when UX-92 added two ids
(15 documented, 17 declared); UX-86's capture-mode ref rename broke the
discovery glob UX-81 advertises (it now matches nothing, while the
correct listing is pasted as evidence in the same file); the bst tier
count reads 14 in four documents and 15 in the CI gate; that CI gate
runs pytest through `tee` without `pipefail`, so `15 passed, 1 error`
would go green; and four bare paths survived the reorg, including the
link-rule test's own assertion message pointing at a file that no
longer exists. All five are `UX-97`, with the two recurrence-prone ones
(the id list, the tier count) to become test-enforced rather than
re-edited.

The docs reorganization itself held up under independent re-checking:
zero dangling markdown links across every tracked file, including the
two example READMEs its own test does not walk, and its two enforced
rules are real tests with sensible scopes — with two soft spots worth
naming: the `python3 -m tools` escape-hatch marker is already used 8
times against a commit message claiming one, and `docs/design/` is
silently outside the rule's scope.

## What this round says about the process

Sixteen filings, sixteen implementations; fourteen hold, and the
failures cluster in verification discipline, not code. The pattern is
precise: every item whose filed acceptance was *actually run* survived
this audit untouched, and every item that substituted a fixture for
the named capture (UX-82, UX-83), read the source instead of running
the test (UX-80), or skipped the record entirely (UX-85) is where the
round's findings live. Meanwhile the best moments were falsifications:
the fixer's cold capture caught UX-92's hit-ratio finding before this
audit could, UX-84's real-bst tier caught a genuine Plane 2 anchoring
bug, and UX-92's own first implementation was caught deriving churn
from a critical-path fallback. The one *code* defect that survived
(UX-93) was in the newest capability, in exactly the configuration its
fixtures didn't model — cache discontinuity, the most common state a
CI cache is in. A capability that judges *why a build did work* needs
fixtures for every reason a build can do work.

The forward-looking half of this round — what the tool should learn to
see next, argued from data already in hand — is
[`design/directions.md`](../design/directions.md) Direction 3.
