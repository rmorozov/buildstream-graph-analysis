# UX-882: a `public:` annotation sets the jobserver auth style, version-controlled

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-879, UX-880 | **Found by:** round 125 Out of Scope + the user ("maybe i can mark some packages by hand for bga to utilize jobserver") | **Serves:** R2 (an element carries its own jobserver policy in the project, not in the operator's command line) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** bounded

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

Read a `public: { bga: { jobserver-auth: fd|fifo|off|flto } }` annotation
off each element and let it set the per-element auth style the same way
UX-879's command-line `--jobserver-auth-override` does — a second, in-tree
*source* for the same four styles, not a new mechanism.

- **Read** via a **separate** `bst show --format` call for
  `%{name}<US>%{public}<RS>` (the RS/US-delimited scheme
  `bst_show_to_graph.py` already uses for `%{public}`), parsed with
  `yaml.safe_load` and `data.get("bga", {}).get("jobserver-auth")` — NOT
  appended to the existing `%{name} %{kind}` line read, whose `line.split()`
  parse breaks on `%{public}`'s multi-line YAML (researcher, round 127).
  Written to a new env `BST_TRACE_ELEMENT_AUTH_MAP` (JSON `{element: style}`)
  beside `BST_TRACE_ELEMENT_KINDS`.
- **Resolve** in `_jobserver_injection`: the command-line
  `--jobserver-auth-override` (BST_TRACE_JOBSERVER_AUTH_MAP) **wins**, then
  the annotation, then `auto` — `override = resolve_auth_override(cmdline,
  elem) or _annotation_style(annotation_map, elem)`, so a run can override
  a committed default and an unmatched element still falls to auto.
- **Not a versioned contract.** The annotation is advisory *input* bga
  reads from a project (like the `kind`/`%{vars}` reads), not a bga-published
  output document — so no `bga.contracts` `/vN` id and no `specification.md`
  Part-32 edit (researcher, round 127: every `/vN` id is on the output
  side; §3.7's rename/remove rule governs published JSON, not an input key).
  Documented in `docs/guides/cli.md` only.

## Decomposition

surfaces: `tools/bst_native_build_tracer.py` (a second `bst show %{public}` read → `BST_TRACE_ELEMENT_AUTH_MAP` json) · `bwrap_shim.py` (`_annotation_style` + the `or`-fallback in `_jobserver_injection`, and read the new env inventory-side) · `docs/guides/cli.md` (§3.10 env + the annotation)
guards: `test_a_public_annotation_sets_the_auth_style.py` (new): an element whose annotation says `off` scrubs where auto would fifo (make 4.4 fixture); a command-line override for the same element beats the annotation; an unmatched element falls to auto; a pure-unit on the `%{public}` YAML → style parse
gap: `keep` (auto-but-never-scrub, for a sub-4.4 element whose owner knows its make is fine) is a new auto-path behaviour, not one of the four override styles — deferred to a follow-up; the extra `bst show` call's cost on a large graph is unmeasured
track: bounded `implementer` on `sonnet`; parallel with UX-881 (shares `bga/cli.py`? no — 882's read is tracer-side; the only shared file is `bwrap_shim.py`, different regions from 881's `_wrapper_mount`, merge-additive)
gate: batch PR (round 127)

Input classes: annotation `off` → scrub on make 4.4 where auto fifos;
annotation `fd`/`fifo`/`flto` → that style; command-line override for the
same element → command-line wins; no annotation, no override → auto
(UX-878, the anchor); malformed/absent `%{public}` → `{}`, treated as no
annotation (never raises).

## Out of Scope

`keep` (the auto-but-no-scrub escape hatch — a follow-up). UX-880's `flto`
mechanism itself (this only adds a second source for the style). The
command-line override (UX-879, shipped). `--wrapper-dir` (UX-881). Any
`specification.md`/`bga.contracts` version bump (advisory input, decided
above).

## Acceptance Test

`tests/unit/`: `build_shim_argv` for an element whose
`BST_TRACE_ELEMENT_AUTH_MAP` says `off` scrubs on a make-4.4 fixture where
auto would rewrite to `fifo:`; a command-line `fd:<that element>` override
beats the annotation (command-line wins); an element in neither map falls
to auto (fifo on 4.4). Plus a pure-unit: the `%{public}` YAML
`bga:\n  jobserver-auth: off` parses to `off`, and a `%{public}` with no
`bga:` key to `None`. Mutation: drop the annotation from the `or` fallback
(annotation never consulted) — the `off`-forced and its precedence
assertions redden.

## Outcome

**Gap measured** (base `f5bd0af`, before this change): `_jobserver_injection`'s
only per-element source was the command-line `BST_TRACE_JOBSERVER_AUTH_MAP`
(`override = resolve_auth_override(os.environ.get(...), ctx["element"])`,
one source) — no project-committed annotation existed.

**Close measured**:

```text
$ python3 -m pytest tests/unit/test_a_public_annotation_sets_the_auth_style.py -q
7 passed in 0.21s
```

`make test-touching` 3048 passed, 62 skipped (only the two expected
`fixing-guide.md` test-file-count failures, the orchestrator's re-derive
at merge); `make lint` exit 0 with the pinned `ruff 0.16.7`.

**Mutation table**:

| mutation | reddened | count |
|---|---|---|
| drop `or _annotation_style(ctx["element"])` from the `_jobserver_injection` resolve | `test_an_off_annotation_scrubs_where_auto_would_fifo` (MAKEFLAGS reappears — annotation never consulted, auto's fifo rewrite runs) | 1 failed, 6 passed (reverted from scratchpad copy, `__pycache__` cleared, 7 passed after) |

**Deviation**: the `%{public}` read is a **separate** RS/US-delimited
`bst show %{name}<US>%{public}<RS>` call, not folded into the existing
`%{name} %{kind}` line read whose `line.split()` breaks on multi-line YAML.
The YAML 1.1 gotcha — unquoted `off` loads as bool `False` — is handled
explicitly (`if style is False: style = "off"`). The annotation is advisory
**input** (like the `kind`/`%{vars}` reads), so no `bga.contracts` `/vN` id
and no `specification.md` Part-32 edit (round-127 researcher). One
authorized `tests/quality_baseline.json` S603 entry (the new
`subprocess.run`, via `dev_baseline.py --write --force --reason UX-882`).
`keep` (auto-but-never-scrub) deferred to a follow-up. Verifier PASS.
