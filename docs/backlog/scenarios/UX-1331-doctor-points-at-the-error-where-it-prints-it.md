# UX-1331: `doctor` says "read the error below" above the error, and warns about suspend inside a container

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_doctor.py::TestTheRemedyPointsTheWayTheReportPrints`, `tests/unit/test_a_capture_that_slept.py::TestDoctorSuggestsIt`

## Motivation

On carbonOS before its prerequisites were installed:

```text
  [FAIL] project-loads: the project does not load (tried test.bst, ...)
           Failed to load source plugin 'git_repo': No module named 'dulwich'
           -> read the error below - `bst show` is what this ran, ...
  [warn] sleep-policy: this machine can suspend while a capture runs (sleep.target is static)
```

The error is printed above the remedy (`tools/bga_doctor.py:528`). The container has no
suspend; `sleep.target is static` is systemd's answer where nothing can suspend it.

## Decomposition

Input classes: a load failure; a host with systemd that can suspend; a container (no systemd as
pid 1, or `/.dockerenv`/`container` env).

## Required Fix

The remedy reads "read the error above". The sleep-policy check reports ok, naming the container,
where the host is a container.

## Out of Scope

Detecting a laptop lid.

## Acceptance Test

A guard asserts the remedy's wording against the order doctor prints in, and the container case.
Reading taken in this container.

## Outcome

**The gap measured.** Reading in this container (pid 1 `process_api`, no systemd):
`check_sleep_policy()` before: `warn` "this machine can suspend ... (sleep.target is static)" is the walk's
reading; the remedy said "read the error below" while `format_text` prints `detail` above the remedy.

**The close measured.** After: `check_sleep_policy()` -> `ok`, "this machine will not suspend (running in a
container: pid 1 is process_api)"; remedy reads "read the error above".
`python3 -m pytest -n 1 -q tests/unit/test_a_capture_that_slept.py tests/unit/test_doctor.py` -> 65 passed, 8 skipped.

**Mutation table.**

| Mutation | Reddened | Count |
|---|---|---|
| remedy back to "below" | `test_a_load_failure_says_the_error_is_above_its_remedy` | 1 failed |
| drop the pid-1 test | `test_the_container_env_var_and_a_non_systemd_pid_1_each_count` | 1 failed |
| drop the `container` env test | same | 1 failed |
| drop `/.dockerenv` | `test_a_container_marker_file_reports_ok_naming_the_container[/.dockerenv]` | 1 failed |

### Deviation from the Required Fix

The verifier held a container false positive on non-systemd init; fixed with the known inits and cgroup, folded. (`3f7b1eb1`)
