# Audit round 19: the source axis meets its own output

Run on 2026-08-20, same retained environment as rounds 10-18. Input:
the sibling landed all of round 18's filings in four commits —
UX-175 (the drain), UX-171..174 (the whole source axis), and
UX-170+176+177 (the band's disputed region and the guard/corner
batches). The suite grew to 2,121; the status table and every file
marker agree.

## The landings, verified live

- **UX-175** 🟢 — the shutdown drains and the drain is the wait: raw
  non-blocking reads with the grace as deadline, binary pipe with one
  decode point, the `read1` handover so nothing pre-interrupt is
  lost; the caller consumes stopped-vs-killed and writes the
  escalation notice; `bga extract --interrupted` wired, with the hint
  carrying it only for the mid-build case. All seven drain tests
  re-run live, including the flood-past-64KB and unterminated-line
  deadlines. One learned detail worth keeping: renaming the flag
  would not redden the guard (argparse prefix matching) — only
  deletion does, and the log says so.
- **UX-170** 🟢 mechanism — the disputed region: a delta that is
  significant *and* inside the baseline set's own observed range now
  answers `WITHIN THE BASELINE SET'S OWN OBSERVED RANGE` instead of a
  verdict; the −25% same-commit pair refuses, the −5.8%/−9.8% pairs
  keep their answers, and the review checked n=3 as well (the
  extreme pair improves from a false REGRESSED to the refusal). The
  *documentation* did not keep up — `UX-180`.
- **UX-171..174** 🟢 — this round's centerpiece verification, run two
  ways. The review re-ran the log's fixture end to end (fresh build,
  rewritten sources, `8 direct | 9/10 blast | 22s`, headline
  reproduced). Independently, this audit built its own: a round-17
  project copy with six libs rewritten to one shared `git` url, `bga
  extract` re-run **offline** on the existing `build.log` (the
  inventory reads YAML, not the network — as designed), and the
  report produced the table exactly as filed:

  ```text
  resource                            direct  blast    work
  gitlab.example.com/org/monorepo          6   8/11     25s
      keys on ref: any commit to this rebuilds all of them ...
      rebuilds 8 element(s) (7 that build, 1 that assemble)
  ```

  `bga blast` answered all three target shapes; the kind split and
  the work-not-wall-clock note rendered; a pre-inventory run said
  "this capture cannot answer that" rather than "nothing".
- **UX-176/177** 🟢 — the paste test really pastes, the phase guard
  really interrupts through a seam, the `@stamp` exact match wins
  over its same-second sibling, the casd file-selection corner is
  closed behaviorally, and the orphan counts were dropped rather than
  wired (one source of truth).

## What the round found

**The tool's own printed identity does not round-trip (UX-178,
High).** Pasting the Shared Sources table's resource cell into
`bga blast` — the obvious next command — silently resolves as a
*path* and answers "rebuilds nothing here", because the table prints
the normalized scheme-less identity and the url detector requires a
scheme. Observed live on the fixture above; with `https://` it works
and even names the ambiguity. UX-164's paste-and-go class, on the
newest feature. Same filing: the existing-but-not-a-run directory
traceback (the log promised exit 2), and two smaller answer gaps.

**The discriminating case that was never built (UX-179, High).** The
review reverted UX-173's cost sorter to count-only order and the
guard class stayed green: on the golden fixture the two orders are
identical, and the test's closing assertion never compares them —
while both the log and the test's own docstring claim otherwise. The
sorter is correct; the guard story is the exact shape UX-176 was
filed to hunt, shipped in the same range as UX-176.

**The trail and the edges (UX-180..182, Medium).** The docs still
assert what the disputed region deliberately broke (the gate's
"never a second definition" docstring, the three-verdict lists, the
present-tense defect sentence UX-170's own Required Fix ordered
corrected) and the glossary has no rows for the axis's five
load-bearing terms; `normalize_url` fails in both directions
(mangled `git+https`/uppercase schemes; pip index over-grouping);
and the inventory stops at the junction boundary — which is exactly
where a freedesktop-sdk-shaped monorepo question will land, so
UX-182 is the axis's natural next step, ahead of need.

## Standing

The MVP verdict stands. The source axis went from argument to
working feature in one round, and its verification found the same
two classes every new feature has shown: the printed-output
round-trip and the guard that describes more than it checks. Priority
for the sibling: **UX-178 first** (a confident false "rebuilds
nothing" on the headline flow, cheap), then **UX-179** (the guard,
plus its two unwired siblings), then **UX-181** before UX-182 (the
identity model should be right before the junction walk multiplies
its inputs), with UX-180 in any gap. After UX-182 lands, the next
conversation with the user's real project is the one this axis was
built for: point `bga analyze` at a junction-heavy capture and see
whether the monorepo headline names the repository they expect.
