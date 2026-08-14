# Ingestion Pipeline: from a real BuildStream run to bga input

This records the design decisions behind `P4-05`/`P4-08`/`P4-09`/`P4-10`
(see `docs/fix-progress-tracker.md`) and the empirical findings behind
them, so a future session doesn't have to re-derive or re-discover any
of this. If you're picking up one of those tasks, read this first.

## Target architecture

```
real bst invocation (wrapper log OR direct)
        |
        +--> tools/bst_log_to_chrome_trace.py --> trace/v9 (P4-05)
        |
        +--> tools/bst_show_to_graph.py       --> graph/v9 (P4-08, done)
        |
        +--> (not yet built)                  --> run-context/v9 (P4-09)
        |
        v
   bga ingests all three, produces a report
```

`bga` itself stays a pure analyzer of already-v9-shaped input (Part 32).
The extraction tools are separate, small, single-purpose scripts under
`tools/` - not folded into `bga`'s own package - because they depend on
a real `bst` binary (+ bubblewrap) being installed, which most of
`bga`'s own test/dev environment does not need and should not be forced
to install. `tests/unit/test_bst_show_to_graph.py` and any future
`bst`-dependent tests skip automatically when `bst` isn't on `PATH`
(see `pyproject.toml`'s `bst` optional extra).

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

## `dependency_type`'s effect on analysis - still open (`P1-30`-adjacent, not yet implemented)

`DependencyEdge.dependency_type` (`bga/ingest/models.py`) is populated
correctly by `bst_show_to_graph.py` now, but **every consumer in
`bga/` still treats every edge identically** as a hard precedence
constraint (`bga/normalize/timestamps.py`'s ready-time gating,
`bga/graph/edg.py`'s structural algorithms, `bga/attribution/blame_chain.py`,
`bga/replay/scheduler.py`) - confirmed by grep, not yet fixed. Per
BuildStream's own semantics (confirmed via its docs): a `build`-type
edge genuinely gates the successor's build start (the dependency's
product must be staged first); a `runtime`-only edge does not - "an
element's runtime dependencies are not available to the element at
build time." Ready-time/critical-path gating (Part 7) should therefore
only apply to `build`/`all`-type edges; a pure `runtime`-only edge
should still count for structural analysis (reachability, blast
radius, leaf/deferrability, Part 24/25) but shouldn't force the
successor's build to wait. This is real follow-on work, not yet
scoped as its own tracker task as of this writing - do that once
`P4-09`/`P4-10` land and there's real `dependency_type`-carrying
input to test against, rather than only synthetic fixtures.

## Two remaining pieces (not yet built)

- **`run-context.json` producer** (`P4-09`): resource capacities,
  `max_jobs`, wall-clock bounds. These come from the real invocation's
  own environment/config (e.g. `bst`'s `--builders`/config file,
  `/proc/cpuinfo` or similar for `effective_cpus`, the wrapper log's
  own start/end timestamps) - not from `bst show`, which has no notion
  of runtime resource capacity at all.
- **Wiring** (`P4-10`): a convenience command or script coordinating
  `bst_log_to_chrome_trace.py` (trace) + `bst_show_to_graph.py` (graph)
  + the new run-context producer into one full `bga`-ready run
  directory from a single real invocation, including deriving the
  target list from the actual invocation (the wrapper log's own
  `Executing command: ... bst build <targets>` line) rather than
  requiring a project-specific umbrella target convention like
  `all.bst` - keeps `requested_target` honest relative to what was
  really built, and works for projects that build several independent
  targets rather than one umbrella element.

## A note on time-of-extraction consistency

`graph.json`'s cache keys and dependency structure reflect the project
state *at the moment `bst show` runs*. If graph extraction happens at a
different time/commit than the build being analyzed, cache keys can
silently stop matching what was actually built, corrupting cold-floor
duration matching (Part 15.2) with no error raised anywhere. Whatever
wires these tools together (`P4-10`) should run graph extraction from
the same checkout as the build it's paired with - ideally the same CI
step - not as an independently-schedulable step.
