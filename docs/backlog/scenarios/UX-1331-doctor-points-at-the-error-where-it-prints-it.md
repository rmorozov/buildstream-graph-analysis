# UX-1331: `doctor` says "read the error below" above the error, and warns about suspend inside a container

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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
