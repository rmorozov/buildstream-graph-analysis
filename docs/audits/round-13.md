# Audit round 13: post-MVP — verify the fixes, then shorten the path

Run on 2026-08-19, same retained environment and captures as rounds
10-12. The sibling session landed round 12's thirteen filings
(UX-112..UX-124) in ten commits; this round re-verified them, and —
per the MVP verdict's own conclusion — opened the polish axis: the
tool now does the right thing, so the remaining leverage is how much
of the user's day it takes to do it.

## Verification scoreboard

Nine of thirteen hold outright; the strongest are the ones that
falsified their own filings:

- **UX-116** ran its filed round-10 clause, got the *opposite* of the
  predicted answer ("graph binds at 6 — room for 2 more builders"),
  settled it with a real 4×3 timing table showing the room was not
  realizable, and reworded the claim rather than the test.
- **UX-120** built the fixture (`examples/09-fine-grained-siblings`),
  fired the merge candidate on real data for the first time, measured
  the projection **missing reality** (1.00s projected vs 2.70s median
  measured merged rebuild) — and shipped it as an explicit floor
  (`projection_is_a_floor`) instead of tuning until it agreed. The
  never-documented "band" its acceptance referenced was refuted in
  place rather than invented.
- **UX-118**'s SIGSTOP diagnosis was confirmed exactly: the
  kill-the-tracer clause went **0/3 → 3/3** after suppressing the
  re-injected attach-stop, and UX-106's wrong "ptrace limitation"
  explanation was annotated, not erased.
- **UX-115**'s CI comment re-verified live on the retained grow pair:
  the gate table carries one-sentence reasons from the same predicates
  the exit codes use, "not requested" and "absent — not empty" cells,
  instance stamps, an update-in-place marker.
- **UX-121** now guards nine *rendered* surfaces (mutation-verified);
  **UX-122**'s docs test reads the workflow's own ref-name expression;
  **UX-114**'s publish decision is extracted and falsification-tested;
  **UX-113**'s `auto` policy re-verified here (all eight busybox
  elements traced, fail-toward-coverage). `make test` with live bst:
  **1538 passed, 0 failed**.

And one closure of this audit's own ledger: **round 12's +31-44%
spine×opens interaction was a warm-up artifact.** UX-112's factorial
refuted it; this round re-measured with an interleaved,
order-controlled design and confirms — no interaction, spine ≈ +1.7s
on the 2003-process storm (~0.85 ms/process) in this environment. The
refutation stands; what does not is its replacement headline, below.

## The findings

- **UX-128 (High)** — UX-117 guarded one of four identical
  `PTRACE_CONT` sites and then asserted no other path could strand a
  tracee; the exec-stop, exit-stop and fork-stop restarts all discard
  the CONT result, each able to reopen the identical hang. Plus the
  three "in a real sandbox" acceptance clauses that landed as plain
  subprocess tests.
- **UX-129 (High)** — "roughly a millisecond per process reconciles
  every figure" doesn't survive its own inputs (they span 0.32-1.14
  ms), the cited `matrix.json` doesn't exist, and the model's
  "budget two minutes" fdsdk extrapolation sits ~5× under the one real
  observation (+11 min), unremarked in four doc sites.
- **UX-130 (Medium)** — the attach-stop is *guessed* (first SIGSTOP per
  pid), the guess eats the direct child's genuine SIGSTOP, the test
  meant to catch that passes either way, and `forget_pid`'s zeroed
  slots break probe chains exactly at fdsdk's pid scale. `PTRACE_SEIZE`
  deletes the whole class.
- **UX-131 (Medium)** — five status rows contradicted their files
  (fixed by this round; the filing is the guard). Third round running
  of the two-copies defect.
- **UX-132 (Medium)** — UX-123's corrected figures left UX-107/108/112
  quoting the old ones unannotated, while UX-118 annotated UX-106
  properly in the same range: the convention needs writing down.
- **UX-133 (Low)** — spine/parser edges: pairing under pid reuse,
  fork-only counting, and the background-daemon wait.

## The polish direction (UX-125..UX-127)

The user asked the right post-MVP question: what simplifies the
scenarios? Walked with three rounds of lived friction and the failing
commands pasted:

- **`bga doctor` (UX-125)** — every environment this audit stood up
  was assembled by failure (venv, plugins, bwrap sysctl, compiler,
  staging), and every check already exists somewhere in CI comments
  and script headers. Front-load them.
- **One command, run twice (UX-126)** — the documented loop is three
  commands and five user-invented paths. `bga snapshot` + a
  project-local run store with `@last`/`@prev` makes the loop's second
  invocation print the compare verdict itself. This is the largest
  remaining gap between what the tool can do and what a tired user
  will actually do.
- **Plane 3's front door (UX-127)** — `bga cache-logs <project-dir>`
  currently answers "nothing to report" about a project whose logs
  exist; it should take the argument users have and list what the
  tree holds.

## Standing

The MVP verdict (round 12) stands; nothing found this round moves it.
The spine remains the one subsystem whose *failure* behavior lags its
data quality — opt-in and `auto` bound the risk, UX-128/130 are the
work — and the verification-discipline trend is genuinely improving:
this round's fix batch contained two self-falsifications done exactly
right (UX-116, UX-120) and one figure-annotation done right (UX-118 on
UX-106), against one guard-covers-one-of-four (UX-128) and one
headline-outruns-data (UX-129). The loop keeps working; the polish
round is what makes the tool's correctness cheap to reach.
