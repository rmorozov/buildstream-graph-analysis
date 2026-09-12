# UX-811: the commit-body gate reads Dependabot's generated bodies

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-696 (the gate), UX-698 (the shelf that sends Dependabot's pull requests) | **Found by:** round 113, PR #217's red `test (3.x)` | **Serves:** the session merging the shelf's pull requests; CI reading only what the register governs | **Topic:** process | **Area:** tools | **Shape:** bounded

## Motivation

`UX-698`'s shelf sends dependency updates as Dependabot pull requests.
Dependabot writes its commit body: release notes, changelogs, a
commits list — 75 lines on PR #217. `UX-696`'s gate reads every commit
the branch adds against CLAUDE.md's eight-line cap, so every
Dependabot pull request is red on arrival, and the shelf can never
merge:

```text
$ git log -1 --format='%ae' origin/dependabot/github_actions/actions-b41540d87c
49699333+dependabot[bot]@users.noreply.github.com
$ git log -1 --format=%b origin/dependabot/github_actions/actions-b41540d87c | wc -l
75
FAILURE tests.unit.test_the_commit_body_gate_runs_before_ci::test_the_checkout_stays_within_the_commit_body_cap
  AssertionError: 1 of 1 commit(s) considered in origin/main..HEAD are over CLAUDE.md's 8-line commit-body cap: [('80c7ecb61', 'Bump the actions group across 1 di…
```

The register governs the record's authors: a task file is where an
argument goes, and a body says what changed. A bot's generated body is
neither an argument nor a record; the pull request is.

## Required Fix

`tools/dev_commit_bodies.py` skips a commit whose author email is a
GitHub App's (`…[bot]@users.noreply.github.com`) and says how many it
skipped, so the count sentence still names its population. Guard in
`tests/unit/test_a_commit_body_is_eight_lines.py`: a long-bodied
commit by such an author exits 0 and is reported as skipped; the same
body by a person still exits 1; mutation: drop the author test, the
bot's commit is over.

## Out of Scope

- Squashing or rewriting Dependabot's commits — its branch is its own.
- Any other author exemption: a person's body is the record.

## Acceptance Test

`python3 tools/dev_commit_bodies.py origin/main` on PR #217's head
exits 0 and prints the skipped count; the two new guards green, the
mutation red; PR #217's `test (3.x)` green on its next run.

## Outcome

**Gap measured.** On PR #217's head (`80c7ecb6`, one commit by
`49699333+dependabot[bot]@users.noreply.github.com`, 75 body lines):

```text
$ python3 tools/dev_commit_bodies.py origin/main     # before
1 commit(s) over the 8-line body budget CLAUDE.md states:
  80c7ecb61  75 lines  Bump the actions group across 1 directory with 6 updates
```

**Close measured.** `_log` carries `%ae`; `over_cap` skips an author
matching `APP_AUTHOR` (`[bot]@users.noreply.github.com$`) and returns
the skipped count, which the sentence names:

```text
$ python3 tools/dev_commit_bodies.py origin/main     # after, same head
0 of 1 commit(s) in origin/main..HEAD checked (0 predate the rule, 1 by a GitHub App); every one is within 8 body lines
$ python3 -m pytest tests/unit/test_a_commit_body_is_eight_lines.py tests/unit/test_the_commit_body_gate_runs_before_ci.py -q
15 passed
```

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `if False and APP_AUTHOR.search(email)` (no exemption) | `test_an_app_s_generated_body_is_skipped_and_counted[…dependabot[bot]…-0-1 by a GitHub App]` | 1 of 14 |

Reverted; 14 passed. The person-authored case (`dependabot@example.com`,
exit 1) stays red under the same body, so the exemption is the App's
address, not its name.

**Deviation.** None. Session-side, one commit; the verifier is PR
#217's own `test (3.x)` on its next run.
