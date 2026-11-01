# UX-1369: Codex reviews the round PR once at ready, and its findings are answered like holds

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** PR #338 (Ruslan, 2026-11-01: "there is review 338 that introduces external pr review - lets review it and incorporate in our agentic workflow"); the workflow review of 2026-11-01 | **Serves:** every round PR, and the escapes no Claude verifier caught | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_codex_review_is_read_from_github.py`

## Motivation

The 09-28 review recommended an independent reviewer on each round PR;
the owner postponed it over Fable's token cost. Codex is set up on the
repository and bills to the owner's ChatGPT plan. #338 (written by
Codex) adds it, but as written it reds CI on two line caps
(CLAUDE.md 87 of 80, `rules.md` 81 of 80), requires both reviews on
every pushed head (#336 had 27 commits), and blocks hand-off on a
security review that never started on #338 itself.

## Decomposition

Input classes: a PR with a Codex review on its head; on an older sha
with only docs or registers after it; with code after it; with a +1
reaction and no review; with no review; a finding with and without a
reply; a diff that crosses a threat-model boundary and one that does not.

## Required Fix

Keep #338's `AGENTS.md`, threat model and `REVIEW.md` narrowing. Rewrite
`codex-reviews.md` to one review per round PR at ready, again only when
code moves after the reviewed sha, a security review only across a
threat-model boundary, none on dependabot or no-code PRs; a review that
never starts is recorded as blocked and does not freeze the queue.
`tools/dev_codex_status.py <pr>` reads completion from the bot's review
or +1 reaction and open findings from unanswered review threads. One line
each in CLAUDE.md and the rules card, inside their caps.

## Out of Scope

Branch protection, a `SECURITY.md` and a private reporting path (the
owner's call); per-track review (tracks are not PRs and keep their
verifiers); merging #338 itself.

## Acceptance Test

`python3 tools/dev_codex_status.py 338` reports #338's one open finding
and exits 1; on #336 it reports no review and the boundary note. The
guard's six tests pass offline and each mutation reds one.

## Decision

The summary comment's `codex-review-state:v1` marker is a proxy: read
at 19:41 UTC it still says `code_review.status: running` for `d9dc9706`,
while the bot's review on that sha was submitted at 15:30:48. Completion
is the bot's own review (`commit_id`) or its +1 reaction; the marker is
printed for the record. Security completion has no other reading, so it
is read from the marker and its absence is a note, never a failure.
"Answered" is a reply in the finding's thread, because thread resolution
is GraphQL-only and the session's GitHub proxy refuses GraphQL.

## Outcome (2026-11-01)

Gap, on `d9b25851` with #338's diff applied: `make lint`'s
`agent-config` and `docs-lane` jobs on #338 read `CLAUDE.md is 87 lines`
and `rules.md is 81 lines, cap is 80` (run 41321437534). After: both 80.

```text
$ python3 tools/dev_codex_status.py 338
#338 head d9dc9706fe; marker says {"code_review": {"commit_sha": "d9dc9706fe...", ... "status": "running"}, "security_review": {... "status": null}}
  FAIL: open finding: docs/contributing/codex-reviews.md:13 .../pull/338#discussion_r4436241059
$ python3 tools/dev_codex_status.py 336
  note: security review wanted (.github/workflows/real-project-capture.yml, bga/viewer/app.js, bga/viewer/element.js) and not started - recorded as blocked
  FAIL: no Codex code review on this PR - mark it ready, or comment `@codex review`
```

`python3 -m pytest -q tests/unit/test_the_codex_review_is_read_from_github.py`:
`6 passed`. Mutations, `PYTHONDONTWRITEBYTECODE=1`:

| mutation | red |
|---|---|
| a submitted review is not read | 1 failed, 5 passed |
| a +1 from anyone counts | 1 failed, 5 passed |
| every path is code | 1 failed, 5 passed |
| a reply does not answer a finding | 1 failed, 5 passed |
| no boundary wants a security review | 1 failed, 5 passed |
| no review is not a problem | 1 failed, 5 passed |

Deviation: the security review's policy (boundary PRs, posting publicly)
is the review's recommended default, pending the owner's call on the
2026-11-01 decision card. The four `S310`/`S603`/`S607` findings on the
tool are forced under this id (a fixed `https` host and `git` argv).
