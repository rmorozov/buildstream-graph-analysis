# Audit round 16: the tool meets a big project

Run on 2026-08-20, same retained environment as rounds 10-15. Inputs:
the sibling's landings for round 15 (UX-147, UX-149..UX-154 in three
commits, plus their own field-driven `UX-155` — the TMPDIR advice from
UX-147's first version was followed by the real user and killed
`buildbox-casd`, so bga's scratch now lives in `.bga/tmp`), and the
user's new situation: the tool **works** on their real project after
those fixes, and the project is big enough that one capture is a
multi-hour session. The round verified the landings, then pointed the
polish lens at exactly that session: what does bga do well and badly
when a capture takes hours, holds thousands of elements, and
sometimes does not finish?

## Round 15's landings, verified

All landed items hold; the review (over `dcdd402..a659725`, with live
runs) and this round's spot checks agree. The notable verdicts:

- **UX-147** 🟢 — shebang materialized as `sys.executable`, self-probe
  before the build with the ENOENT/EACCES distinction, environ guard
  through a real shim process, three-way zero-invocation summary
  verified live in both readings (9-tasks/9-lines and warm-cache 0/0).
  The stale-casd detection was **deferred with a recorded deviation** —
  that gap graduated to `UX-161`.
- **UX-149** 🟢 with caveats — `doctor --capture` runs the real chain
  end to end in ~8s (verified live: probe → 1 sandboxed task → shim
  reached once → records classified), cleans up after itself. Caveats:
  its FAIL branches have no tests (the acceptance's three live failure
  reproductions were never run), and the probe's isolated `HOME`
  means it *cannot* see a stale casd — both carried into
  `UX-161`/`UX-162`.
- **UX-150** 🟢 — the wheel job is real: fresh venv, project copied
  outside the checkout, foreign cwd, `unset PYTHONPATH`, snapshot with
  diagnostics asserted. README leads with the deployed install.
- **UX-151** 🟢 — the split verified live on the exact field shape
  (`--json-status-fd 12` before the command splits correctly; the
  overlay family consumes three), unknown flags recorded and
  summarized, fingerprint as record line 1, excluded from the count.
  One new defect found beside it: `buildbox_run_path` resolves via
  `shutil.which` and is **null on every standard install** (bst
  vendors the binary off-PATH) — `UX-162` item 1.
- **UX-152** 🟢 — `detach_signal` consults `is_group_stop_signal`
  first, the degrade branch routes through it, the decision-table
  seam is tested and `spine.c` compiles clean. The log's claim that
  the state-`T` probe "cannot be written as specified" over-reaches:
  the orphaned-group reasoning is right for the shape tried, but a
  probe with a non-orphaned survivor group is constructible —
  `UX-162` item 6 keeps the record honest.
- **UX-153** 🟢 — one `element_path()`, doctor imports it, no
  hardcoded `elements/` survives in either file, the workflow runs
  doctor against freedesktop-sdk, `check_compiler` probes
  `-shared`/`-static` from stdin. But the same principle has a deeper
  unclosed half: discovery *within* the element path is non-recursive
  — promoted to this round's `UX-160` rather than a caveat, because
  its cost lands on the user tonight.
- **UX-154** 🟢 — re-ran the toll sweep independently: every surviving
  `toll` is a comment, docstring or published JSON key; the AST guard
  is correctly scoped; `real-project.md` teaches `bga baseline` with
  a guard asserting presence *and* order.
- **UX-155** 🟢 — scratch in `.bga/tmp` with the fallback message,
  `normalize_tmpdir()` fixing `os.environ` itself (the two-casd
  measurement in the log is the round's best diagnosis), doctor's two
  new checks, five falsifying mutations. The `.bga`-under-the-project
  trade-off (bst has no ignore mechanism; a root-spanning `local`
  source would stage live scratch into cache keys) is real but
  undocumented — `UX-162` item 7.
- **UX-148** stayed 🔴 by design; the review confirmed nothing
  half-landed.
- **d86e755** (the three CI fixes) — principled: a seam split with no
  weakened assertion, a test re-pointed at the condition it names, and
  a genuinely better `check_bst` that says "activate" when a sibling
  bst sits beside `sys.executable`.

Fast suites: 191 passed across the five capture/doctor/spine/scratch/
granularity modules; docs enforcement 17/17; `make lint-docs` clean.

## The round's own experiments: a capture that does not finish

The user's next session is hours long. Everything below was run live
on a copy of `examples/06` outside the repo.

**A failed build verdicts as an improvement.** Sabotage one element,
snapshot: the build fails (exit 255, honest), the extraction records
`build_outcome: {failed_elements: ['lib-d.bst']}` — and the terminal
ends with

```text
Verdict: IMPROVED  (total duration -26.35s, -65.6%, 40.15s -> 13.80s)
```

because four elements never built. Nothing consults the failure the
run-context wrote: not the verdict, not the analysis banner. The
failed run then silently became `@prev`, so the *next* healthy
snapshot compared against wreckage (baseline confidence 0.57, no
explanation). A user returning to a scrolled terminal reads verdicts,
not exit codes. Filed as **UX-156**: the verdict leads with NOT
COMPARABLE (the UX-78 refusal grammar, exit 6 under gates), and
auto-compare skips failed baselines out loud.

**Ctrl-C destroys the trace bga already has.** SIGINT mid-build
(delivered via `os.kill`; this container's shell builtin turned out to
ignore backgrounded `kill`, which cost three attempts): bga dies with
a raw `KeyboardInterrupt` traceback from `bst_run_wrapped.py:81`; the
snapshot holds `build.log` and nothing else. Mechanism, not accident:
every Plane 2 artifact lives in `capture_scratch` during the build and
is copied out only after `run_wrapped` *returns*
(`tracer:548-562`), so the interrupt skips the copies and the
`finally` rmtree deletes them; `extract_run` never runs on the
completed elements Plane 1 already holds; and the spawned `bst` — with
no process-group handling — **kept building** after bga died. The one
piece that behaves: `--list` labels the husk "(no run directory)" and
`@last` skips it. Filed as **UX-157**: interrupt means salvage —
forward, wait for bst, copy in a `finally`, extract, exit 130.

**The census assesses nothing on real layouts.** Element discovery is
non-recursive `os.listdir` in all three census sites; every example
keeps elements top-level, essentially every real project nests them.
Unassessed elements are traced (UX-113's fail-safe, correctly), so on
the user's project `--trace-spine=auto` — the snapshot default —
silently becomes whole-build ptrace at a cost UX-108 still has not
measured. UX-142's "fixture convention read back as a world fact",
one directory deeper. Filed as **UX-160**.

**The stale casd is checkable and unchecked.** Deferred out of UX-147,
sharpened by the review: doctor's probe isolates `HOME` and therefore
*cannot* reproduce the one cause it most needs to (a fresh casd is
started every probe), while any plain `bst` command before a snapshot
plants a stale one. The question is answerable from `/proc` before
the build starts. Filed as **UX-161**.

**Smaller frictions, same lens**: `--help` is a design-history lecture
(`compare` 143 lines, `cache-logs` 88, `capture run` 82 — module
docstrings fed to argparse verbatim; the docs concision pass never
reached the help surface) — **UX-158**. bga's own phases are silent
for however long they take on a big project, the store shows no sizes
and has no prune — **UX-159**. And the review's small-debt inventory —
the null `buildbox_run_path`, "(empty)" beside a fingerprint-bearing
record, a dead `doctor_exit`, four acceptance-named claims without
tests, the `.bga`-staging caveat — **UX-162**.

## For the user's session tonight

Three practical notes while the filings land, no code needed:

1. **For the first macro-picture capture, pass `--trace-spine=off`.**
   The macro picture is Plane 1's; on a nested-element layout
   auto-spine currently means full-build ptrace (UX-160) at an
   unmeasured cost. Turn it back on per-element later, where the
   census says it matters. (It is sticky — one `--trace-spine=off`
   is remembered; UX-145's announcement will remind you.)
2. **Do not Ctrl-C a capture you want the trace from** (UX-157);
   if the build must die, let an element fail on its own — a failed
   build's artifacts are all kept and extracted.
3. **Before the capture, check for a leftover daemon**:
   `pgrep -a buildbox-casd` — if one is running from an earlier plain
   `bst` command, stop it (`bst shutdown`, or kill the pid; bst
   restarts it) so the capture's PATH is the one it sees (UX-161).
   And read the failed-run verdict with UX-156 in mind: a comparison
   involving a build that did not finish is not a measurement yet.

## Standing

The MVP verdict (round 12) stands. The diagnosability chain the field
failure demanded is landed and verified; what round 16 adds is the
**big-project axis**: the tool's remaining sharp edges are no longer
in what it measures but in how it behaves when the session is long,
the project is deep, and the build does not always finish. Priority
for the sibling: **UX-156 and UX-157 first** (both are what the user's
next unlucky evening looks like), then **UX-160** (it is billing the
user's every capture right now) and **UX-161** (the field failure's
one unwatched cause), then UX-148 from last round, with UX-158/159/162
as the polish tail.
