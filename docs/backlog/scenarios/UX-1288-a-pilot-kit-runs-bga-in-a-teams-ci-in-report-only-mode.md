# UX-1288: a pilot kit runs bga in a team's CI, report-only, from one script

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1285, UX-1286, UX-1287 | **Found by:** the owner's choice on 2026-10-02 after the state audit ("Pilot kit"): 1 of 351 rows since 2026-09-20 came from a running deployment | **Serves:** R4, R5, R8 | **Topic:** docs | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Out of Scope

GitLab and other CI wrappers until the owner names the system; the
jobserver (off throughout the pilot); publishing a wheel to PyPI.

## Acceptance Test

`bash -n` and shellcheck clean; every `bga` command and flag the script
and the guide name exists; a dry run of `capture` then `report` on two
committed fixture bundles plus a candidate prints a ci-comment and
exits 0 even when the verdict is slower.

## Outcome
