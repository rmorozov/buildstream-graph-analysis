# UX-939: the exercised line names an environment nothing can read, so a version bump in CI reds every branch with no way to clear it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-571 | **Blocks:** — | **Found by:** round 136 — CI's BuildStream moved to 2.8.1 and `bst-tests` went red on `#264`, on `main` and on every open branch, and no session could produce the second reading the line asks for | **Serves:** every branch whose CI runs the bst tier, and the next round that meets a red nobody can measure away | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`docs/spec/ingestion-pipeline.md` carries the same line twice, once
under each `## Empirically confirmed facts` heading:

```text
**Last exercised on `bst` 2.8.0, 2.7.0, 2026-09-03.** The tier runs in two
environments with two binaries - CI's runner and the development
container - so the line names both.
```

`UX-571`'s guard reads the binary and asserts it is in that set. On
2026-09-22 CI's binary became 2.8.1:

```text
tests/unit/test_the_ingestion_facts_name_the_bst_they_ran_on.py:86
  the document says it was last exercised on bst 2.8.0, 2.7.0; this
  binary reports 2.8.1. Re-run the bst tier here and add the version.
  1 failed, 50 passed, 9379 deselected in 122.83s
```

Every other bst-marked guard in that run passed on 2.8.1, so the tier
is healthy and only the line is stale. The obvious repair is to write
2.8.1 into the set. **It cannot be done honestly, and that is the
finding.**

The line names one version per *environment*, which is round 83's own
correction to `UX-571`. CI's is readable: the tier runs there and the
binary reports itself. The other one is not readable, because it is not
one environment:

```text
$ which bst bwrap buildstream          # this session's container
                                       # (no output)
$ python3 -c "import buildstream"
ModuleNotFoundError: No module named 'buildstream'
$ pip show buildstream
WARNING: Package(s) not found: buildstream
```

Another session's container, measured the same way, has neither `bst`
nor `bwrap`, so even an installed one could not sandbox. Session
containers are provisioned per session; there is no standing
"development container" whose version could be read. The `2.8.0`
already in the line came from a session that `pip install`ed
BuildStream in-session — a property of who provisioned that container
on that day, not of an environment this repository has.

So this is not a stale figure waiting to be refreshed. The `2.8.0`
entry **never named an environment**: it named one session's scratch
install, on one day, in a container that no longer exists. The line
claims two environments have exercised these facts, and one of them has
no referent — which is why no amount of measuring clears it.

So the guard asks for a reading nobody can take. A session that happens
to have `bst` would be a **third** environment, and writing its version
in would be a guessed version wearing a measurement's clothes. And the
red is invisible locally: only one test in that file is
`@pytest.mark.bst`, so every session's `make test` skips it and stays
green while CI reds.

**The repository already has the shape that works.** Its durable
version claims are about what a version *publishes*, not about what a
machine has installed:

```text
bga/artifact_weight.py:5          BuildStream 2.8.0 publishes no such number
bga/cache_capacity.py:7           the cheapest exact source BuildStream 2.8.0 has
bga/schemas.py:2928               BuildStream 2.8.0 has no artifact size
tests/unit/test_an_artifact_has_a_weight.py:4   2.8.0 publishes no per-element figure
```

Those survive a runner image change. "The version the development
container has" does not, and a claim that needs re-reading whenever
someone provisions a container is a claim the repository cannot keep.

## Required Fix

Decide what the line is a claim *about*, and say which, with the cost:

- **The tier's own environment.** The line names one version, read
  where the tier ran, and the guard asserts against the binary in the
  process running it. A session with no `bst` skips, as it already
  does; CI's bump is then a one-line consequence of a real reading.
  Cost: the line no longer records that two binaries have seen these
  facts.
- **What the version publishes.** The line names the versions whose
  *output* the facts were derived from, as the prose above does, and
  the guard stops reading `bst --version` at all. Cost: nothing then
  catches a runner whose binary has moved past what was confirmed.

The 2.8.1 bump is a consequence of whichever is chosen, not the fix.
Until then the honest record is that CI's runner reports 2.8.1 and the
second row is unstated because no environment can witness it.

## Out of Scope

Re-running the bst tier to earn a date; that is what this row decides
the shape of. `UX-571`'s other corrections, which stand.

## Acceptance Test

A version bump on the runner is cleared by a reading taken in the
environment the bump happened in, with no session needing a binary it
does not have, and a mutation that points the guard at a version no
binary in the run reports reddens it. The two `## Empirically confirmed
facts` headings still have to agree, which `UX-571`'s other clause
already asserts.

## Outcome
