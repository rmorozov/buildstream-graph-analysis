# UX-883: a preflight warns when an LTO element meets a sub-4.4 make

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-878 | **Found by:** round 126 (the clean path off the scrub is make 4.4 + fifo, but nothing tells the operator that the element they are staring at is the one that would benefit) | **Serves:** R2 (an operator migrating make version by version is told which elements the migration unblocks) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** bounded

## Motivation

UX-878 scrubs a compiler-driving kind on a sandbox make <4.4 (safe against
the ICE) and UX-879/UX-880 give per-element levers, but the operator has
to *already know* which elements are the LTO-on-old-make ones to reach for
a lever. The clean, permanent answer — move that element's sandbox to GNU
Make ≥4.4 so UX-878's fd→fifo rewrite just works, no scrub, no shim — is
invisible: nothing in the capture output names the element that the
migration would unblock. The operator learns it only by hitting the ICE
or by reading round docs.

## Required Fix

At `bga capture run`, when the jobserver is active, emit a one-line
**preflight warning** per element that is on a sub-4.4 sandbox make *and*
whose kind is compiler-driving (a `_COMPILER_SAFE_POLICIES` kind), naming
the element and the remedy: "scrubbed to recipe `-jN` (make <4.4); move
this element to make ≥4.4 for fifo pool-fill, or force `fd`/`flto`
(UX-879/880)". The probe result already exists per element
(`_make_probe_cache_path`, `bwrap_shim.py`); the warning reads it, it does
not re-probe. Quiet by default noise-wise: one line per affected element,
de-duplicated, suppressible with an existing verbosity/quiet flag.

Surfaces: `bga/cli.py` (capture run — collect the per-element probe
results and print the warning) or `tools/bst_native_build_tracer.py` (if
the probe results surface there); `docs/guides/cli.md` (the warning's
text). No new contract key.

## Decomposition

surfaces: `bga/cli.py` or `tools/bst_native_build_tracer.py` (the warning emit) · `docs/guides/cli.md`
guards: `test_a_preflight_warns_on_lto_meeting_old_make.py` (new): a capture whose element probes <4.4 on a compiler-driving kind prints the warning naming the element and remedy; an element on make ≥4.4, or a non-compiler kind, prints nothing
gap: the warning is advisory — it does not change behaviour (the scrub still happens); "make it an error under --strict" is a later filing if wanted
track: bounded `implementer` on `sonnet`; parallel with UX-880 (disjoint surface — 880 is the override/shim path, 883 is the warning emit); shares `bga/cli.py` with 880 only at the capture-run entry (merge-additive)
gate: batch PR (round 126)

Input classes: element on make <4.4 + compiler-driving kind → warning;
element on make ≥4.4 → no warning; non-compiler kind on make <4.4 → no
warning; two elements same kind+version → one de-duplicated line each (or
grouped). Boundary: exactly 4.4 → no warning (fifo works).

## Out of Scope

Making it a hard error (a `--strict` follow-up). The scrub behaviour
itself (UX-878 stays). The make/autotools LTO gap (UX-884).

## Acceptance Test

`tests/unit/` new file: through the capture-run path with a fake sandbox
make reporting 4.3 on a `cmake` element, stderr (or the warning channel)
contains one line naming the element and the make-4.4 remedy; with make
4.4 reported, no such line; with a non-compiler kind on 4.3, no line.
Mutation: drop the version comparison (warn always) — the make-4.4 and
non-compiler-kind "no warning" assertions redden.

## Outcome

_(filled at close)_
