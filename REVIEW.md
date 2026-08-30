# Review instructions

What a review of this repository checks, and what it leaves alone.
`CLAUDE.md` is the day-one page and
[`docs/contributing/fixing-guide.md`](docs/contributing/fixing-guide.md)
is the rule; this file is neither. It is the review policy, and it is
read by whoever — or whatever — reviews a pull request here.

## Passes

Run four passes and tag every finding with the pass it came from.

**Bugs.** Logic errors, broken edge cases, subtle regressions. The
question is what input makes this wrong, stated concretely: a value, a
state, an ordering.

**Security.** Injection, authentication gaps, secrets or absolute paths
in a committed artifact. `bga` reads other people's build logs and
writes a page they will open — a field that reaches the report reaches
a browser.

**Compliance.** The diff against the task file that asked for it:

- does it do what the **Required Fix** says, and
- does it stay inside **Out of Scope**, and
- does the **Acceptance Test** section carry real pasted output rather
  than a description of output?

A diff that solves a different problem than the one filed is a finding
even when the code is good.

**Evidence.** This repository's own discipline, which no generic
reviewer applies:

- a number without the command and fixture that produced it;
- a new guard with no mutation recorded against it (see the `falsify`
  skill) — a guard nobody falsified is a guard nobody knows can fail;
- a guard whose setup a *different* gate already excludes, so it would
  pass whatever the gate under test does. Five of those were found in
  `UX-420` alone, and they are invisible to reading;
- a ratio judging a quantity near its noise floor, without an absolute
  magnitude beside it (`UX-420`, `UX-422`);
- a timing compared across machines in any form — absolute, scaled or
  ranked (`UX-418`);
- a claim in a document that its own body does not do.

## What Important means here

Reserve **Important** for a finding that would break behaviour, leak
data, breach a hard rule in fixing guide §5, or leave a guard unable to
fail. Everything else is a **nit**.

A missing measurement is Important, not a nit. This repository has
shipped wrong numbers that four documents then quoted.

## Cap the nits

At most five nits per review; summarise the rest as a count. A review
nobody finishes reading is a review that did not happen.

## Do not report

- Generated files, committed fixtures under `tests/fixtures/`, and the
  golden snapshot — those change by regeneration, not by hand.
- Anything `make lint`, `make check-clean` or the suite already
  enforces. If CI can catch it, CI should, and a finding about it is a
  finding about the wrong layer.
- Prose style in a task file's Outcome. It is a record, not an essay.

## The threshold

Findings do not approve or block on their own. A human approves through
branch protection, informed by them. The agent that wrote the change
has no route to approve it, and that separation is the point of writing
this file down rather than trusting a prompt.

## Tuning

When a review flags the same mistake twice, the correction goes into
`CLAUDE.md`'s **Things Claude gets wrong** in that same review — and
because review reads `CLAUDE.md`, the mistake is caught from the next
pull request onward. When a pass stops producing findings that survive
verification, retire it here rather than leaving it as ritual.
