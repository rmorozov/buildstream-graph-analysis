# Audit round 17: the fixes verified where they will be lived in

Run on 2026-08-20, same retained environment as rounds 10-16. Input:
the sibling landed **all eight** round-16 filings in eight commits —
UX-156..UX-162 plus the twice-deferred UX-148. This round verified
every one of them live, in the exact shapes the user's big-project
sessions will exercise, and filed what the verification itself walked
into. The polish lens stays: simple, concise, consistent.

## Eight landings, eight live verdicts

Everything below was exercised on real captures (a copy of
`examples/06` outside the repo, plus the review's own nested-layout
copy), not just read.

- **UX-156** 🟢 with words to fix — the failing snapshot leads with
  `THIS BUILD DID NOT FINISH`, the verdict refuses
  (`Verdict: NOT COMPARABLE` with the reference-only numbers below
  it), gates exit 6, and the next healthy snapshot walked back past
  the failed run *and said so*. The mechanics hold. The words around
  them are the new filing (`UX-164`): the replay hint printed under
  the walk-back is `$ bga compare @prev @last`, and `@prev` resolves
  to the very wreckage the walk-back skipped — pasting the tool's own
  suggestion reproduces the comparison it just refused. Plus a number
  agreement slip and a count that calls six cache hits casualties
  ("0 of 7 scheduled built" on a queue of 0 built / 6 cached /
  1 failed).
- **UX-157** 🟢 — SIGINT mid-build, live: exit 130, no traceback,
  `plane2.json` and `run/` salvaged, partial analysis with the
  incompleteness banner, no surviving `bst`/`buildbox-run`. The
  contract is real — and it ends at the build's edges. A SIGINT that
  landed during `Extracting run data (bst show)...` (this round,
  live) was a raw `KeyboardInterrupt` traceback and a snapshot
  without `run/`, even though `build.log` was complete and extraction
  is re-runnable from it. The slow phases UX-159 flagged are exactly
  the unprotected ones — filed as `UX-163`, with the review's
  grace-window edge (120s then SIGTERM kills bst before its Pipeline
  Summary, losing `queue_summary` on precisely the biggest builds).
- **UX-160** 🟢 — the review built the nested copy and ran it end to
  end: `Census: 11 of 11 element(s) assessed`, Plane 2 keyed by
  `components/*.bst`, and `bga correlate` joined nine elements across
  planes — the exact mismatch the item existed to prevent, gone. The
  shim's name derivation and the census agree.
- **UX-161** 🟢 — a manually started casd on the build's cache dir is
  detected (pid, age, remedy), one on a different cache dir is not,
  doctor states its own blind spot. One divergence found beside it:
  the check reads `buildstream.conf` while bst 2.7 tries
  `buildstream2.conf` first, and the `cachedir:` parse repeats the
  naive `startswith` that UX-162 just fixed for `element-path:` —
  `UX-166`.
- **UX-158** 🟢 with a defect class the guard cannot see — the caps
  hold (compare 36, extract 40, top 45; capture/snapshot grew to
  23/33 from UX-148/159 flags landed later in the same range — the
  log's table is honest at its commit, stale at HEAD). But "cut to
  its first sentence" was executed by deleting continuation *lines*:
  at least seven flag helps now end mid-sentence
  (`correlate --help` ends "for the same"; `graph --help` "grouped by
  BuildStream"; five more, one with an unbalanced paren). A truncated
  string is shorter, which is what a line-count guard rewards —
  `UX-165` restores the sentences and adds a fragment check.
- **UX-159** 🟢 — all phase lines observed in order on a live
  capture; `--list` sizes and total; `prune --keep/--older-than/
  --dry-run` all behaved, alias protection included. The seam is in
  *what* it protects: with a failed and an interrupted run as the two
  newest, `prune --keep 2` protected exactly those and offered to
  delete the only healthy snapshot — the walk-back's baseline. Husks
  survive every criterion; the "recorded baseline" it guards has no
  producer. `UX-167`.
- **UX-162** 🟢 — all seven debts paid as logged; the vendored
  `buildbox-run` resolves live, the four claimed tests exist and
  pass, the UX-152 annotation narrows the claim exactly as the
  convention asks.
- **UX-148** 🟢 — with a sabotaged bwrap under `--diagnose`, the
  summary quoted the sandbox's stderr and named the invocation; the
  per-invocation stderr files exist; `replay-sandbox` printed
  ready-to-paste, and its refusal on vanished binds names the paths.
  The tee preserves signal semantics per the UX-140 contract
  (re-raise via `os.kill(self)`, `WIFSIGNALED` reaches the parent).
  The default path keeps the pure exec — verified byte-for-byte
  behavior, no stderr dir without `--diagnose`.

Suites: 1,719 passed (all unit modules including the eight new ones),
docs suites 34 passed, `make lint-docs` clean. Status table and file
markers agree for all eight.

## What this round files

Two Highs from the verification's own footsteps:
**UX-163** (the interrupt contract covers the build and not the
minutes around it) and **UX-164** (the walk-back's replay hint
reproduces the comparison it just refused — on long-project stores,
where failed and interrupted runs are the common tenants, the printed
command is wrong more often than right).

Four Mediums: **UX-165** (seven help strings end mid-sentence, plus
the stale table annotation), **UX-166** (the casd check reads a
config bst does not), **UX-167** (prune protects two aliases and not
the baseline the walk-back needs; husks survive; the baseline key has
no producer), **UX-168** (analysis slurps the whole trace into RAM —
GB-scale RSS right after a big build — plus the census closure cost
and six one-liners).

A consistency probe that found nothing to file: `@last`/`@prev` are
accepted uniformly across `analyze`, `correlate`, `utilisation`,
`diagnostics`, `cache-trend`, `compare` and `baseline --candidate` —
the alias grammar is whole.

## Standing

The MVP verdict (round 12) stands. The big-project axis opened in
round 16 is closing fast: of its seven filings plus UX-148, all eight
landed and all eight hold. What round 17 adds is smaller in kind —
the two Highs are seams *between* verified features (salvage × phase
structure; walk-back × replay hint), which is what audits find when
the features themselves have stopped breaking. Priority for the
sibling: **UX-164 first** (one printed line, actively misleading,
cheap), then **UX-163** (the remaining interrupt windows), then
UX-167 (the prune contradiction), with UX-165/166/168 as the tail.
After those, the polish backlog is genuinely thin; the next axis
worth opening is UX-168's capacity work plus UX-108's still-unpaid
overhead measurement — the two numbers a thousands-of-elements
project asks about first.
