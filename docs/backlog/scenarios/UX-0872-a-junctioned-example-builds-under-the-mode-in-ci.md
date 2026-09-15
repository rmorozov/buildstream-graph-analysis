# UX-872: a junctioned example builds under the mode in CI

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-869, UX-871, UX-856 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R4 (the snapshot entry point with the jobserver on runs in CI, on a junction) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

Every jobserver-on CI step runs `bga capture run` or the tracer
directly on a project with no junction; `bga snapshot --jobserver`
(`UX-856`) has never run in CI, and no example has a junction, so the
two defects the user hit on the first day (`UX-869`, `UX-871`) had no
step to fail on.

## Required Fix

`examples/12-junctioned/`: a small project whose elements come through
a local junction (a sub-project inside it holding one cmake element and
a stack), built by the `bst-examples` job with `bga snapshot
--jobserver auto -- bst build all.bst`, asserting the junctioned cmake
element's decision reads `joined` with a kind, not `unknown_kind`, and
the build exits 0; the README carries this box's reading, dated.

## Decomposition

Input classes: a junctioned cmake element, the junction element itself
(never joins), the stack on top; the journey it extends is the user's
`bga snapshot --jobserver auto` on a junctioned project.

## Out of Scope

A remote junction; a second example under fifo-style auth (CI's make
is 4.3 - name the class as CI-only in the README).

## Acceptance Test

`tests/unit/test_the_examples_build.py` gains the step's assertions
(the exit, the joined decision on the junctioned element); mutation:
point the assertion at an unjunctioned element - red. The live reading
from this box pasted in the Outcome.

## Outcome

**Gap measured.** `git show HEAD:.github/workflows/ci.yml | grep -c
'bga snapshot --jobserver'` -> `1`, and that one hit is a comment
(line 1560, "UX-856's `bga snapshot --jobserver` landed the same
round") - the jobserver-on steps all use `bga capture run
--jobserver`, never the user's own `bga snapshot --jobserver`. No
`examples/*` directory named a junction (`ls examples | grep -i
junction` -> nothing) before this change.

**Close measured.** `examples/12-junctioned/` added: a local junction
(`elements/junction.bst`) into `sub/`, a real second BuildStream
project holding one `cmake` element (`core.bst`, one C file) and the
stack that groups it; top-level `all.bst` depends on
`junction.bst:stack.bst`. A new CI step ("Build + capture 12-junctioned
(UX-872)") runs `bga snapshot --jobserver auto -- bst --builders 2
build all.bst` and checks the result through a real committed script,
`examples/12-junctioned/check_jobserver_decision.py` (not an inline
workflow one-liner - `tests/unit/test_the_workflow_does_not_know_the_
payload.py`/`UX-354` refuses a `run:` block that parses this
repository's own JSON and names a key itself).

Real run, this box, 2026-09-15 (fresh HOME/XDG caches, a copy under the
scratchpad, `tests/unit/_bst_env.py`'s sized `XDG_CONFIG_HOME` -
`UX-755`, this box's free disk is small next to its nominal size):

```text
exit=0 elapsed=13.9s
core.bst decision: {'decision': 'joined', 'element': 'core.bst', 'kind': 'cmake', 'max_jobs': 4, 'policy': 'cmake_meson'}
```

`kinds_read.json`'s own diagnostic (`read_element_kinds_for_jobserver`,
called directly - the real file lives in a scratch dir removed when
the capture's own `with capture_scratch(...)` block exits):

```json
{"argv": ["bst", "show", "--format", "%{name} %{kind}", "all.bst"], "count": 7, "junctions": 3, "collisions": 0}
```

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `ci.yml`'s `JUNCTIONED_ELEMENT=core.bst` -> `unjunctioned.bst` | `test_the_ci_step_12_captures_via_bga_snapshot_with_the_jobserver_on` | 1 of 14 in `test_the_examples_build.py` |
| `check_jobserver_decision.py` called with `unjunctioned.bst` against a real `core.bst`-only report (the Acceptance Test's own named mutation) | `test_the_ci_steps_12_decision_check_refuses_an_unjunctioned_element` | 1 (real script, not a synthetic paraphrase) |
| `check_jobserver_decision.py` called against a `kind: unknown_kind` row | `test_the_ci_steps_12_decision_check_refuses_unknown_kind` | 1 |

Both ci.yml mutations were applied to the real file, run, and reverted
from a saved copy (never `git checkout --`).
