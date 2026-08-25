# Changelog

What changed between the `bga` you installed and the one you have now.

A release here records a **contract state**, not a date: the nine
published contracts and the command surface as they stood, plus what
moved since the last row. The procedure is
[`docs/contributing/release-guide.md`](docs/contributing/release-guide.md)
and the argument is
[Direction 10](docs/design/directions.md).

Two things a reader should know before using the numbers:

- **The package version is provenance, not compatibility.** It says
  which build wrote an artifact. What decides whether your parser still
  works is the *contract* version — `analyze/v2` — and those move
  independently. A release that bumps the package while every contract
  stays put has broken nothing you pin.
- **Pre-1.0, `breaking` and `extending` both move MINOR**, so the row
  records which it was. The number cannot say it while the major is
  pinned at 0.

| release | date | closed rows | commit | kind |
|---|---|---|---|---|
| [0.2.0](#020--the-build-that-says-what-it-is-2026-08-24) | 2026-08-24 | 243 | `fac9618` | initial |

## 0.2.0 — the build that says what it is (2026-08-24)

The first recorded release, and it is named for what it adds rather
than for what it fixes: **an artifact now says which build produced
it.**

`bga` reads its own past output as input — `@last`/`@prev`, the
baseline set, `cache-trend`, `store-aggregate` all open artifacts
written by whatever `bga` was installed at the time. Until this
release, nothing in those artifacts said which build that was:
`__version__` was read in two places, both the `--version` string, and
written into nothing. A run directory from the first week and one from
last week were indistinguishable to the tool reading them both.

**Contract delta:** none. All nine contracts stay at `v1`, and no
command or flag was added, renamed or removed. The version moves
because `0.1.0` had never moved and therefore could not signal that
anything had — and because from here the number is derived from this
recorded state rather than chosen.

**Upgrade note:** none required. Artifacts written by older builds
carry no producer stamp, and that absence reads as `unstamped` — an
explicit unknown, never as agreement. Nothing is rewritten, and no
comparison behaves differently yet; `UX-250` is where the recorded
stamp starts deciding anything.

**Carried findings.** `UX-241`'s first review filed three, all still
open and all documentation: the architecture's CLI table is two
subcommands behind (`UX-245`), the end-to-end guide never reaches
`bga whatif` (`UX-246`), and the architecture's own Verification Log is
stale about its currency (`UX-247`). They are named here rather than
left in the backlog alone, so "we knew" is on the record.

```text state
contracts: analyze/v2 blast/v1 compare/v1 correlate/v1 host/v1 plane2/v1 plane2/v2 sources/v1 store-aggregate/v1 store/v1 whatif/v1
commands: analyze baseline blast cache-logs cache-trend capture checkout-cost chrome-to-trace compare correlate cross-check diagnostics doctor extract floors gen-synthetic graph graph-from-show log-to-chrome native-to-chrome rebuild-set release-notes replay run-context snapshot sweep timeline utilisation view whatif wrap
```

### What landed

<!-- generated: UX-252 238→243 -->
5 scenarios closed (closed-row markers 238 → 243).

**contracts**

- [UX-248](UX-0248-there-is-no-authoritative-contract-inventory.md) — `schemas.names()` answers a narrower question than it looks like it does - the documents `bga --schema` can print, not the documents `bga` writes.
- [UX-249](UX-0249-nothing-an-artifact-records-says-which-bga-wrote-it.md) — `bga` reads its own past output as input, and nothing an artifact recorded said which build wrote it.
- [UX-250](UX-0250-comparison-refuses-on-host-and-mode-but-not-on-contract-movement.md) — `bga compare` refuses on host and on cache mode, with an exit code of its own, and had nothing to say about the two runs having been measured by different builds of the tool

**docs**

- [UX-251](UX-0251-a-release-is-a-contract-state-not-a-date.md) — `bga --version` said `0.1.0`, unmoved across 29 rounds and 247 scenarios;
- [UX-252](UX-0252-the-release-notes-should-be-generated-from-the-closed-rows.md) — Hand-writing release notes would make a third copy of facts that already live in the task file's Outcome and the closed row - and two hand-maintained copies of one fact drifting is this repository's…
<!-- /generated -->

Rows 1–238 predate recorded releases: they landed across twenty-nine
rounds under a version that never moved, which is the thing this
release fixes. Their history is
[`docs/backlog/scenarios/closed.md`](docs/backlog/scenarios/closed.md)
and each task file's Outcome, and reprinting 238 of them here would be
a copy of that file rather than a changelog.
