# UX-776: a derivation from git history is a property of the clone

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-744 (the register this fired on) | **Serves:** the session whose `--write` produces a different answer from CI's, on the same commit | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-744` derives the round register from `git log`. This container's
clone is shallow, so `git log` stops at the boundary and the
derivation stops with it:

```console
$ ls .git/shallow && git rev-list --count HEAD
.git/shallow
610
$ python3 -c "...print(len(dev_round_register.rounds()))"
32
```

CI checks out with `fetch-depth: 0`:

```text
E   AssertionError: [...round-register.md disagrees with the
    derivation - run --write] - and the derivation reads
    ['7', '8', '9', ... '69', '74', ... '107']
```

71 rounds against 32. `--write` here wrote a register missing 39
rounds and every CI job reddened on it — four Python versions, twice,
deterministically. The suite was green locally at the same commit,
because locally the *same truncated history* produced the file and
then agreed with it.

That last sentence is the defect. `--check` compares the derivation
against a file the same derivation wrote, so a clone that cannot see
the whole input is self-consistently wrong. This is `UX-418`'s
across-machines shape — a reading that cannot be compared between
runners — arriving through git rather than through timings.

Two costs, and the second is worse:

1. Whoever runs `--write` decides the register's content.
2. The failure is invisible where the work happens and only fires in
   CI, so the round pays a full push-and-wait cycle to learn it.

## Required Fix

The instrument refuses rather than answering from half its input:
`--check` and `--write` both red when `.git/shallow` exists, naming
`git fetch --unshallow`. A guard asserts the real checkout is not
shallow, so the condition is caught in `make test` and not in CI.

Not: silently unshallowing (a session's network is not the tool's to
spend), and not widening `--check` to tolerate a subset (that makes
the truncation permanent).

## Out of Scope

- Other tools that read `git log`. `dev_track_cost.py`,
  `dev_commit_bodies.py` and `dev_process_bands.py` all shell out to
  git, and whether each is depth-sensitive is a sweep this row does
  not do — the two it would need are a different measurement. Filed as
  a question for the next review rather than answered here.
- The container's clone depth itself — it is the harness's, and a
  tool that only works on a full clone should say so rather than
  depend on how it was cloned.

## Acceptance Test

```console
$ python3 tools/dev_round_register.py --check
/home/user/buildstream-graph-analysis is a shallow clone - ... (UX-776)
$ git fetch --unshallow && python3 tools/dev_round_register.py --check
$ echo $?
0
```

## Outcome

**Closed round 108.** Found by CI, not by the suite: four jobs red on
one guard while `make test` was green on the same commit.

**The gap measured.** `.git/shallow` present, 610 commits, 32 rounds
derived. After `git fetch --unshallow`: 1,538 commits, 71 rounds. The
committed register was 40 rows short and `--check` was clean against
it, because the file and the check read the same truncated history.

**The close measured.** `check()` and `main()` both refuse when
`.git/shallow` exists. The register was re-derived on the complete
history: 40 rows added, `--check` exit 0.

**Mutation table.**

| mutation | reddened |
|---|---|
| the refusal removed from `check()` | `test_check_refuses_rather_than_deriving_from_half_a_history` |
| `is_shallow()` reads `.git` instead of `.git/shallow` | `test_a_complete_clone_is_not_refused` **and** `test_the_real_checkout_is_complete` — the second is the one that matters: a refusal that fires on every clone is not a refusal |
| `is_shallow()` back to the marker's existence — the version CI reddened | `test_a_left_behind_marker_is_not_a_shallow_history`, whose fixture is a real `--depth 1` clone and a real stale marker, not a written file |

The second mutation is why the pair exists. A guard that only asserts
"a shallow clone reds" passes when the tool reds on everything.

**The first fix read a proxy, and CI said so.** `is_shallow()` began
as `(.git/shallow).exists()`. That reddened every job on `43dab8d` —
on a runner holding all 1,538 commits, which carries a stale marker.
`git rev-parse --is-shallow-repository` reads the same file and would
have fixed nothing. What distinguishes them is measurable: a grafted
boundary still records its parent in its own object and lacks the
parent object; a stale marker's parent is present.

```console
$ git clone --depth 1 file://$origin r && cd r
$ git cat-file -e $(git cat-file -p $(cat .git/shallow) | awk '/^parent/{print $2}')
$ echo $?
1                       # cut
$ # same marker written by hand over a complete clone
$ echo $?
0                       # stale
```

So the row's own defect — an instrument reading a proxy for the thing
it names — was committed once more while fixing it, and caught by the
only instrument that could: CI, on a machine whose clone differs.

**Deviation.** The row asks for the refusal and a guard, and both
landed. `test_the_real_checkout_is_complete` is the addition: it reads
the checkout the suite is running in rather than a fixture, so the
condition is caught where the work happens. It is the only clause here
that would have prevented this round's cost.

### Corrected by `UX-781` (2026-09-07)

The reading above is **also a proxy**, and the same CI job falsified it
two commits later. `git fetch --depth=N` on a clone that was complete
grafts a boundary without deleting anything, so every parent object is
still present and the test reads `False` on a history git has already
stopped walking:

```console
$ git -C fullprobe rev-list --count HEAD ; git -C fullprobe fetch --no-tags --depth=200 origin main ; git -C fullprobe rev-list --count HEAD
1541
855
$ python3 -c "…print(reg.is_shallow('fullprobe'))"
False
```

That is the third proxy for one question — marker existence, then
object presence — each committed as the fix for the last. What the
derivation depends on is the traversal: a commit named in
`.git/shallow` is parentless to git whatever the object store holds.
`is_shallow()` now asks whether such a commit is an ancestor of
`HEAD`; the guard's fixture is the depth fetch that falsified this,
and the version this row shipped is one of its mutations. See
`UX-781`, which also carries the cause of the truncation itself —
`ci.yml`'s own base-diff step, on the job that failed.

The register's 71 rows and both entry points' refusal stand.
