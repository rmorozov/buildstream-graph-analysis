# UX-882: a `public:` annotation sets the jobserver auth style, version-controlled

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-879, UX-880 | **Found by:** round 125 Out of Scope + the user ("maybe i can mark some packages by hand for bga to utilize jobserver") | **Serves:** R2 (an element carries its own jobserver policy in the project, not in the operator's command line) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

UX-879/UX-880 set the per-element auth style with a `--jobserver-auth-override`
**command-line** glob map. That is the operator's lever, but it is not
version-controlled: it lives in whoever's invocation, not in the project,
and it re-specifies globs every run. A mixed-make project migrating
element by element wants the policy to travel **with the element** —
committed, reviewed, diffable. BuildStream elements already carry a
`public:` domain for exactly this kind of out-of-band, tool-read metadata.

(Note: an earlier premise that BuildStream reads `public: bst: max-jobs:`
was found wrong — `bst_show_to_graph.py:152-190`, `serialization_points.py`
— BuildStream itself reads `variables: max-jobs`. But bga reading its
**own** `public: bga:` sub-domain is independent of what BuildStream reads;
bga already threads a per-element `kind` map into the sandbox via
`BST_TRACE_ELEMENT_KINDS`, and this rides the same channel.)

## Required Fix

Read a `public: { bga: { jobserver-auth: keep|fifo|off|fd|flto } }`
annotation off each element (via `bst show %{public}` or the `.bst` YAML,
alongside the existing `kind` read), thread it into the sandbox as a
per-element map (a new env beside `BST_TRACE_ELEMENT_KINDS`, or folded
into `BST_TRACE_JOBSERVER_AUTH_MAP`), and resolve it in `_jobserver_injection`
with a defined precedence: an explicit `--jobserver-auth-override` from the
command line **wins** over the annotation (the operator can override the
committed default for one run), the annotation wins over `auto`. `keep`
means "auto, do not scrub even on <4.4" (the escape hatch for an element
whose owner knows its make is fine).

Surfaces: `tools/bst_native_build_tracer.py` (read `public: bga:`,
new env), `bwrap_shim.py` (resolve annotation vs override vs auto),
`docs/guides/cli.md` + `docs/spec/specification.md` §3.12 (the annotation
key — a published contract surface, so a version bump per §3.7 if it
counts as a schema key).

## Decomposition

surfaces: `tools/bst_native_build_tracer.py` (public read + env) · `bwrap_shim.py` (precedence resolve) · `docs/guides/cli.md` · `docs/spec/specification.md` §3.12
guards: `test_a_public_annotation_sets_the_auth_style.py` (new): an element with `public: bga: jobserver-auth: off` scrubs even where auto would fifo; a command-line override for the same element wins; `keep` suppresses the <4.4 scrub
gap: whether the annotation key is a versioned contract (§3.7 bump) or advisory-only — decide at build time; the `public:` read path's cost on a large graph (one extra `bst show` field) unmeasured
track: bounded `implementer`; serial after UX-880 (shares the resolve precedence in `_jobserver_injection`)
gate: a later round (filed this round, not built)

## Out of Scope

UX-880's `flto` mechanism (this is a second *surface* onto the same
styles). The command-line override (UX-879, shipped). `--wrapper-dir`
(UX-881).

## Acceptance Test

`tests/unit/`: `build_shim_argv` for an element whose annotation map says
`off` scrubs on a make-4.4 fixture where auto would rewrite to `fifo:`; a
command-line `fd:<that element>` override beats the annotation; `keep`
leaves auto's fifo rewrite in place but suppresses a <4.4 scrub. Mutation:
ignore the annotation map (annotation never consulted) — the `off`-forced
and `keep`-suppresses-scrub assertions redden.

## Outcome

_(filed round 126, not built — deferred to a later round)_
