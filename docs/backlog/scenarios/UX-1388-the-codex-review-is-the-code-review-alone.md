# UX-1388: the Codex review is the code review alone

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-1369` | **Found by:** Ruslan, 2026-11-24 07:40 UTC ("for me codex security review doesn't work. So I propose to drop it from rules and use only codex review described in #338") | **Serves:** every round PR | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_codex_review_is_read_from_github.py`

## Motivation

`UX-1369` asks for `@codex security review` on a round PR whose diff
crosses a threat-model boundary. It never started for the owner (#338,
and `dev_codex_status.py` reports it "not started - recorded as blocked"
on every such PR), so the rule produces a standing blocked note and no review.

## Required Fix

The procedure, `AGENTS.md`, `REVIEW.md` and `dev_codex_status.py` request
and read the Codex code review only; the threat model stays as reading for
the code review's Security pass.

## Out of Scope

The code review's cadence (`UX-1369`: once at ready, again when code moves).

## Acceptance Test

A guard reddens when any of the four review documents asks for
`@codex security review`, when the status tool reads a security review, or
when the procedure drops its "No security review" line.

## Decision

Drop the request, its boundary table (`BOUNDARIES`, `crosses_boundary`,
`security_note`) and its marker read; retitle the threat model, which is
the Security pass's reading, not a second review's.

## Outcome

Gap: `git grep -n -i "security review" -- AGENTS.md REVIEW.md docs/contributing tools/dev_codex_status.py`
at `0aa392cf` read 9 lines asking for or reading it (procedure item 3,
its grounding and link, `AGENTS.md:25`, `REVIEW.md:11`, the tool's
docstring, `security_note` and its marker read).

Close: `python3 -m pytest -q -p no:xdist tests/unit/test_the_codex_review_is_read_from_github.py` -> 8 passed.

| mutation | reddened | count |
|---|---|---|
| `@codex security review` appended to `AGENTS.md` | `test_no_rule_requests_a_security_review` | 1 failed, 7 passed |
| `state.get("security_review")` appended to the tool | same | 1 failed, 7 passed |
| procedure's `**No security review.**` renamed | same | 1 failed, 7 passed |
| reverted | — | 8 passed |
