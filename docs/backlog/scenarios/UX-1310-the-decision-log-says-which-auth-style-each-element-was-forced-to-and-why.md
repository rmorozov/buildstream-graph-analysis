# UX-1310: the decision log says which auth style each element was forced to, and by which switch

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** Ruslan, round 168 (2026-10-03): checking a `public: bga: jobserver-auth: off` annotation on his own project, the only witness was grepping `exec_argv` in `--diagnose` output | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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
