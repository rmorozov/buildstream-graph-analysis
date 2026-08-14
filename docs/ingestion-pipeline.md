# Ingestion Pipeline: from a real BuildStream run to bga input

This records the design decisions behind `P4-05`/`P4-08`/`P4-09`/`P4-10`
(see `docs/fix-progress-tracker.md`) and the empirical findings behind
them, so a future session doesn't have to re-derive or re-discover any
of this. If you're picking up one of those tasks, read this first.

## Target architecture

```
real bst invocation (wrapper log OR raw log OR direct)
        |
        +--> tools/bst_log_to_chrome_trace.py --> Chrome Trace JSON (P4-05, done)
        |          |                                (also the user's own real
        |          |                                 perfetto.dev visualization
        |          |                                 path - unchanged)
        |          v
        |    tools/chrome_trace_to_bga_trace.py --> trace/v9 (done)
        |
        +--> tools/bst_show_to_graph.py       --> graph/v9 (P4-08, done)
        |
        +--> tools/bst_run_context.py         --> run-context/v9 (P4-09, done)
        |
        v
   tools/bst_extract_run.py (P4-10, done) coordinates all of the above
   from one project dir + one log into one complete run directory
        |
        v
   bga ingests it, produces a report - verified working end-to-end
   against a real BuildStream 2.7.0 build with zero manual editing
```

`bga` itself stays a pure analyzer of already-v9-shaped input (Part 32).
The extraction tools are separate, small, single-purpose scripts under
`tools/` - not folded into `bga`'s own package - because they depend on
a real `bst` binary (+ bubblewrap) being installed, which most of
`bga`'s own test/dev environment does not need and should not be forced
to install. `tests/unit/test_bst_show_to_graph.py`, `test_bst_extract_run.py`,
and any other `bst`-dependent tests skip automatically when `bst` isn't
on `PATH` (see `pyproject.toml`'s `bst` optional extra).

`tools/bst_log_to_chrome_trace.py` produces Chrome Trace JSON, not
trace/v9, directly - that's deliberate, not an oversight: it's also the
user's own real, already-in-use tool for visualizing a build's timeline
in `ui.perfetto.dev`, and that output shape must keep working exactly as
before. `tools/chrome_trace_to_bga_trace.py` is a second, separate,
general-purpose tool that does the trace/v9 conversion - see "Why a
second, separate trace/v9 adapter" below for why this isn't the same
thing as `tests/fixtures/synthetic_multi_subproject/adapter.py`.

## Why `bst show`, not raw `.bst` YAML parsing

Considered and rejected: parsing `.bst` element files directly. BuildStream's
own dependency resolution (junction composition, the `all`-type default,
"a build-dependency pulls in its own runtime dependencies transitively")
is non-trivial and already correctly implemented by BuildStream itself;
reimplementing it in `bga`'s tooling would be a second, likely-diverging
copy of that logic. `bst show` gets this resolution for free. The
trade-off (a real `bst` + bubblewrap install needed to run the
extraction) was judged worth it - confirmed on 2026-08-14 against a
real `bst show`/`bst build` (BuildStream 2.7.0).

## Empirically confirmed facts (2026-08-14, against real `bst` 2.7.0)

Do not re-guess these from documentation alone - they were confirmed by
actually installing BuildStream (`pip install buildstream
buildstream-plugins`, `apt install bubblewrap`) and running real
commands against a small from-scratch project
(`tests/fixtures/bst_show_project/`).

1. **`--format` has `%{build-deps}`/`%{runtime-deps}`/`%{deps}` symbols**
   in BuildStream 2.x (absent from some older/mirrored manpage
   snapshots, which briefly suggested a `bst show`-per-element +
   transitive-reduction approach was needed - it is not). Each returns
   the element's own **direct** dependencies, not a transitive closure.
2. **That value can contain embedded newlines** when an element has
   more than one dependency of that type (rendered as one `"- name"`
   line per dependency). A naive line-by-line stdout parser silently
   corrupts any multi-dependency element's record. `bst_show_to_graph.py`
   works around this by delimiting the whole record set with ASCII
   `\x1e`/`\x1f` (record/field separator) control characters baked
   into the `--format` string itself, and parsing the full stdout blob,
   never splitting on `\n`.
3. **`bst show`'s progress/log output goes to stderr, never stdout** -
   confirmed by capturing both streams separately. `--format` output on
   stdout is clean (no interleaved log lines), so the parser doesn't
   need to filter anything out of stdout.
4. **Junction-qualified element names round-trip identically** between
   `bst show`'s `%{name}` and a real `bst build`'s own log lines (both
   render `junction-name:element-name` the same way, confirmed by
   actually running `bst build` and diffing the log line against `bst
   show`'s output for the same element). This was the single highest-risk
   unknown before implementing `P4-08`: if `tools/bst_log_to_chrome_trace.py`
   (trace side) and `bst_show_to_graph.py` (graph side) disagreed on
   how to spell a junctioned element's name, `graph.json`'s
   `dependencies`/`trace.json`'s `task_key.element_uid` would silently
   fail to join, with no obvious error. They agree - no changes were
   needed to the existing log converter for this.
5. **A dependency with BuildStream's default type (`all`, i.e. both
   build and runtime) appears in *both* `%{build-deps}` and
   `%{runtime-deps}`** for the same element. `bst_show_to_graph.py`
   collapses this to a single `dependency_type: "build"` edge (a strict
   superset of what `"runtime"` alone would constrain) rather than
   emitting two edges - `graph/v9`'s schema (Part 32.2) models one type
   per edge, and nothing downstream (`bga/graph/edg.py`,
   `bga/normalize/timestamps.py`) reads `dependency_type` as a genuine
   tri-state today anyway (see the next section).
6. **`%{key}` (cache key) is available even before a build runs** (a
   `waiting`-state element already has a real key), but the docs' own
   caveat - "if all sources are consistent" - is real: an element with
   an unpinned/unresolvable source ref can return an empty key. Maps to
   `cache_key: null`, never a fabricated placeholder.
7. **BuildStream's `git` source plugin is not bundled** in the base
   `buildstream` PyPI package as of 2.x - it's in the separate
   `buildstream-plugins` package. `tests/fixtures/bst_show_project/`
   deliberately uses only `kind: local` sources so its tests need no
   network access and no extra plugin package; a project using `git`
   sources needs `buildstream-plugins` installed too.
8. **`bst show`/`bst build` need a working sandbox backend (bubblewrap,
   the `bwrap` binary) even to run `show`** (static introspection) -
   BuildStream's platform initialization is unconditional. `apt install
   bubblewrap` (or the equivalent for your OS) is required alongside
   the `bst` optional extra, not just `pip install buildstream`.

## Empirically confirmed facts about real BuildStream *logs* (2026-08-14, against real `bst` 2.7.0)

Confirmed by actually running real builds (success and failure cases)
against `tests/fixtures/bst_show_project/` and a throwaway `kind: manual`
project, and by reading BuildStream's own source
(`buildstream/_frontend/widget.py`, `buildstream/_context.py`,
`buildstream/data/userconfig.yaml`) - not assumed from the log line
*shape* alone (`[elapsed][hash][action:element] STATUS message`), which
several wrong assumptions turned out to hide behind:

1. **The status word for a real failure is `FAILURE`, not `FAIL`.**
   `tools/bst_log_to_chrome_trace.py`'s original `BST_LOG_RE` alternation
   only had `FAIL` - a real build failure never matched at all, in
   *either* wrapped or raw mode, silently leaving the task "active"
   forever (no `E` event ever emitted). Invisible against
   `tests/fixtures/synthetic_multi_subproject/`, whose synthetic model
   never generates a failing build. Fixed by adding `FAILURE` to the
   alternation (kept `FAIL` too, untested but harmless to tolerate).
2. **START/SUCCESS message text is not a phase description - it's a log
   file path** (e.g. `bst-show-test-project/base/4a9059d4-build.log`)
   for the *outer* per-(hash, action) bracket, confirmed directly in
   BuildStream's own source: "START and SUCCESS messages are expected to
   have no useful information in the message text, so we display the
   logfile name for these messages" (`_frontend/widget.py`). The
   synthetic fixture's own adapter (`tests/fixtures/synthetic_multi_subproject/adapter.py`)
   recovers task kind by pattern-matching invented phase text ("Running
   build commands") - that only works because the synthetic model
   generates log lines that way; it is not how a real BuildStream log
   looks, and would not work against one. The real, general adapter
   (`tools/chrome_trace_to_bga_trace.py`) instead reads the `action` word
   (`track`/`fetch`/`build`/`pull`/`push`) already present in the log
   line's own `[hash][action:element]` bracket - `bst_log_to_chrome_trace.py`
   now carries it straight through into each Chrome Trace event's
   `args.action` (and `args.element`), an additive change verified
   byte-for-byte harmless to the pinned synthetic-fixture test (it never
   reads `args` on `B` events at all).
3. **A single real task emits one *outer* START/terminal bracket plus one
   or more *nested* START/terminal pairs for internal sub-phases**
   ("Staging sources", "Caching artifact", …), all sharing the *same*
   hash+action key. Confirmed on a real build:
   ```
   [--:--:--][4a9059d4][build:base.bst] START   base/4a9059d4-build.log
   [--:--:--][4a9059d4][build:base.bst] START   Staging sources
   [00:00:00][4a9059d4][build:base.bst] SUCCESS Staging sources
   [--:--:--][4a9059d4][build:base.bst] START   Caching artifact
   [00:00:00][4a9059d4][build:base.bst] SUCCESS Caching artifact
   [00:00:00][4a9059d4][build:base.bst] SUCCESS base/4a9059d4-build.log
   ```
   The pre-existing "a new START force-closes whatever's already open for
   this hash" handling would have produced 2-3 spurious short spans per
   real build task instead of one correct one - a real correctness bug
   for real logs (both wrapped and raw), invisible against the synthetic
   fixture (whose model only ever emits one START per task, no nesting).
   Fixed with a per-(hash, action) depth counter in `handle_bst_event`:
   only the depth 0→1 `START` opens a span and only the matching depth
   1→0 terminal status closes it - verified byte-identical on the
   synthetic fixture (it never nests, so the counter never exceeds 1
   there) and verified against the real nested sequence above (exactly
   one span, `Status`/`Message` reflecting the *final*, outer terminal
   event even when an inner sub-phase failed along the way).
4. **BuildStream's real concurrency flags are `--builders`/`--fetchers`/`--pushers`**
   (global flags, before the subcommand) - `--max-jobs` is a *different*
   concept ("Number of parallel jobs allowed for a given build task",
   confirmed in `_context.py`: `effective_build_max_jobs`, e.g. `make -j`
   parallelism *within* one task), not what `run-context/v9`'s `max_jobs`
   field means. `resource_capacities`/`max_jobs` map as: `PROCESS =
   builders`, `DOWNLOAD = fetchers`, `UPLOAD = pushers`, `max_jobs =
   builders` - confirmed against Part 27's own critical-path resource-mix
   table (`FETCH / PULL / DOWNLOAD`, `PUSH / UPLOAD`) for the PULL/PUSH
   mapping specifically.
5. **BuildStream's bundled scheduler defaults** (`buildstream/data/userconfig.yaml`,
   used whenever no `--builders`/`--fetchers`/`--pushers` override and no
   user config file overrides them either): `fetchers: 10`, `builders:
   4`, `pushers: 4`. `tools/bst_log_to_chrome_trace.py`'s `bst_max_jobs`
   default (`4`) predates this investigation and turned out to already
   match the real default by coincidence - now explicitly justified
   rather than an unexplained guess, and extended with real
   `bst_fetchers`/`bst_pushers` defaults too.
6. **BuildStream prints its own already-resolved scheduler limits
   unconditionally**, as standalone header lines (`Maximum Fetch Tasks:
   10`, `Maximum Build Tasks: 4`, `Maximum Push Tasks: 4` - no
   `[hash][action:element]` bracket at all, unlike per-task lines).
   Reading these directly (`get_scheduler_config()`) is more robust than
   re-parsing `--builders`/`--fetchers`/`--pushers` CLI flags ourselves,
   since BuildStream has already applied whatever precedence it uses
   (CLI flag > user config > bundled default) - `tools/bst_run_context.py`
   (P4-09) relies entirely on this rather than re-deriving precedence.
7. **BuildStream prints the real, resolved target list unconditionally**
   too: `Targets:       base.bst, base2.bst` (comma-space-separated,
   present in both wrapped and raw logs since it comes from BuildStream
   itself, not a wrapper). This is what `tools/bst_extract_run.py`
   (P4-10) uses for target derivation - more robust than parsing a
   wrapper's own shell command line (which only exists for wrapped logs
   and needs shell-quoting-aware parsing).
8. **`local` sources still run a (fast) FETCH phase** in real BuildStream
   - they are not skipped just because there's no network fetch to do.
   Confirmed on `tests/fixtures/bst_show_project/` (all `kind: local`):
   every element still gets a real `fetch:` bracket in the log.
9. **A fully-cached build (nothing to do) produces *no* per-task log
   lines at all** - not even a `CACHED` status line for the queue -
   confirmed by rebuilding an already-built project: the "Pipeline"
   summary shows `cached` for every element, and the queue-processing
   section is entirely empty. `CACHED`/`SKIPPED`/`SKIP` remain in
   `BST_LOG_RE`'s status alternation for tolerance (plausible for other
   queue actions, e.g. artifact `pull`) but were not positively confirmed
   the way `FAILURE` was.
10. **Elapsed-time precision without `--verbose`'s microsecond mode is
    1-second resolution** (`HH:MM:SS`, no fractional part) - a build
    fast enough to complete within one second produces *every* event at
    the same elapsed value, and therefore (in raw mode) the same absolute
    timestamp. This is a real, inherent precision limit of raw-log
    timestamps for fast builds, not a bug - `tests/fixtures/bst_show_project/`'s
    own real end-to-end test run produces 0-duration spans for exactly
    this reason. A wrapped log doesn't have this problem (it anchors on
    the wrapper's own per-line UTC timestamp, not BuildStream's elapsed
    prefix).

## Why a second, separate trace/v9 adapter

`tests/fixtures/synthetic_multi_subproject/adapter.py` stays exactly as
it is - it's correct for what it does (converting the *synthetic*
model's own Chrome Trace output, which uses invented phase-message text
by construction) and is pinned by `tests/test_synthetic_multi_subproject.py`.
`tools/chrome_trace_to_bga_trace.py` is a new, general, real tool built
alongside `P4-10` specifically because that fixture-specific approach
(recover task kind from message text) does not work against a real
BuildStream log at all (see fact 2 above) - a genuinely different tool
for a genuinely different, real-data problem, not a refactor of the
fixture-only one.

## `dependency_type`'s effect on analysis - still open, now filed as `P4-11`

`DependencyEdge.dependency_type` (`bga/ingest/models.py`) is populated
correctly by `bst_show_to_graph.py`, but **every consumer in `bga/`
still treats every edge identically** as a hard precedence constraint
(`bga/normalize/timestamps.py`'s ready-time gating, `bga/graph/edg.py`'s
structural algorithms, `bga/attribution/blame_chain.py`,
`bga/replay/scheduler.py`) - confirmed by grep, not yet fixed. Per
BuildStream's own semantics (confirmed via its docs): a `build`-type
edge genuinely gates the successor's build start (the dependency's
product must be staged first); a `runtime`-only edge does not - "an
element's runtime dependencies are not available to the element at
build time." Ready-time/critical-path gating (Part 7) should therefore
only apply to `build`/`all`-type edges; a pure `runtime`-only edge
should still count for structural analysis (reachability, blast
radius, leaf/deferrability, Part 24/25) but shouldn't force the
successor's build to wait. Now that `P4-10`'s real end-to-end pipeline
exists (real `dependency_type`-carrying input to test against, not only
synthetic fixtures), this is filed as its own task - see `P4-11`.

## A note on time-of-extraction consistency

`graph.json`'s cache keys and dependency structure reflect the project
state *at the moment `bst show` runs*. If graph extraction happens at a
different time/commit than the build being analyzed, cache keys can
silently stop matching what was actually built, corrupting cold-floor
duration matching (Part 15.2) with no error raised anywhere.
`tools/bst_extract_run.py` (P4-10) does a best-effort check for this: if
the project directory is a git repository, it warns (does not fail) when
the working tree is dirty (`git status --porcelain` non-empty) - the
strongest signal available post-hoc, since a real BuildStream log
carries no commit hash to compare against directly. This is a real,
acknowledged limitation, not a full guarantee: a *clean* tree can still
be at the wrong commit relative to what was actually built if extraction
runs later against a since-moved branch. The most reliable fix is
structural, not detectable after the fact - run graph extraction from
the same checkout as the build it's paired with, ideally the same CI
step, not as an independently-schedulable one.
