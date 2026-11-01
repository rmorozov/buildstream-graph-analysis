# Codex reviews in the agent workflow

After local verification and self-review, the implementing agent requests
both external reviews on every PR, including documentation and workflow
changes. This is a process requirement, checked by the human integrator;
this document does not install a branch-protection check or enable a service.

## Request and record

1. Run the existing push gate, push the branch and open or update the PR.
   Record its full head SHA and the task or user request in the PR description.
2. Check whether automatic reviews already cover that head. For either
   missing review, post its command as a separate PR conversation comment:

   ```text
   @codex review
   ```

   ```text
   @codex security review
   ```

3. Record each request URL, reviewed SHA, result URL and state in the PR:
   pending, completed, or blocked. A request, reaction, missing comment or
   empty public findings list is not proof that the review completed.
   Inspect the associated task/report where available.
4. Validate findings against the code and relevant contracts. Fix accepted
   findings with regression evidence; explain rejected findings with evidence.
   Record deferred work and its impact for the human approver. Sensitive
   security details stay in a restricted report; the PR carries safe status.
5. After a new push or rebase, repeat for the new head; use automatic runs
   when they demonstrably cover it. Do not post duplicate requests for a
   review already pending on that head.
6. Hand off with both results and outstanding dispositions. Do not merge or
   claim review completion while either review is pending or blocked.
   A maintainer may explicitly waive a blocked service for a named head,
   recording the reason and substitute review; an agent cannot self-waive.

If access, quota, installation or service availability prevents a review,
record the actual response and leave the PR draft or explicitly blocked.
Requesting review does not configure repository access. Local self-review,
CodeQL and dependency audits do not count as either Codex review.

## Grounding

Code review starts at [AGENTS.md](../../AGENTS.md) and
[REVIEW.md](../../REVIEW.md). Security review uses
[the threat model](../design/threat-model.md). Authors link the affected task,
contract, guide and validation output in the PR. Reviewers verify those
documents against the implementation and identify assumptions they could
not validate. Never claim a test or scan ran without its result.

## Audit of the existing guidance

Source audit, 2026-11-01, main at `d9b25851`; GitHub file reads and code
searches for `threat` and `security`. No runtime or security scan was run.

| Existing grounding | Assessment and change |
|---|---|
| CLAUDE.md, rules card, fixing guide | Detailed commands, invariants, evidence and completion rules; retain these as the source of truth. Add an AGENTS.md entry point for Codex. |
| REVIEW.md and the self-review/review skills | Four substantive passes and review routing already exist. Add external-review lifecycle and narrow fixture/CI exclusions so real defects remain reportable. |
| Architecture and ingestion documents | Useful domain grounding; reviewers read only affected sections and verify against code. |
| tools/bga_view.py and architecture | Local viewer boundaries are documented, but security context is scattered. Add a compact threat model spanning input, export, capture and CI. |
| .github/workflows/quality.yml | CodeQL for Python and JavaScript, dependency audit and other checks exist. They do not establish completion of either requested Codex review. |

AGENTS.md, SECURITY.md and docs/design/threat-model.md were absent at the
audited revision (file reads returned 404). A security reporting contact and
supported-version policy still need a maintainer decision; this change does
not invent one. If no private reporting channel is configured, ask the
maintainer for one without publishing exploit details.

**Guard:** none — review completion and service access are external states.
Acceptance is a PR with both request links, completion or blocking evidence,
head SHA and finding dispositions. Text-presence tests cannot prove a
service ran. CI and the existing push gate remain separate requirements.

## Invocation references

Verified against official OpenAI documentation on 2026-11-01:
[code review rules](https://developers.openai.com/blog/custom-code-review-rules-for-codex)
and [security review](https://developers.openai.com/blog/scaling-cyber-defenders-with-daybreak).
Availability depends on workspace access and repository connection.
