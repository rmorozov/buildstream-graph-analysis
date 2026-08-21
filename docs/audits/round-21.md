# Audit round 21: the viewer argued, the field round verified

Run on 2026-08-21, same retained environment as rounds 10-20. Two
threads: verification of round 20's ten field-feedback landings, and
the round's design work — the user's call that *"we are on the verge
of necessity for making a viewer"*, argued as
[Direction 7](../design/directions.md) and decomposed into four
filings.

## Round 20's landings, verified — all ten hold

The review re-ran four mutations (the progress gate, the sources
complaint, a dropped compare field against the schema guard, and the
help-guard coverage), drove the pip-through-blast and 68-char paste
cases live, and timed the synthetic budget test. Highlights:

- **UX-183** — the Ticker's gate order is right, zero bytes on a
  non-TTY, stdout untouched by architecture. One claim outran its
  test: the byte-identity comparison runs progress-off against
  progress-off (no force-on mechanism exists), so it proves nothing
  about progress — and the `bst show` Popen change lost
  kill-on-exception, so Ctrl-C there now orphans the child. Both in
  **UX-197**.
- **UX-185** — the suspend detection is real end to end (clock pair
  in the log, derived 5s threshold, backwards-step excluded, compare
  exit 6 with the sentence, `--inhibit` wrapping what is launched and
  never what is recorded). The guards even caught a four-round-old
  wording defect: findings.py called every incomplete build "FAILED:
  0 element(s)". One dead field (`RunContext.suspended`) → UX-197.
- **UX-186** — the host manifest classifies on exactly the three
  fields that move durations, the gates fail closed with
  `--allow-cross-host` as the deliberate override, old runs stay
  usable as "host unknown", and the `host`/`host_manifest`
  coexistence has its own guard.
- **UX-188/UX-192** — `bga timeline` merges both planes into a
  Perfetto-loadable legacy JSON array; the table stopped eliding (a
  key you cannot paste is not a key) with a 68-char fixture; the pip
  keying sentence through blast is correct. The one surviving wart:
  the Plane 1 converter still prints "Open <scratch-path>" about a
  file deleted moments later — the stream moved, the sentence stayed.
  **UX-197**.
- **UX-190/UX-191** — the schemas are stamped and self-declared, the
  round-trip guard reddens on a dropped field (re-verified by
  mutation), `--schema` answers before argparse demands a run, and
  argcomplete is wired inert-by-default. Environment note that became
  a UX-197 item: without dev extras the whole schema-guard module
  *skips silently*.

Suite on the committed range: **2,358 passed** (2,389 with the bst
tier), lint clean, status table and markers agree for all ten. Two
stale counts found in the audit commit itself — "twelve items" for
ten, in the very commit titled "two counts the prose outgrew".

## Direction 7: the viewer

The design's one load-bearing rule: **the published JSON is the
entire interface.** UX-190 made every output self-declare a schema;
the viewer consumes exactly those payloads — no private endpoints, no
viewer-side semantics — which yields the two properties that keep it
thin: anything the viewer should show must first enter the published
schema (so the text renderer, CI and external tools get it too), and
the page renders the *schema*, not the report (so new fields render
with zero viewer changes). The "dozens of cool TypeScript libraries"
get their door the same way: view-hints (`bga:quantity`,
`bga:severity`, column order) in the JSON Schema, so any tool that
reads schemas can chart the reports without bga blessing a frontend
stack.

Decisions argued in the direction:

- **Server**: stdlib `http.server`, `127.0.0.1`, ephemeral port,
  `webbrowser.open` — no Flask, no node toolchain, no build step;
  vanilla ES modules checked into the repo.
- **Timelines**: wholesale to ui.perfetto.dev via the documented
  deep-link handshake (~30 lines, tab-to-tab — worth one docs
  sentence because it looks like an upload and is not);
  `--perfetto` for the direct path; the SQL engine exposed as a
  canned-PerfettoSQL page rather than a feature.
- **Format**: stay on legacy Chrome JSON — Perfetto ingests it,
  protobuf buys density we do not need yet; the revisit trigger is
  named (a trace too large to post), and it is UX-169 territory
  before it is a format problem.
- **Two delivery modes, one page**: served locally, or exported as a
  single self-contained file (`--export`) for CI artifacts and
  "send me your report".
- **Deliberately deferred**: the dependency-DAG view — the one panel
  needing a real graph library waits for a concrete question.

Filed as **UX-193** (server + shell + schema-driven rendering +
view-hints v1), **UX-194** (the Perfetto handoff), **UX-195** (the
export mode), **UX-196** (the band drawn, the store trend, the blast
explorer — plus `store/v1`, the one payload the views need that does
not exist yet).

## Standing

The MVP verdict stands. The field round closed clean — ten items,
ten holds, six seams — and the project now has its third design axis
in five rounds (sources, then the field batch, now the viewer),
each driven by the user's actual use rather than speculation.
Priority for the sibling: **UX-197 first** (six one-sitting seams,
two of them user-visible today), then **UX-193** — the viewer core
is the axis-opener and everything else in Direction 7 builds on its
shell; UX-194 next (the handoff is the user's headline ask), then
UX-195/UX-196 in either order. The review's ground truths are
already folded into the filings: `bga timeline` emits a bare-array
legacy trace Perfetto loads, `findings[]` carry severity on every
finding (the schema should say so — UX-193's hints make it so), and
nothing in the repo serves HTTP today, so UX-193 starts clean.

## Landed

All five items UX-193..UX-197 are 🟢 Done, in this branch. The status
table carries each one's measured outcome; the task files carry the
falsification logs.

**Direction 7 exists now.** `bga view` serves one run's published JSON
behind an allowlist of four documents and four assets — no listing, no
write method, no filesystem fall-through. The page renders the
*schema*: `app.js` holds no list of the report's fields, and the
discriminating guard adds a field that did not exist when it was
written, asserts it renders, and hashes `app.js` to make "no viewer
change" literal. `--perfetto` hands the timeline over tab-to-tab
(**272,964 B → 24,782 B gzipped**, 9.1%); `--export` writes one
self-contained file (**82 KiB** for a real capture with its timeline,
**638 KiB** at 1,202 elements, of which the page is 6.0%).

**What only real runs found.** The acceptance names `examples/06`, so a
real `bst build all.bst` was captured under `bga snapshot` — 46.1 s, 9
findings, 14 renderable sections — and it found two things every unit
test had missed: `bga view @last` resolved to the *snapshot* instead of
the run one level in, and the schema did not declare `pipeline_overhead`
or `timestamp_agreement`, both present on every wrapper-derived run and
absent from the golden fixture `UX-190`'s guard validates. `UX-179`'s
shape, in the guard `UX-190` built to prevent exactly it.

**The round's dominant finding is about guards, not code.** Of the
defects fixed here, **eight were guards that could not fail**:

- `UX-183`'s byte-identity test compared progress-off with
  progress-off — and routing the ticker to stdout, the exact regression
  it exists to prevent, left it *passing*.
- `UX-191`'s element-completer guard stayed green with the branch it
  guarded deleted.
- `UX-189`'s clone-size fixture, twice (a compressible payload, then a
  local clone hardlinking the object store).
- `UX-194`'s origin-check guard asserted a property `postMessage` makes
  untestable.
- `UX-195`'s render guard never touched the loader; its escaping guard
  injected through a computed field.
- `UX-196`'s geometry guard was insensitive to the axis; its blast
  mutation wrote the correct value.

Every one was found by falsifying — and two of them only after two or
three attempts, because a mutation that leaves a guard green looks
exactly like a mutation that was harmless. Three further defects came
from a fix being applied at one caller and not the class: `UX-197`
fixed the doomed scratch path in the Plane 1 converter because
`bga timeline` calls it, and `bga view` reached the *merge* converter
the same way.

The suite stands at **2,495**, the `bst` tier at 43 with none skipped.

