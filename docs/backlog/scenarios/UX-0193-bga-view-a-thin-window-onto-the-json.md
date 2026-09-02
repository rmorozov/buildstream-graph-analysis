# UX-193: `bga view` — a thin window onto the JSON

**Priority:** High | **Status:** 🟢 Done | **Depends on:** Direction 7 (the argument), UX-190 (the schemas this renders) | **Topic:** viewer

## Motivation

The user's request, round 21: the reports have outgrown the terminal —
*"we are on the verge of necessity for making a viewer"* — and the
design constraint that keeps a viewer maintainable is argued in
Direction 7: **the published JSON is the entire interface**. The
viewer renders the schema, not the report; anything it should show
must first exist in `analyze/v1`/`compare/v1`/`blast/v1`, which is
also what lets any external TypeScript library chart the same data
without bga blessing a frontend stack.

## Required Fix

1. **`bga view [RUN]`** (`@last` default, the alias grammar):
   `http.server` on `127.0.0.1`, ephemeral port, `webbrowser.open`,
   `--port`/`--no-browser`. Serves the static page, the run's JSON
   payloads (produced through the same `main()`s the CLI uses, cached
   beside the run), and the chrome trace. Path allowlist — the run's
   own files only; no listing; nothing writable.
2. **The page**: vanilla ES modules checked into the repo, **no node
   toolchain, no build step**. Sections render generically from the
   schema: arrays with column hints → sortable tables; `findings[]` →
   the findings list with severity styling; deltas with direction
   semantics → signed, colored numbers. The verdict banner gives
   refusals (`NOT COMPARABLE`, interrupted, suspended) visual weight.
   A new report field renders with zero viewer changes — that
   property is the acceptance's core.
3. **View-hints v1 in the schemas**: `bga:quantity`
   (duration_us / bytes / share / count), `bga:severity` on findings,
   column order hints — a small vocabulary documented beside Part
   32's output schemas, versioned with them (UX-190's rules apply).
4. Help under the UX-158 cap; one docs section in `cli.md`; the
   README's real-project flow gains one line (`bga view @last` after
   the first snapshot).

## Out of Scope

- The Perfetto handoff (UX-194), export mode (UX-195), comparative
  views (UX-196).
- Any bundler, framework, or npm dependency (Direction 7's rule; a
  richer TS app would be a *consumer* of the schema, not part of
  this).

## Acceptance Test

`bga view @last` on `examples/06` serves a page whose findings,
tables and verdict match `--format json` field-for-field (asserted by
a headless fetch of the served JSON and a DOM-free parse of the
rendered data attributes — no browser dependency in CI). The
zero-viewer-changes property is the discriminating test: add a
synthetic field with hints to a fixture payload and assert it renders
(appears in the served page's generic section) with no viewer-code
change. The server refuses a path outside the run (asserted), binds
localhost only, and `--no-browser` prints the url instead of opening
it. Schemas with hints still validate the golden runs (UX-190's
guard unchanged).

---

## What was built

**`bga view [RUN]`** — `http.server` on `127.0.0.1`, an ephemeral port,
`webbrowser.open` in a thread (so the server is already answering when
the tab arrives), `--port` and `--no-browser`. The payload comes from
`bga.cli.main()` rather than from the renderer directly, so the viewer
and the terminal cannot disagree about what a run says — asserted
field-for-field.

**The security posture is an allowlist, not a root.** Four documents
and three assets; everything else is 404. There is no directory
listing, no write method, no filesystem fall-through, and the asset
path is re-checked with `realpath` against the asset directory. The
mutation that matters is the one this shape exists to prevent: teaching
the handler to serve `os.path.join(run_root, path)` when the table
misses makes `run-context.json` reachable and reddens the guard.

**The page renders the schema, not the report** — `app.js` contains no
list of the report's fields. It asks `schemas.json` what each key *is*
and dispatches on shape plus hints. **The discriminating test** adds a
field that did not exist when `app.js` was written, with nothing but
hints, and asserts it renders — then hashes `app.js` before and after
to make "no viewer change" literal rather than rhetorical. Reverting
the generic dispatch to a hard-coded `KNOWN` list reddens it, which is
the property in one sentence.

**View-hints v1**: `bga:quantity` (a closed set of six),
`bga:severity`, `bga:columns`, `bga:direction`. Annotations, so a
hinted document validates exactly as before — `UX-190`'s guard is
unchanged and still passes. A quantity outside the set, or a hint on a
key the document does not declare, raises when the schema is built;
both are silent otherwise, because the renderer would simply fall
through and print a plausible raw number.

**No toolchain**: three files in `bga/viewer/`, no `package.json`
anywhere in the repository, nothing fetched from a CDN — all three
asserted.

Tests: 31 (`tests/unit/test_the_viewer_renders_the_schema.py`). The
JavaScript is driven through Node against the real `app.js` with a
~40-line DOM shim, so CI needs no browser and the assertions are about
the shipped file. Twelve mutations, each red.

### Two things only a real capture found

The acceptance names `examples/06`, so it was run there: a real
`bst build all.bst` under `bga snapshot`, **46.1 s, 9 findings across
three severities, 14 renderable sections**. Both findings below were
invisible to every unit test, which passed explicit paths.

1. **`bga view @last` did not work.** It hand-rolled the alias gate
   with `resolve_snapshot`, which names the *snapshot*; `analyze` needs
   the *run* directory one level in, so `@last` produced
   `No such file or directory: .../run_context.json`. `bga timeline`
   legitimately wants the snapshot (its `build.log` and raw Plane 2
   log) and this command copied its shape without noticing the
   difference. `run_store.resolve` — which does the gate *and* appends
   the subdirectory, and whose docstring asks every command to route
   its positional through it — is the fix.
2. **The schema under-described real output.** `pipeline_overhead` and
   `timestamp_agreement` are present on every run with Plane 1 wrapper
   data and absent from `tests/fixtures/golden/`, so `UX-190`'s
   round-trip guard had never seen either. `UX-179`'s shape once more:
   a guard passing on the fixture it was built for. Both are declared
   now (an addition, so no version bump), and the new guard asserts the
   *general* property — every key a wrapper-derived run emits is a key
   the schema declares — with a precondition test that the enriching
   fixture really does emit more, since vacuity is how the gap survived
   the first time.

**Deviation from the Required Fix:** none. The `--port`/`--no-browser`
flags, the path allowlist, the hints, the docs section and the README
line are all as specified; the README line cost one line of the
`UX-135` budget, so a two-line comment in the same block was folded
into one to stay at 250.

