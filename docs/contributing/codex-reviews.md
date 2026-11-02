# Codex reviews in the agent workflow

Codex reviews the **round PR** once, after the `integrator` merged the
tracks and the `walker` read the page, as an independent reviewer from
another vendor. It does not replace the push gate, CI, the Claude
`verifier`s that read each track, or the owner's approval (`UX-1369`).

## When

1. **At ready.** The session marks the round's draft PR ready for review;
   Codex reviews a PR automatically when it is marked ready, so no
   comment is posted. If nothing arrives, comment `@codex review` once.
2. **Again only when code moves.** A commit after the reviewed sha that
   touches code (not `docs/`, not a derived register, not a catch-up or
   adopt) asks for one more review. `python3 tools/dev_codex_status.py <pr>`
   says which.
3. **Security review** (`@codex security review`) only when the PR's diff
   crosses a boundary in [the threat model](../design/threat-model.md).
   The repository is public: findings post in the PR, as every review
   comment does.
4. **Not at all** on dependabot PRs, and on retro or memo PRs with no code.

## Findings

Each Codex finding is answered like a `verifier` hold: fixed with a
regression guard, or declined with evidence, in the owning task file,
and a reply in the finding's thread links that answer. The `closer`
pastes `dev_codex_status.py`'s output into the round document. Exit 0 is
the hand-off to the owner; exit 1 names each open finding or unreviewed
code change.

## When the service does not answer

A review that never starts is recorded as blocked in the round document
and the PR proceeds on CI and the verifiers; a missing external review
does not freeze the queue. On #338 the security review never started,
and the summary comment's `codex-review-state:v1` marker still read
`running` after the code review was submitted, so completion is read
from the bot's review or its +1 reaction, never from the marker.

## Grounding

Codex starts at [AGENTS.md](../../AGENTS.md), then [REVIEW.md](../../REVIEW.md);
a security review also reads [the threat model](../design/threat-model.md).
The PR names its task files, which carry the Required Fix and Acceptance
Test a reviewer checks the code against. Invocation:
[code review rules](https://developers.openai.com/blog/custom-code-review-rules-for-codex),
[security review](https://developers.openai.com/blog/scaling-cyber-defenders-with-daybreak).
