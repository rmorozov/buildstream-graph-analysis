# Audit round 6

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping. Rounds 7-10 were always separate files; rounds 2-6 had accumulated inside the design doc, which made it an argument about direction *and* a changelog. The text below is unedited apart from heading levels.

## What the sixth round found (2026-08-17)

The round set out to do the one thing the fifth named as most valuable —
capture a **real timeline** from a real project, not just a real graph.
It ended up finding two defects that had nothing to do with scale and one
piece of infrastructure the project needed all along.

### Getting a real project to build at all

`freedesktop-sdk` cannot be built from the container this repository is
worked on from, and this was established rather than assumed. Two
independent blocks, both network policy:

- its bootstrap seed is a 238MB OCI image on
  `cdn.registry.gitlab-static.net`, which the egress proxy refuses with
  `403` to `CONNECT` (the registry API host itself answers normally, so
  it is specifically the blob CDN);
- its own artifact/source cache at `cache.freedesktop-sdk.io:11001`
  accepts the `CONNECT` and then resets the TLS handshake.

Nothing in the project avoids this: the only elements with no
dependencies at all are config/import elements that perform no build
work.

So the capture moved to a GitHub-hosted runner
(`.github/workflows/real-project-capture.yml`), and the method is worth
recording because both obvious approaches fail in opposite directions.
Building from source is a full compiler bootstrap and does not fit a CI
job; building with the project's own artifact cache enabled produces a
timeline in which *nothing was built*, only pulled. The workflow does
both: **warm** the local cache from the project's remote, **cut** a
bounded subgraph's artifacts, then **capture** a rebuild with remotes
ignored, so exactly that subgraph builds from source on top of a cached
base with its real dependencies, parallelism and durations.

The cut set cannot be arbitrary, and this is the part that is easy to get
silently wrong: BuildStream builds an element when *its own* artifact is
missing, so a cached dependent is never rebuilt and never asks for its
dependencies at all. The delete set has to be **upward-closed** over
build edges, up to and including the requested target, or the build stops
short of it and the capture is empty. `tools/bst_rebuild_set.py` computes
that closure from the same `graph.json` the graph extractor already
produces.

Three iterations of that workflow each taught something, and each is
recorded in its commit:

1. `bst build` is the wrong verb for the warm phase — it finished in
   **7 seconds**, because when the target's artifact is already in the
   remote there is nothing to build and therefore nothing to pull. The
   101 dependencies stayed uncached. `bst artifact pull --deps all` asks
   for the closure explicitly. A guard now asserts that the set
   BuildStream considers un-built after the cut is *exactly* the set that
   was deleted, before anything expensive starts — because the failure
   mode's only symptom was a job that times out two hours later for an
   unrelated-looking reason.
2. Workflow artifacts are served from `*.blob.core.windows.net`, which
   the same egress policy blocks — so the obvious way to get a capture
   out of CI does not work from here. The capture is also pushed to a
   branch, which has the better property anyway: a capture becomes a
   versioned, fetchable object rather than something that expires in
   fourteen days.
3. The build died on every element with `bwrap: loopback: Failed
   RTM_NEWADDR: Operation not permitted`, and the honest response was to
   *measure* rather than guess whether the Plane 2 PATH shim was
   responsible. The workflow now retries a failed traced build **without**
   the tracer; both failed identically, which exonerated the tooling and
   pointed at Ubuntu 24.04's
   `kernel.apparmor_restrict_unprivileged_userns=1`.

### `UX-53`: two duration definitions, found on a fixture that predates round 1

The cross-check sweep — written from scratch at the start of every round
since the third, and now checked in as `tools/bga_cross_check.py`
precisely because it has found something every time it was pointed
somewhere new — was aimed at `tests/fixtures/synthetic_multi_subproject`
for the first time, and disagreed:

```text
structural.sensitivity.critical_path_us   144500000
floors.t_infinity_observed                118000000
```

`UX-52`'s acceptance criterion states in as many words that those two
must be equal. They were 22% apart, and in the *unsafe* direction for a
quantity Part 14.1 certifies as a floor. The gap is exactly the FETCH and
TRACK time along the critical path (20.0s + 6.5s), because `UX-50` had
built a *second* per-element duration map by summing an element's tasks,
while `analyze_graph` — three hundred lines away — already took their
maximum.

The lesson is now three rounds old and getting sharper each time. `UX-50`
was about fixture *durations*, `UX-52` about fixture *dependency types*,
and this one about **tasks per element**: every fixture that pinned this
invariant gives each element exactly one task, where max and sum
coincide, so both `UX-50` and `UX-52` tested it and neither could fail.
What is new is that the fixture with the right shape *was already in the
repository*. Nothing had ever pointed the sweep at it. The scarce
resource was not data, it was attention.

### `UX-54`: a failed build scores 1.00, and the CI gate lets it through

The capture that finally came back was of a build in which **all four
attempted elements failed** — and `bga` reported `Efficiency Score:
1.00`, never using the word "failed". A build that dies early looks, to a
scheduling model, exactly like a build with nothing left to optimize.

Following that through the CI gate this project exists to support:
efficiency 1.00, confidence 0.14, and `_compare_exit_code` **fails open**
on low confidence by design (`UX-40`). A broken build passes the gate on
scheduling grounds. The fail-open rule is right for a *noisy* signal; a
build that did not complete is a definite fact, and needs the opposite
treatment.

The status was never missing — BuildStream states it, and
`bst_log_to_chrome_trace.py` already carried it into the chrome trace's
End events. It was dropped at the last hop, and **no fixture in this
repository contains a failed task**, so nothing could notice. It took a
real project on a machine where the sandbox did not work.

That is the round's most transferable result: a capture nobody wanted
was the only one that could show it. Every example project here is
written to build cleanly, which means the entire failure axis of the tool
was untested by construction.

### The capture that finally worked

With the sandbox knob cleared, the run went through: **2,801.9 seconds
(46.7 minutes)**, 25 elements rebuilt from source on top of a 101-element
cached base, 12 element kinds, 36 runtime edges, **127,630 traced
processes** in Plane 2 — 155× the largest capture it had ever seen.

What held up, on real data, is worth stating as plainly as what did not:

- **Every cross-check agrees, 8 of 8.** `UX-52`'s runtime-edge gating and
  `UX-53`'s single duration definition both hold on a real project:
  `sensitivity.critical_path_us == t_infinity_observed == 2,796.85s`, and
  an independent longest-weighted-path pass over the raw trace reproduces
  it exactly.
- **`UX-27`'s two-signal design is vindicated by a real build.**
  `Efficiency Score 1.00` alongside `Dispatch Occupancy 33.6%` is not a
  contradiction, it is the point: `T∞` is 2,796.85s of a 2,801.9s
  makespan, so the build genuinely *is* a serial chain
  (`openssl` 487s → `cmake-stage1` **1,226s** → `python3` 496s →
  `bison` → `doxygen` 389s → `libxml2`) and the scheduler has nothing
  left to give. One number says "the scheduler is done", the other says
  "the graph is the problem", and only having both makes that legible.
- **Plane 2 survived the scale.** 127,630 processes, `getrusage` CPU time
  for 119,590 of them (93.7% coverage), no crash, no corruption.

And two things it measured about itself:

- **The hook's fixed per-process path budget is naive at this scale.**
  Round 5 recorded it as "8192 slots / 256 KiB, chosen without evidence"
  and said a large real build was what would settle it. Settled:
  **149,053 dropped paths against 65,101 recorded**, a 70% drop rate. The
  `dropped` counter existing is what let this be answered rather than
  guessed, which is the design working as intended.
- **`UX-56`**: 99.4% of those processes were tagged with
  `buildstream-build`, `freedesktop-sdk`'s build root, because the
  element tag comes from bwrap's `--dir` — the element only under
  BuildStream's *default* build-root layout. Every per-element Plane 2
  figure became a whole-build figure wearing an element's name, and
  `bga correlate`'s join key was not an element UID at all.

And one that only a real *cache* could show — **`UX-55`**: 101 of the 126
elements were cached, and `bga` reports a cached critical-path element as
"no matching task found - genuine coverage gap, worth investigating",
failing a hard gate. That drives confidence down, which makes
`UX-03`/`UX-39`'s regression gate fail open. The better the cache works —
the entire point of BuildStream — the less `bga` gates. That is the CI
story's real blocker, and no fixture could contain it: every fixture here
is a full build in which nothing is cached.
