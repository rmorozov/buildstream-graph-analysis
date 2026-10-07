# UX-1310: the decision log says which auth style each element was forced to, and by which switch

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan, round 168 (2026-10-03): checking a `public: bga: jobserver-auth: off` annotation on his own project, the only witness was grepping `exec_argv` in `--diagnose` output | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_decision_log_names_the_forced_auth_style.py`

## Motivation

`jobserver_decisions` records `{element, max_jobs, decision, kind,
policy, pid}` per sandbox (`record_jobserver_decision`,
`tools/native_trace/bwrap_shim.py:1205-1250`) and nothing about the
per-element override: whether `--jobserver-auth-override` or a
`public: bga: jobserver-auth:` annotation matched, which style it
forced, or that an annotation was present and not read. A user who
sets one cannot see it take effect except by reading every sandbox's
argv with `--diagnose`, and an annotation BuildStream never loaded
(misplaced `public:`, a junction override) is silent.

```text
$ grep -n '"override\|"auth_style\|"source"' tools/native_trace/bwrap_shim.py | wc -l
0
```

## Decomposition

Input classes: a command-line override match; an annotation match; both
(the command line wins); neither (auto); a pinned element (nothing
read); an override glob that matches no element in the build; an
annotation style outside the four. Journey: `bga capture run
--jobserver auto --jobserver-auth-override 'off:giant.bst' ...`, then
the report's `jobserver_decisions` and the capture's printed summary.

## Decision

```text
Route:     record_jobserver_decision gains forced_style/forced_by from a new pure _forced_auth(element, policy_style, kind) that re-reads the same override sources _auth_style_for uses; the tracer's capture summary prints one line per forced element plus one warning per unmatched override glob and per annotation entry naming an unrun element, read from the decision rows it already joins.
Rejected:  threading the forcing source out of _auth_style_for's return value — six call sites want only the style; a second pure lookup keeps them untouched.
Rejected:  printing the warnings from the shim — one shim per sandbox cannot know "no element in the build matched"; only the tracer sees every decision row.
Files:     tools/native_trace/bwrap_shim.py (record_jobserver_decision ~1205-1250, new _forced_auth next to _auth_style_for); tools/bst_native_build_tracer.py (summary print beside the decisions read); bga/schemas.py (jobserver_decisions row: two optional keys); docs/guides/jobserver.md ("check it took effect" paragraph); tests/unit/test_the_decision_log_names_the_forced_auth_style.py (new)
Guard:     tests/unit/test_the_decision_log_names_the_forced_auth_style.py — fake-bwrap harness, one case per input class: command-line match → command_line; annotation → annotation; both → command_line; neither → keys absent; pinned → keys absent; unmatched glob → warning printed exactly once; out-of-four annotation style → not forced, warned.
Mutation:  _forced_auth returns annotation when both match → "both" case reddens; drop de-dup on the unmatched-glob warning → "printed once" reddens.
Class:     product
Split:     one track; parallel with UX-1314 (which only reads the row's existing `pid` key).
Question:  none — junctioned `junction.bst:x.bst` annotation keys are normalised to the short name before the never-ran comparison.
```

## Required Fix

Each decision line carries `forced_style` and `forced_by`
(`command_line` / `annotation` / absent); the capture prints one line
per forced element, and one warning per override glob that matched no
element and per annotation map entry naming an element the build never
ran. The jobserver guide's "check it took effect" paragraph names it.

## Out of Scope

Reading `%{public}` differently from BuildStream.

## Acceptance Test

A shim-level test with the fake-bwrap harness reads both fields for
each input class; the unmatched-glob warning is printed once. Reading
taken in this container.

## Outcome

**Gap measured** (base `d0e434e2`): the shim writes neither key, and
the guard cannot import a summary that does not exist.

```text
$ git show d0e434e2:tools/native_trace/bwrap_shim.py | grep -c '"forced_style"\|"forced_by"'
0
$ pytest -q tests/unit/test_the_decision_log_names_the_forced_auth_style.py   # base shim + tracer
ERROR tests/unit/test_the_decision_log_names_the_forced_auth_style.py   (ImportError: forced_auth_summary)
```

**Close measured** (this container, x86_64): one real shim process per
input class exec'ing a fake `bwrap`, its decision row, then
`forced_auth_summary` over that row (map `off:giant.bst;fd:core.*`).

```text
command-line  {'element': 'core.bst', 'decision': 'joined', 'forced_style': 'fd', 'forced_by': 'command_line'}
              | Jobserver auth: core.bst forced to fd by --jobserver-auth-override
              | Warning: --jobserver-auth-override glob 'giant.bst' matched no element in this build
annotation    {'element': 'core.bst', 'decision': 'joined', 'forced_style': 'fifo', 'forced_by': 'annotation'}
              | Jobserver auth: core.bst forced to fifo by its public: annotation
              | Warning: gone.bst's jobserver-auth annotation names an element this build never ran
both          {'element': 'core.bst', 'decision': 'joined', 'forced_style': 'fd', 'forced_by': 'command_line'}
              | Jobserver auth: core.bst forced to fd by --jobserver-auth-override
              | Warning: --jobserver-auth-override glob 'giant.bst' matched no element in this build
neither       {'element': 'core.bst', 'decision': 'joined'}
pinned        {'element': 'core.bst', 'decision': 'pinned'}
              | Warning: --jobserver-auth-override glob 'giant.bst' matched no element in this build
out-of-four   {'element': 'core.bst', 'decision': 'joined'}
              | Warning: core.bst annotates jobserver-auth: keep, not one of fd, fifo, flto, off; ignored
$ pytest -q tests/unit/test_the_decision_log_names_the_forced_auth_style.py
13 passed in 3.64s
```

**Mutation table** (each reverted from a scratch copy; `cmp` identical, 13 passed after):

| mutation | reddened | run |
|---|---|---|
| `_forced_auth_source` reads the annotation first | `[both]`, `[annotation]`, junctioned case | 3 failed, 10 passed |
| `_auth_map_globs` drops its de-dup | `test_an_unmatched_glob_is_warned_exactly_once` | 1 failed, 12 passed |
| annotation keys compared unshortened | `test_a_junctioned_annotation_that_ran_by_its_short_name_is_not_warned` | 1 failed, 12 passed |
| pinned row records the keys | `test_a_pinned_element_names_nothing` | 1 failed, 12 passed |
| `BST_TRACE_NO_INJECT` row records the keys | `test_a_no_inject_sandbox_names_nothing` | 1 failed, 12 passed |
| show parse filters to the four again | `test_the_show_parse_keeps_an_out_of_four_style_for_the_warning` | 1 failed, 12 passed |
