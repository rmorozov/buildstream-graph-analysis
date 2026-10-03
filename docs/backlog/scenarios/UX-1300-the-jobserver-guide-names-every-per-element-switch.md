# UX-1300: the jobserver guide names every way to keep one element out of `auto` or force its style

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan's question (2026-10-03): "how can I override jobserver auto for specific buildstream element to fd or off? in which doc we have such switch documented?" | **Serves:** R1, R2, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_the_jobserver_guide_names_every_per_element_switch.py`

## Motivation

Four per-element switches exist; the guide a user reads for the
jobserver names none of them, and the one place that does is a
"reachable only from `--help`" list for a flag no `--help` prints:

```text
$ grep -c -E "auth-override|jobserver-auth:|notparallel" docs/guides/jobserver.md docs/guides/pilot.md
docs/guides/jobserver.md:0
docs/guides/pilot.md:0
$ grep -n "jobserver-auth-override\|jobserver-auth: fd" docs/guides/cli.md | cut -c1-60
1234:- `bga capture run --jobserver-auth-override 'fd:<glob>[
1235:- `public: { bga: { jobserver-auth: fd|fifo|off|flto } }`
$ sed -n 1224p docs/guides/cli.md
### Flags reachable only from `--help`
$ bga capture run --help | grep -c auth-override
0
```

The switches, from the code:

| switch | code |
|---|---|
| `bga capture run --jobserver-auth-override 'style:glob ...'` | `bga/cli.py:3294`, `resolve_auth_override` `tools/native_trace/bwrap_shim.py:537` |
| `public: bga: jobserver-auth:` in the element | `_annotation_style` `bwrap_shim.py:1777`, read by the tracer's one `bst show` (`read_jobserver_bst_show`, `UX-1011`) |
| `notparallel: True` (a composed `-j1`): pinned, nothing injected | `parse_element_max_jobs`/`jobserver_decision` `bwrap_shim.py:273-298` |
| `--jobserver off`: every element | `bga/cli.py` `_translate_capture_jobserver` |

Precedence is the override, then the annotation, then auto
(`bwrap_shim.py:859-861`). `bga snapshot` rejects the override flag
(`error: unrecognized arguments: --jobserver-auth-override`), so a
snapshot user has the annotation only. cli.md:1235 still says the
annotation is read by a separate `bst show`; `UX-1011` folded it into one.

## Required Fix

A section in `docs/guides/jobserver.md` naming the four switches in
precedence order, the four styles and when each is right (`fd` never on
an LTO element; `flto` there), with one example of each; a pointer from
`pilot.md`'s jobserver section and from cli.md's `--jobserver` entry;
cli.md:1235's read corrected. A guard reads the style set from the code
(`_AUTH_OVERRIDE_STYLES`) and the flag name from `bga/cli.py`, and fails
when the guide drops either.

## Out of Scope

Printing the override in `--help` (`UX-1301`), and giving `bga snapshot`
the flag (`UX-1302`): code changes, filed from the same day's docs audit.

## Acceptance Test

`grep -c` above reads non-zero for `jobserver.md`; the new guard is
green and reddens when a style or the flag name leaves the guide. The
reading is taken in this container.

## Outcome

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — the guide for the jobserver named none of the
switches, and the one list that did is titled for a `--help` that
prints none of them.

### The gap, measured

```text
$ grep -c -E "auth-override|jobserver-auth:|notparallel" docs/guides/jobserver.md docs/guides/pilot.md
docs/guides/jobserver.md:0
docs/guides/pilot.md:0
```

Reading the code for the section found two more facts the backlog had
not written: `notparallel` (a pinned `-j1`) is checked before the
override, so it beats both; and `bga-jobserver-env` (`UX-851`) is
recorded but no shim reads it, so the guide names `kind_job_env`'s
`MAKEFLAGS`/`JOBS`/`MAXJOBS` instead (`UX-1304`).

### After

```text
$ grep -c -E "auth-override|jobserver-auth:|notparallel" docs/guides/jobserver.md docs/guides/pilot.md
docs/guides/jobserver.md:5
docs/guides/pilot.md:1
$ python3 -m pytest -q -p no:randomly tests/unit/test_the_jobserver_guide_names_every_per_element_switch.py tests/unit/test_docs_links_and_commands.py
72 passed in 37.73s
```

`jobserver.md` gains "One element, not the whole build": four switches
in the order `_jobserver_injection` reads them, the four styles, and one
example of each surface. `pilot.md` and cli.md's `--jobserver` entry
link it; cli.md:1235's separate `bst show` is now the one `UX-1011` call.
The guard runs the guide's flag example through
`_translate_capture_jobserver_auth_override` and `resolve_auth_override`,
and its YAML through `_public_auth_style`.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | the `flto` row dropped from the guide | 2 of 13 |
| A2 | `_AUTH_OVERRIDE_STYLES` gains `auto` | 2 of 14 |
| A3 | the YAML example's `off` misspelt `of` | 1 of 13 |
| A4 | the flag example's `off:` written `none:` | 1 of 13 |
| A5 | the `notparallel` row dropped | 1 of 13 |
| A6 | pilot.md's link loses its anchor | 1 of 13 |

### Deviation from the Required Fix

The table has four rows in the code's order, `--jobserver off` and
`notparallel` first, rather than the override first: the code checks
the pin before the override (`bwrap_shim.py:815`).
`test_the_documented_invocations_parse.py` called the guide's
`--jobserver-auth-override` no such flag, because it reads argparse and
the flag is consumed before argparse runs; its inventory now reads the
`_translate_capture_*` flags by AST, as it already reads `--schema`.

