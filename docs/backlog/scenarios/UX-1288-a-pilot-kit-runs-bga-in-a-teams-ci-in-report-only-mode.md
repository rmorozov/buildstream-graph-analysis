# UX-1288: a pilot kit runs bga in a team's CI, report-only, from one script

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1285, UX-1286, UX-1287 | **Found by:** the owner's choice on 2026-10-02 after the state audit ("Pilot kit"): 1 of 351 rows since 2026-09-20 came from a running deployment | **Serves:** R4, R5, R8 | **Topic:** docs | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_pilot_kit_runs_report_only.py`

## Motivation

Every default the rollout groups depend on is reasoned, not measured:
the band window of 10 (UX-899), the overhead on one shape (UX-895),
the pool size ("uncalibrated", UX-1005). Only a pilot on a real
pipeline measures them, and today a team has to assemble one from
`ci-comment.md`, `cli.md` and UX-900's Outcome. The pilot must never
block a merge until the gate's false-alarm rate is known on that
team's own population.

## Decomposition

Input classes: nightly build (always captured); review build (captured
on a sample); bare-metal agent; container agent (the memory gate,
UX-1282, so the jobserver stays off); no `cc` on the agent (doctor
fails the setup step, not the build). Journey: a CI engineer copies
one script and one workflow, sets three variables, and reads a
comment on the next review build.

## Required Fix

A shell script, `examples/ci/bga-pilot.sh`, CI-agnostic, with three
subcommands: `setup` (pinned install by commit, `bga doctor`),
`capture` (the build under `bga capture run`, class declared with
`--build-type`/`--variant`, bundle written into a kept directory), and
`report` (`compare --band-from-class --bundles`, `--format ci-comment`,
never failing the job). A GitHub Actions workflow wraps it. A guide,
`docs/guides/pilot.md`, says what each step costs, what the pilot
measures in two weeks, and the switch from report-only to gating.

Every switch a pilot may set is a variable at the top of the workflow,
with its default, and the guide carries one table of them: jobserver
mode (`off` by default, how to turn it on, why containers keep it off
until UX-1282), `BGA_ADMISSION`, `--trace-opens` and the spine (their
measured cost), the review sample rate, build type and variant. A
pilot never needs a task file or `cli.md`'s environment table to find
or disable one (the owner, 2026-10-02: pilots "will suffer" if the
jobserver options are buried in task files).

## Out of Scope

GitLab and other CI wrappers until the owner names the system; the
jobserver (off throughout the pilot); publishing a wheel to PyPI.

## Acceptance Test

`bash -n` and shellcheck clean; every `bga` command and flag the script
and the guide name exists; a dry run of `capture` then `report` on two
committed fixture bundles plus a candidate prints a ci-comment and
exits 0 even when the verdict is slower. A guard reads the
guide's switch table against the script's variables, both ways.

## Outcome (round 167, 2026-10-02) — 🟢 Done

**Premise:** held — no kit existed, and no guide said how to turn the
jobserver off for a pilot; the one `--jobserver off` line was a
`bga snapshot` baseline in `cli.md`.

### The gap, measured

```text
$ git ls-tree --name-only 95f41384b examples/ci docs/guides/pilot.md
(nothing)
$ git grep -n -e "--jobserver off" 95f41384b -- docs/guides
docs/guides/cli.md:197:bga snapshot --jobserver off -- bst build all.bst    # the baseline
docs/guides/cli.md:912:| `BST_TRACE_ADMISSION_POOL` | ... (`--jobserver off` leaves it unread ...
```

### After

```text
$ shellcheck examples/ci/bga-pilot.sh; echo rc=$?      # shellcheck 0.11.0
rc=0
$ python3 -m pytest -q tests/unit/test_a_pilot_kit_runs_report_only.py -rs
SKIPPED [1] ...:139: pending UX-1286: bga compare has no ['--bundles'] yet
SKIPPED [1] ...:298: pending UX-1286: bga compare has no --bundles yet
SKIPPED [1] ...:314: pending UX-1286: bga compare has no --bundles yet
SKIPPED [1] ...:323: pending UX-1286: bga compare has no --bundles yet
11 passed, 4 skipped in 6.97s
```

16 switches, one table in `docs/guides/pilot.md`, the same 16 names and
defaults in the script's switch block and the workflow's `env:`;
`PILOT_JOBSERVER` is `off` in all three. The report half (two kept
bundles + a slower candidate -> ci-comment, exit 0; `PILOT_ENFORCE=on`
-> 4; five kept -> band) skips until `bga compare --bundles` exists.
Run here with a shim answering `--bundles` as exit 8: the kit fell back
to the 1% rule, printed `**REGRESSED** — wall-clock 100.0s → 130.0s`,
exited 0, and 4 with `PILOT_ENFORCE=on`.

### Mutations verified red and reverted (12)

| # | mutation | reddened (`-k` / whole file) |
|---|---|---|
| A1 | guide row `PILOT_CROSS_HOST` renamed | guide-and-script names, 1 / 1 |
| A2 | `PILOT_ENFORCE` dropped from the workflow `env:` | workflow switches, 1 / 1 |
| A3 | workflow `PILOT_REVIEW_SAMPLE` 25 -> 50 | defaults agree, 1 / 1 |
| A4 | jobserver default `auto` in all three files | jobserver off, 1 / 2 (+ capture argv) |
| A5 | script `bga doctor` -> `bga doktor` | real subcommands, 1 / 1 |
| A6 | guide `--jobserver` -> `--jobservers` | guide flags exist, 1 / 1 |
| A7 | stray `fi` after `main` | bash -n, 1 / 5 (every run of the script) |
| A8 | `rm -f "${all[$i]}"` unquoted | shellcheck, 1 / 1 |
| A9 | sha refusal `exit 2` -> `exit 0` | setup refuses, 1 / 1 |
| A10 | capture passes `--jobserver auto` | bundle kept, jobserver off, 1 / 1 |
| A11 | sample test `-ge` -> `-lt` | unsampled build, 1 / 3 (capture never runs) |
| A12 | `--host-samples` -> `--host-sample` | capture flags exist, 1 / 1 |

All 12 reverted from copies; the file read 11 passed, 4 skipped after.
Flags are matched whole: `--host-sample` is a substring of the real
flag and argparse accepts the prefix, so a substring test could not see A12.

### On the merged tree, with UX-1286's real `--bundles` (integrator)

The pending skip and its `KNOWN_SKIP_REASONS` entry are gone; the kit's
assumed interface held (principals excluded by stamp: two kept + the
candidate read `hold other 1 run`). File: 15 passed, 0 skipped.

| # | mutation | reddened (`-k`) |
|---|---|---|
| R1 | kit: band refusal `-eq 8` -> `-eq 9` (no fallback comment) | slower candidate comments, 1 |
| R2 | kit: enforce `-eq 4` -> `-eq 40` | enforcing re-applies, 1 |
| R3 | `bga/cli.py`: `bundle.load_tree(...)` -> `pass` | five kept judge the band, 1 |

### Deviation from the Required Fix

Fixture bundles are exported at test time from the golden fixture, not committed; the report half ran once UX-1286 merged.
The shellcheck skip reason stays in `tests/conftest.py` (the UX-1286 one left at merge); the selector's max ceiling 194 -> 195 (`bga/cli.py`, this guard).
