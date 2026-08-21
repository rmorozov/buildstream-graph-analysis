# Audit round 20: the field speaks

Run on 2026-08-21, same retained environment as rounds 10-19. Two
inputs: the sibling's single commit landing all of UX-178..UX-182,
and the user's first sustained field feedback — nine observations
from real local use, each of which this round ground-truthed against
the code before filing. The suite stands at 2,169.

## Round 19's landings, verified

All five hold; the review reproduced **nine** claimed mutations
(count-only sorter, stacks-as-building, dropped `known_identity`,
missing junction walk, cwd rules, and more — each reddening exactly
the test its log names) and re-ran the round-trip live: the printed
resource cell pastes back and answers with the same numbers. The
parser-coverage guard genuinely fails on a new uncovered subcommand
(simulated); the verdict-list guard genuinely reads verdicts out of
`compare.py`'s chain (a renamed verdict reddens it); the
`directory:`-keying provenance was checked against installed bst
source (`_elementsources.py` does exactly what UX-180's log claims).
README is 249 lines, inside budget; the glossary is ten rows.

And the round's own class arrived on schedule — two live defects in
the very commit that closed their categories, filed as **UX-192
(High)**:

- The Shared Sources table **elides identities over 43 characters**
  (`"..." + identity[-40:]`), and `known_identity` has no elision
  handling — so the round-trip UX-178 just closed is open again for
  exactly the long forge urls real projects use. Reproduced live
  with a 67-char identity: "Resolved as a path… rebuilds nothing
  here", exit 0. The acceptance fixture passed by being 31 chars —
  the passes-on-the-fixture-it-was-built-for shape UX-179 was filed
  about, recurring one round later.
- `bga blast` builds its keying sentence from `resolved_as`
  (`"url"`), not the resource's kind — a pip resource queried
  through blast says "any commit to this rebuilds all of them", the
  exact sentence UX-181 removed from the table.

Plus six smaller seams (kind-pairing in blast's direct set, the
junctioned path's filesystem form, the path-colon rewrite the UX-181
log over-claims about, pip's dropped index, `git+http`, and the
thirteen alias commands outside every help guard).

## The field feedback, ground-truthed and filed

Each item was checked against the code before it became a filing:

- **Progress vs pipes (UX-183, High).** Long commands hold one phase
  line for minutes. Verified: stdout is already pipe-clean on every
  `--format json` path (47 stderr prints; two converter status lines
  are the only stdout exceptions, carried into UX-188). The filing:
  TTY-gated in-phase progress on stderr, byte-identical non-TTY
  behavior, a stdout byte-identity guard.
- **Import/manual repo paths (UX-184, Medium).** The inventory reads
  sources on *every* element kind (verified live with
  `kind: import`), and bst rejects out-of-project local paths — but
  bga fed one anyway silently mangles it into a colliding identity.
  Complaints instead of silence, and the acceptance imports one real
  sanitized stanza from the field project, because the recipe shape
  in question cannot be guessed from here.
- **Sleep during capture (UX-185, Medium).** Ground truth: `hook.c`
  and `spine.c` stamp `CLOCK_MONOTONIC` — which stops during
  suspend — while Plane 1's wrapper stamps wall clock. A suspend
  makes the planes disagree about the same build and nothing
  notices. The filing: `--inhibit` (systemd-inhibit wrapping, named
  when active, never default), plus drift detection feeding
  `incomplete_reason: suspended` into UX-156's refusal grammar.
- **Cross-host comparison (UX-186, High).** Verified: compare has
  three comparability axes and none is host-shaped;
  `run-context.json` records two numbers that call a laptop and a
  runner the same machine; richer fingerprints exist in two places
  nothing reads. The filing: a host manifest in every capture,
  cross-host caveats with capped confidence, gates exit 6 without
  `--allow-cross-host`, baseline warning on mixed sets. UX-92's 33%
  runner spread is this item's own measurement.
- **Long-output readability (UX-187, Medium).** The critical path
  still prints in full under UX-33's rule, written when paths were
  ten elements. Render every format at 1,202 elements, cap with
  named elisions and `--full-*` flags, JSON never truncates.
- **Chrome tracing and the merge (UX-188, Medium).** The pieces
  exist: `log-to-chrome` works on a snapshot's `build.log` (verified
  live), and `native-to-chrome combined` *is* the plane merge — but
  snapshots don't retain the raw log it needs, a wrong input
  succeeds silently with zero events (reproduced), and the path to
  the merged timeline is three commands with invented paths. The
  filing: retain the raw log (gzipped), `bga timeline @last`, refuse
  empty conversions.
- **The clone weight (UX-189, Low).** Measured: eight `captures/*`
  branches, ~7.8 MiB in one pointer alone, fetched by every default
  clone. `git clone --single-branch` in the docs, fetch-on-demand
  line beside it.
- **Schemas (UX-190, Medium).** Input formats are spec'd; output
  JSON has no schema, no version field, and this very range renamed
  a published compare field silently. Self-declared versions,
  `--schema` from the renderer's own source of truth, a
  validate-the-golden-run guard.
- **Autocompletion (UX-191, Medium).** The need is real; the click
  migration is not: `argcomplete` completes argparse programs as
  they stand. Custom completers for `@`-aliases and element names —
  `bga cache-trend @<TAB>` is the experience the feedback named.
  Click recorded as considered and declined, with reasons.

## Standing

The MVP verdict stands, and the tool now has its second sustained
field report — this one *usage* feedback rather than a failure
report, which is itself the milestone: the first field round (15)
was "it does not run"; this one is "it runs and here is what would
make it pleasant". Priority for the sibling: **UX-192 first** (two
live defects re-opening closed classes, both one-file fixes), then
**UX-186 and UX-183** (the two Highs the user will feel tonight),
then UX-188 (the merge exists — surfacing it is cheap), with
UX-184/185/187/189/190/191 in dependency-free parallel. UX-187's
render-and-measure step should run against the user's own capture if
one can be shared — the 1,202-element synthetic is the floor, not
the target.

## Landed

All ten items UX-183..UX-192 are 🟢 Done, in this branch rather than
a sibling's. The status table carries each one's measured outcome; the
task files carry the falsification logs. Four things the fixes found
that the audit itself had not:

- **UX-192's class recurred inside the fixes.** The `UX-187` Shared
  Sources cap shipped silent (no elision line), the serialized-pairs
  elision reached no code path, `bga timeline <path>` refused an
  explicit path, and the `UX-191` snapshot completer called `os` in a
  module that does not import it. Every one was caught by the guard
  written for its own item, not by review.
- **A four-round-old defect surfaced from UX-185's angle.**
  `findings.py` called an interrupted *and* a suspended capture "THIS
  BUILD FAILED: 0 element(s) ended in FAILURE ()" — `UX-156` gave
  `incomplete_reason` three values and the headline had only ever
  branched on one.
- **Three guards were found guarding nothing, by falsifying them**
  (`UX-191`'s element completer; `UX-189`'s clone-size fixture, twice
  over). The discipline earns its cost: a mutation that leaves a guard
  green is the only way to learn it was never a guard.
- **UX-189 would have shipped a break.** Documenting
  `--single-branch` without item 3 would have left
  `git show origin/captures/…` in the workflow doc, which under that
  clone is `fatal: invalid object name`.

Two counts in the round's own prose were estimates that the code had
outgrown — "fifteen subcommands, ten aliases" against a real 11 and 17.
Both guards that quoted them now read `create_parser()` and
`TOOL_ALIASES` instead.

> **Corrected in `UX-197`:** this section originally opened "All twelve
> items UX-183..UX-192", which is ten. Round 21 caught it, and the
> placement is the lesson — a miscount in the very paragraph announcing
> that two other counts had been corrected. Hand-counted figures in
> prose are the class; `UX-197` item 5.

The suite stands at **2,389**, the `bst` tier at 43.

