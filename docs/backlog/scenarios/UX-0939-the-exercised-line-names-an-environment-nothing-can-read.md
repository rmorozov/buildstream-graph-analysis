# UX-939: the exercised line names an environment nothing can read, so a version bump in CI reds every branch with no way to clear it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-571 | **Blocks:** — | **Found by:** round 136 — CI's BuildStream moved to 2.8.1 and `bst-tests` went red on `#264`, on `main` and on every open branch, and no session could produce the second reading the line asks for | **Serves:** every branch whose CI runs the bst tier, and the next round that meets a red nobody can measure away | **Topic:** guards | **Area:** tools | **Shape:** judgement

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

**The gap.** CI's BuildStream moved to 2.8.1 on 2026-09-22 and
`bst-tests` went red on every branch. The cause was a floor, not a
version: `pyproject.toml`'s `all` and `bst` extras both declared
`buildstream>=2.0`, and CI's bst jobs install through
`pip install -e ".[dev,bst]"`, so the runner took whatever was newest
that day. Two other sites pinned *behind* it - `ci.yml`'s real-project
venv and `real-project-capture.yml` both installed
`BuildStream==2.7.0` - so the repository ran two versions and
asserted about a third.

**The close.** One pin, read from one place:

```text
.github/workflows/ci.yml    env: BST_VERSION "2.8.1"
                                 BST_PLUGINS_VERSION "2.8.0"
```

Two keys because they do not track: PyPI's newest `buildstream` is
2.8.1 and its newest `buildstream-plugins` is 2.8.0. Every install site
in `ci.yml` now uses them, `real-project-capture.yml` pins the same
pair literally, and both extras declare `buildstream>=2.8.1`. The
exercised line carries **one** version, dated today, because the second
entry was the finding: it named a session's scratch install and no
container could witness it.

The runner's half needed no binary of ours, because the re-run
`UX-571`'s own message asks for has already happened - this branch's
run 35764660641, job 106881230092 on `1119f4c1`:

```text
AssertionError: the document says it was last exercised on bst
2.8.0, 2.7.0; this binary reports 2.8.1.
1 failed, 50 passed, 9379 deselected in 122.83s
```

So 50 of the 51 bst-gated tests pass on 2.8.1 and the one failure is
the line itself. The date above is that run's.

**The new guard**, `tests/unit/test_the_pinned_bst_is_the_documented_one.py`,
asks the one question that needs no binary - does the pin say what the
document says - so a session without `bst` catches the drift `UX-571`'s
guard can only catch in CI.

| # | mutation | reddened |
|---|---|---|
| M1 | `BST_VERSION` moved to 2.8.0 | the pin/document clause |
| M2 | one exercised line moved to 2.8.0 | the same clause, on the set |
| M3 | one install returned to a bare `pip install buildstream` | the floor clause |
| M4 | `BST_VERSION` deleted | two clauses |
| M5 | the capture workflow's literal moved to 2.8.0 | the second-file clause |
| M6 | the capture workflow's install unpinned | that clause and the floor one |

M5 and M6 cover the one site that cannot read the key: no workflow
file sees another's `env:`, so `real-project-capture.yml` repeats the
version literally, and two pinned sites disagreeing is this row's own
finding one file over.

**Deviations.** Three, all stated rather than hidden.

1. `UX-940`'s two behaviour claims were re-read *before* the pins moved,
   in 2.8.1's own wheel rather than by running it: `stack.py`'s
   `get_unique_key` returns `1` and `BST_ELEMENT_HAS_ARTIFACT` is
   `False`; `element.py:3103` still refuses a redefinition of
   `max-jobs`, and no file in the wheel reads `max-jobs` from `public:`.
   Both hold, so the bump removes no version they were true of.
2. `real-project-capture.yml`'s pin carried a comment saying it was the
   version every capture here was taken with. Captures already in the
   repository stay on 2.7.0; a capture taken after this lands is on
   2.8.1 and its `run_context` says so. The comment now says that.
3. The extras' floor moved from `>=2.0` to `>=2.8.1`, which is a
   user-facing change: it is the smallest floor that matches what is
   exercised, and `requirements.lock` is compiled with `--extra dev`
   only. Measured, not argued: `quality.yml`'s own freshness command,
   `uv pip compile pyproject.toml --extra dev`, diffs zero lines
   against the committed lock, which holds no `buildstream` line.

`make lint` clean. `make test` on the pushed sha is in the pull request.

