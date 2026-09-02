# UX-158: --help is a design-history lecture

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-135/UX-137 (the same concision pass, which stopped at the docs) | **Topic:** cli

## Motivation

The docs corpus was cut 3,128 → 2,203 lines for concision (UX-135..
139) and the `--help` surface — the one place every user looks first —
was never audited. Measured, `bga <cmd> --help`, lines:

```text
compare 143   cache-logs 88   capture-run 82   extract 77
capture 66    bga (top) 66    analyze 60      baseline 59
snapshot 53   sweep 47        correlate 43
```

`bga capture --help` opens with UX-11's five brainstormed options, an
external contribution's proxy design, a risk-reduction spike and a
Deep Experiment — the module docstrings are fed to argparse as
`description`, so the backlog's design history *is* the help text.
A user asking "what do I type" scrolls three screens of provenance
to find the flags. The history is valuable and already lives in the
backlog files and docs; the help is the wrong home.

## Required Fix

Every subcommand's help is: usage, a 3-6 line description of what the
command does and when to reach for it, the flags, and at most one
pointer (`Full background: docs/...`). Module docstrings can keep
their history — pass a short `description=` to argparse instead of
`__doc__` where the two have diverged in purpose. Target: no
`--help` over ~40 lines; the top-level `bga --help` fits one screen
with one line per subcommand.

A guard test measures rendered help (`main(['--help'])` captured, per
subcommand) against the cap, the same way the docs tests pin table
shapes — so the next design saga lands in a file, not in argparse.

## Out of Scope

- The docs (already concise); the module docstrings as *code*
  documentation — they may keep any length, they just stop being the
  help text verbatim.

## Acceptance Test

`bga capture --help`, `bga compare --help` and `bga extract --help`
each render under 40 lines with flags visible on the first screen; the
new guard test fails when any subcommand's help exceeds the cap
(verified by mutation: re-point one `description=` at `__doc__`); no
command loses a flag or its epilogue examples where those are the
short kind (`snapshot`'s two-command loop stays).

---

## What was built

| command | before | after | | command | before | after |
| --- | --- | --- | --- | --- | --- | --- |
| `compare` | 143 | **36** | | `capture` | 66 | **20** |
| `cache-logs` | 88 | **29** | | `analyze` | 60 | **42** |
| `capture run` | 82 | **42** | | `baseline` | 59 | **34** |
| `extract` | 77 | **40** | | `snapshot` | 53 | **29** |
| `bga` (top) | 66 | **45** | | `sweep` | 47 | **31** |

> **Annotated by `UX-165`.** The table above is honest at this item's
> commit and stale at the tip: `capture` is 23 and `snapshot` 33 today,
> grown by flags `UX-148` and `UX-159` landed later in the same range.
> Every command still meets its cap, which is what the guard checks.
>
> `UX-165` also found the cut's real cost. "Flag help cut to its first
> sentence" was applied by deleting continuation *lines*, and **ten**
> strings lost their sentence's back half - the line-count guard could
> not see it, because a truncated string is *shorter*, which is exactly
> what the cap rewards. (`UX-132`/`UX-144`'s annotate-rather-than-rewrite
> convention.)

The biggest single win was not prose. argparse puts a flag's help on a
second line whenever the flag exceeds 24 characters, and a third of these
flags do (`--fail-on-inefficient-additions` is 31); widening that column
alone took `compare` from 49 to 36. The rest: short `description=`
constants for the five tools that passed `__doc__`, flag help cut to its
first sentence, and one line per entry in the alias block.

A guard test renders every subcommand's help and caps it, so the next
design saga lands in a file rather than in argparse.

### Deviation, recorded

The acceptance asks for "~40 lines". `compare` (36), `capture` (20) and
`extract` (40) meet it; `analyze` and `capture run` land at 42 and the top
level at 45. Those are already one line per flag or per command - going
further would mean deleting flags, not prose - so the cap is 45 and the
number is stated rather than the target quietly restated.

### One requirement broken and restored

Dropping the module name from the alias block cost a documented property:
these tools stay independently runnable, and a reader who wants to script
one needs to know where it lives.
`test_help_names_the_underlying_module` caught it; the module is back, on
the same line.
