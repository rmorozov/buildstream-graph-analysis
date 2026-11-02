# Agent instructions

Read [CLAUDE.md](CLAUDE.md) for the project map and commands, then
[the rules card](docs/contributing/rules.md). These rules apply to all
coding agents; provider-specific model names in CLAUDE.md apply only
when that provider is available. Report unavailable capabilities.

## Review guidelines

Read [REVIEW.md](REVIEW.md) before reviewing a change. Follow its four
passes and finding threshold. For security, also read the
[threat model](docs/design/threat-model.md). Read the task and affected
contract or guide sections; use code and guards to verify their claims.

Prioritise wrong results, unsafe recommendations, data exposure and
material time or memory regressions. Distinguish measured results from
fixed-duration replay projections; preserve unknowns and refusals.
Trace changed values through JSON, CLI and viewer consumers. A passing
internal assertion does not prove that rendered advice is consistent.

## Before handing off a PR

Follow [the external review procedure](docs/contributing/codex-reviews.md):
a round PR is reviewed once when marked ready, again only when code moves
after the reviewed sha, and a security review only when the diff crosses a
threat-model boundary. Answer each finding in its task file.
A review-only task reports findings without modifying the author's code.
Do not recursively request reviews when acting as the reviewer.

Existing push checks, CI and human approval remain required.
