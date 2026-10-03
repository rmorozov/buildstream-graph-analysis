# UX-1304: `bga-jobserver-env` is validated and recorded, and no sandbox ever reads it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** tests/unit/test_a_declared_jobserver_env_joins_an_unknown_kind.py

## Motivation

`UX-851` filed `variables: {bga-jobserver-env: "NAME=-j"}` so an
unknown kind could join the jobserver; `tools/bst_extract_run.py:424`
reads and validates it into `run_context.jobserver_env`, and nothing in
the shim or tracer consumes it - `kind_job_env`
(`tools/native_trace/bwrap_shim.py:350`) joins an unknown kind only on a
composed `MAKEFLAGS`/`JOBS`/`MAXJOBS`.

```text
$ grep -rn jobserver_env --include=*.py bga tools | grep -v tests | cut -d: -f1 | sort -u
bga/disclosure.py
tools/bst_extract_run.py
```

## Decomposition

Input classes: an unknown-kind element with a declared `bga-jobserver-env`; one without; a shipped kind with a declaration; a malformed entry (already refused at read). Journey: `bga capture run --jobserver auto` on a custom-plugin project, then `jobserver_decisions`.

## Required Fix

Either the shim sets the declared `NAME` for an unknown kind, or the
declaration is documented as a record only; no guide names it today.

**Decision:** the shim sets it. The tracer re-serializes the declaration
into `BST_TRACE_JOBSERVER_ENV` (`_declared_jobserver_env`, beside
`BST_TRACE_ELEMENT_KINDS`); `kind_job_env`, for a kind outside the table
with no `MAKEFLAGS -jN`/`JOBS`/`MAXJOBS`, sets each `NAME` to `PREFIX` +
`BST_TRACE_PROJECT_MAX_JOBS` beside the `MAKEFLAGS` auth, policy
`declared_env` (in both auth-narrowing sets, as `jobs_env` is). `UX-851`
never specified the value; the width is the project's `max-jobs`. A
`NAME` BuildStream composed itself is the element's own width
(`parse_element_max_jobs` reads it with `PREFIX` stripped, so `-j1` is
`pinned`); any declared `NAME` composed - parseable or not - makes
`recipe_promise` read `DECLARED`, and `kind_job_env` injects nothing for
it (`unknown_kind`), so no second `NAME` or auth widens a capped or
serial element. A composed `MAKEFLAGS` keeps its contents with the auth
appended (`_respect_composed`). The width comes
from the build target's `%{max-jobs}` (`read_project_max_jobs`), which a
`notparallel` target reports as `1` (`tools/bst_show_to_graph.py:165`);
so a width of `1` applies nothing - a project really at `1` has nothing
to share, and skipping it is the behaviour before this row.

## Out of Scope

The per-kind table itself.

## Acceptance Test

A capture of an unknown-kind element under a declared
`bga-jobserver-env` reads `joined` in `jobserver_decisions`, or the doc
says it never will. Reading taken in this container.

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — on `9dd99dc0` no shim or tracer line reads the
declaration, and an unknown kind under it gets nothing.

### The gap, measured

```text
$ BST_TRACE_JOBSERVER_ENV=MYJOBS=-j BST_TRACE_PROJECT_MAX_JOBS=4 python3 -c \
  "import base_shim as b; print(b.kind_job_env('custom','--jobserver-auth=fifo:/j'))"   # git show 9dd99dc0:tools/native_trace/bwrap_shim.py
([], [], 'unknown_kind')
$ git grep -c "jobserver_env\|JOBSERVER_ENV" 9dd99dc0 -- tools/native_trace/ tools/bst_native_build_tracer.py
(no output, exit 1)
```

### After

```text
$ BST_TRACE_JOBSERVER_ENV=MYJOBS=-j BST_TRACE_PROJECT_MAX_JOBS=4 python3 -c \
  "from tools.native_trace import bwrap_shim as b; print(b.kind_job_env('custom','--jobserver-auth=fifo:/j'))"
([('MYJOBS', '-j4'), ('MAKEFLAGS', '--jobserver-auth=fifo:/j')], [], 'declared_env')
$ BST_TRACE_JOBSERVER_ENV=MYJOBS=-j python3 -c "...jobserver_decision(parse_element_max_jobs(
  ['--dir','x','--setenv','MYJOBS','-j1']),4); _respect_composed([('MYJOBS','-j4'),('MAKEFLAGS',auth)],
  ['--setenv','MYJOBS','-j2','--setenv','MAKEFLAGS','-s'])"
pinned
[('MAKEFLAGS', '-s --jobserver-auth=fifo:/j')]
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly tests/unit/test_a_declared_jobserver_env_joins_an_unknown_kind.py
16 passed in 0.58s
```

The decision log for that sandbox reads `decision: joined`, `policy:
declared_env` (`test_the_decision_log_reads_joined_and_declared_env`,
through `_resolve_kind_and_probe` and `record_jobserver_decision`); the
sandbox argv carries `--setenv MYJOBS -j4` beside a `fifo:` auth under a
fake make 4.4. Not taken: a real `bst` capture of a custom-plugin
project - no such fixture exists here. Files naming the shim, the guide
or the register, plus the guide/docs/terse/snapshot files: `2254 passed, 8 skipped, 18 deselected in 97.88s`.
The verifier's first pass (on `bb26b8e3`) found a composed `MYJOBS -j1`
widened to `-j4`, a composed `-j2` overwritten, and a composed
`MAKEFLAGS -s` dropped; A7-A9 are those three, now guarded. Its
second pass (on `8962e970`) found a composed `MYJOBS -j2` still let
`OTHER --jobs=4` through, and `MYJOBS --jobs=1` under prefix `-j` read
`joined` and widened; A8/A12 guard both.

### Mutations verified red and reverted (12)

| # | mutation | reddened |
|---|---|---|
| A1 | `kind_job_env`'s `if declared:` -> `if False:` (the defect) | kind-level, decision log, argv x2, make 4.3 - 5 failed, 11 passed |
| A2 | `PREFIX + width` -> `PREFIX` alone | kind-level, argv - 2 failed |
| A3 | `width is None` no longer refuses | `test_an_unknown_project_width_leaves_the_declaration_unapplied` - 1 failed |
| A4 | tracer never sets `BST_TRACE_JOBSERVER_ENV` | `test_a_capture_under_the_mode_hands_the_declaration_to_the_shim` - 1 failed |
| A5 | tracer's mode-off branch keeps a stale one | `test_a_capture_with_the_mode_off_hands_it_nothing` - 1 failed |
| A6 | `declared_env` out of `_COMPILER_SAFE_POLICIES` | two argv cases - 2 failed |
| A7 | `parse_element_max_jobs` never reads a composed `NAME` | `test_a_composed_name_of_one_pins_the_element` - 1 failed |
| A8 | `recipe_promise` no longer reads `DECLARED` | `..._keeps_its_own_width_and_blocks_every_other`, `..._off_its_prefix_injects_nothing` - 2 failed |
| A9 | a composed `MAKEFLAGS` replaced, not appended to | `test_a_composed_makeflags_keeps_its_contents` - 1 failed |
| A10 | `declared_env` out of `_MAKE_CONSUMER_POLICIES` | `test_a_sandbox_make_below_4_4_gets_the_fd_style` - 1 failed |
| A11 | a project width of `1` applied | `test_a_project_width_of_one_leaves_the_declaration_unapplied` - 1 failed |
| A12 | `kind_job_env`'s `DECLARED` row dropped (falls to `jobs_env`) | the same two - 2 failed |

Reverted from the scratch copy: `16 passed`. No guard failed to discriminate.

### Deviation from the Required Fix

None - the shim path; the value (`PREFIX` + project `max-jobs`) is the Decision's, `UX-851` named none.
