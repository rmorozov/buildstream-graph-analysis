# Audit round 15: a field failure the tool cannot see

Run on 2026-08-20, same retained environment as rounds 10-14. Two
inputs this round: the sibling's landings for round 14's filings
(UX-135..UX-139 docs, UX-140..UX-146 verification findings, including
the first task ever filed from a real user report), and that same
user's field experience — the first deployment of `bga` outside this
repository, on Ubuntu 24.04, against a real project. Two things
happened there: `bga snapshot -- bst build <element>` died with
`buildbox-run failed with returncode 1` and nothing else (a plain
`bst build` works; plane 1 capture from two rounds ago works; turning
opens and spine off changes nothing), and the deployment shape itself —
bga checked out in one directory, installed into the venv of a project
in another — turned out to be a shape nothing had ever tested.

The round's job was therefore different from rounds 11-14: not only
verify the landings, but reproduce the field failure if possible, and
where it is not reproducible, make the tool able to diagnose it in the
field. The result is the diagnosability chain: UX-147..UX-150.

## The deployed shape, rebuilt by hand — and it works

The second report first, because it was testable. The user's shape,
reproduced end to end on this container:

1. `python -m build --wheel` from the checkout → `bga-0.1.0-py3-none-any.whl`.
2. A **fresh venv elsewhere** with `buildstream==2.7.0`,
   `buildstream-plugins`, and the wheel — no `-e .`, no `PYTHONPATH`,
   no repo on any path.
3. A copy of `examples/06` **outside the checkout** (its `optimized/`
   removed, so nothing repo-shaped remains).
4. `bga snapshot -- bst --builders 4 --max-jobs 4 build all.bst` run
   from a **third directory**.

Full capture: both planes recorded, the `.bga/runs/<stamp>` store
created, `@last` alias live, and the second run auto-compared. The
`--diagnose` mode landed by UX-146 was exercised the same way and
reported `shim ran 1 time(s); 1 rewritten`, with the JSONL record
beside the plane-2 report.

That is the good news, and it falsifies the obvious hypothesis: the
field failure is **not** a packaging or path defect that any
wheel-installed run would hit. But it also means the one configuration
users actually deploy in has zero CI coverage — round 15 proved it
works by hand, and nothing keeps it working. Filed as **UX-150**
(installed-wheel end-to-end capture in the packaging job; README's
Install section teaches the deployed form first, `-e .` as the
contributor mode).

## Where the field failure can hide

Since the shape works here, the failing link is environment-specific.
The round mapped where a `buildbox-run failed with returncode 1` with
no further detail can come from, and measured what this container
would show in each case:

- **The wrapped command failing** (bad element, project error): bst's
  log carries the element's own failure verbatim — verbose, not the
  field symptom.
- **The sandbox failing to start**: simulated with a fake `bwrap` that
  prints to stderr and exits 1 — and the stderr **does** reach
  BuildStream's log on this container. So on the user's stack, either
  their buildbox-run build swallows the child's stderr, or the failure
  happens *before* bwrap ever runs.
- **The shim failing to exec**: the shim is a `#!/usr/bin/env python3`
  script materialized into a temp directory
  (`install_bwrap_shim` copies it verbatim). A noexec temp mount, an
  AppArmor denial on executing from `/tmp`, or a child PATH without
  `python3` all fail the exec *inside buildbox-run* — which then
  reports exactly the field error, stderr swallowed, while UX-146's
  diagnostics record stays **empty** (the shim never ran to write it).
- **The shim never being resolved**: buildbox-run finding `bwrap` by
  absolute path, or — the subtle one — `bst` reusing an
  already-running `buildbox-casd` whose environment predates the
  capture's PATH. Same empty record.

That empty record is the sharp edge: UX-146's zero-invocation summary
currently reads it as "this build ran unmodified and the capture is
empty for that reason, not because the sandbox failed" — the benign
cause asserted, where the field case is almost certainly one of the
other two. Three filings close the region the shim-side record cannot
see:

- **UX-147** — a shim self-probe exec at capture start (fail fast with
  the real errno before a twenty-minute build, not after), the shebang
  materialized as the absolute `sys.executable` at install time,
  stale-`buildbox-casd` detection, and a zero-invocation summary that
  names all three causes with the evidence it has.
- **UX-148** — under `--diagnose` the shim tees the real bwrap's
  stderr per invocation instead of pure-execing (signal semantics
  preserved per the UX-140 contract), a failed build's summary quotes
  the stderr tail, and `bga capture replay-sandbox` re-execs a
  recorded rewritten argv directly — the ten-second local repro for
  argv-specific sandbox failures.
- **UX-149** — `bga doctor --capture`: a canned one-element probe run
  through the *actual chain* (bst → buildbox-run → PATH shim →
  rewritten argv → hook) with every recorder on, reported per link in
  chain order as ok/FAIL/skip, classifying exactly UX-147's causes.
  Doctor today proves the parts with bga's own arguments; nothing
  proves the chain until the user's real build pays for the answer.

For the field case concretely: once UX-147/UX-148 land, the user's
next failing run produces either an immediate self-probe error naming
the errno, a stale-daemon warning, or a diagnostics file whose stderr
tail says what the sandbox objected to — any of which is enough to fix
or file precisely.

## Round 14's landings, verified

The sibling landed all eleven round-14 filings. Spot verification
this round, hands-on where the claim was behavioral:

- **UX-142 (doctor vs `all.bst`)**: `bga doctor` on a project without
  `all.bst` no longer false-FAILs — verified in the foreign-venv repro
  above, where doctor was run before the first snapshot.
- **UX-146 (`--diagnose`/`--no-inject`)**: exercised live; the JSONL
  record and the "shim ran N time(s)" summary behave as filed. The
  zero-invocation blind spot is a *new* finding (UX-147), not a
  regression of this fix.
- **UX-135 (README length/order)**: README is 245 lines; "Use it on
  your real project" begins at line 47, immediately after Install;
  doctor + snapshot are the first commands a real-project user meets.
- **UX-136 (superseded flows)**: `bga baseline` is now taught in the
  README's CI section; the manual three-`--baseline-run` assembly is
  gone from both most-read docs. The one surviving "multiply by
  however many" sentence in `real-project.md` was checked against
  UX-124 and is the **legitimate** no-host-memory fallback, printed
  with the honest parenthetical "(the capture recorded no host memory,
  so this cannot do it for you)" — verified not a defect, recorded
  here so the next reader doesn't re-file it.
- **UX-140** 🟢: the SEIZE-unavailable path now kills the blocked
  child, restores signals and **execs**; wait-status parity
  (traced == untraced == `-15`), pid-identity no-wrapper proof, and
  the seam asserted absent from the injected env — all five acceptance
  assertions present and passing.
- **UX-141** 🟢: one `CONT_SITES` list feeds all three parametrized
  tests, the spine rejects unknown sites with rc 2, and the tier pin's
  37→39 was confirmed by collection (delta correctly attributed to
  UX-142's tests, not its own).
- **UX-144** 🟢 all four clauses; **UX-145** 🟢 all three (sticky-flag
  announcement, `baseline --candidate` through the resolver,
  `memory_envelope_direction()` returning `unchanged` on zero delta).
- **UX-143** 🔴 **item 1 claimed done and not done — the round's
  headline finding.** The new `detach_signal` tests `event != 0`
  before consulting `is_group_stop_signal` — and under SEIZE a
  group-stop *is* an event-stop, so it returns 0 for exactly the case
  it was written for, while the degrade branch the finding was filed
  against still detaches with the old `pass_through` untouched. A
  group-stopped tracee is resumed on all three detach paths; the
  acceptance's state-`T` probe was never written (the range's ten new
  spine tests are all UX-140/141). Verified twice: by the review agent
  and re-verified by hand in `spine.c`. Reopened as **UX-152**. Items
  2-3 (drain-cap release, both guards tightened) are genuinely done.
- **UX-142** 🟡: the headline holds (verified live above), but the
  probe principle stops at the headline — `check_staged_sources` and
  the tracer's census still hardcode `elements/` (seven sites; on a
  nonstandard layout, `--trace-spine=auto`'s census comes back empty
  and everything is traced at full price, silently), the
  wire-into-real-project-CI acceptance clause was dropped unrecorded,
  and `check_compiler` tests presence where the spine needs `-static`.
  Filed as **UX-153**.
- **UX-135..UX-139 (the docs batch)** 🟢 with two slips: the corpus
  arithmetic checks to the line (245 + 147 + 1,811 = 2,203), the
  relocations/glossary/journey-B page all hold — but `real-project.md`
  still has **zero** `bga baseline` (the exact superseded assembly
  UX-136 was filed against survives at its comparison section), and
  UX-138's `toll` sweep stopped one file short of `bga correlate`.
  Both, plus two figure/cross-reference slips, filed as **UX-154**.

The review also surfaced what is now the **strongest remaining
hypothesis for the field failure itself**: the shim's arity table was
validated on bubblewrap 0.9.0 and treats unknown flags as arity 0, so
any newer flag with an operand (`--json-status-fd 12`, `--seccomp`,
`--argv0`, …) makes the split stop at the *operand* — garbage argv,
bwrap exits non-zero, `buildbox-run failed with returncode 1`,
unchanged by `--trace-opens`/`--trace-spine`, and `--no-inject` would
succeed. The mis-split detector can't see it (`startswith("-")`, but
these mis-splits put a *number* at `command[0]`) and the diagnostics
record omits every version fact needed to check the table. Filed as
**UX-151** — and it makes the user's `--diagnose` file, once they run
it, decisive either way.

The full suite passes in the round's dev venv: **1,729 passed** (live
bst tier included), the one red being this round's own README link to
`round-15.md` racing the file's creation — green on re-run.

## Standing

The MVP verdict (round 12) stands; the polish direction (rounds 13-14)
has converged — the docs corpus and the command surface stopped
producing findings faster than they close. Round 15 opens the next
axis the first real deployment demanded: **diagnosability** — when the
tool fails in an environment we cannot reach, the artifacts it leaves
behind must be enough to diagnose it remotely.

The priority order for the sibling: **UX-151 and UX-147 first** — the
arity table because it is the likeliest actual cause and its fix is
cheap, the self-probe because it makes the user's *next* failing run
informative either way; then UX-152 (a real correctness bug shipped
under a 🟢); then UX-148, with UX-149 composing them; UX-150, UX-153
and UX-154 are independent.

And for the user's next session on the Ubuntu 24.04 box, the
diagnostic path that needs nothing new to land:
`bga snapshot --diagnose -- bst build <element>` and read the count —
**non-zero**: look at `received_argv` for any flag not in the shim's
table with a bare number as `command[0]` (UX-151's signature);
**zero**: check `bwrap --version`, whether a `buildbox-casd` predates
the capture, whether `TMPDIR` is noexec, and whether buildbox-run is
even the bubblewrap runner; either way `--no-inject` splits the
rewrite from the shadowing. The diagnostics JSONL beside the plane-2
report is the file to send.
