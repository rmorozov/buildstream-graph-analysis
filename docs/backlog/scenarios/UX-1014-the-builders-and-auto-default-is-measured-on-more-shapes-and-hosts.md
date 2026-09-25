# UX-1014: the "safe cap plus auto" default is measured on more shapes and hosts before it is anyone's default

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1005 | **Found by:** Ruslan on the Graviton thread (2026-09-25): "we found sane default solution and further we need more experiments, scenarios and data" | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

One graph on one host carries the default today. `13-mixed-graph` on 16
Cortex-A72 cores, 3 repeats each (runs 36163582462, 36153575373):

```text
4 builders off 143.6s   8 off 143.6s   8 + auto 118.3s
32 off ~206s            32 + auto ~182s   32 + auto + admission ~205s
```

`10-jobserver` (already fills the cores) reads auto within ~1s of off
after UX-1011; `11-serial-giant` at max-jobs 3 reads -57%.

## Decomposition

surfaces: new `examples/` shapes, `graviton_arms.sh` legs, the probe workflow
guards: each shape's reading is pasted with its run id; the default holds or is filed against
gap: which shapes break it - two critical chains; a giant that is memory-bound; many medium elements; a host whose knee sits below its cores
track: a sequence of measured legs, one row each as they land

## Required Fix

Readings for at least: two giants on one host; a chain of wide
elements; a memory-bound giant (PSI withdraw); an x86 16-core host; a
real project (freedesktop-sdk or LLVM). Each either confirms the
default or names the shape where it loses.

## Out of Scope

The one ranked queue (admission) - UX-1005 track C's own follow-up.

## Acceptance Test

A table in `docs/guides/real-project.md` of shape x host x arm, every
cell a pasted wall with its run id.

## Outcome

Not started.
