# Round 144 — the second styleguide audit's rows, viewer tracks in parallel

Run on 2026-09-27 off main at `71d3dcda` (`#297`/`#298`), on `UX-1042`-`UX-1051`'s
filing and `UX-1052`-`UX-1055` filed inside the round. `UX-1045` did not land a
track and stays open.

```text
closed   UX-1042 UX-1043 UX-1044 UX-1046 UX-1047 UX-1048 UX-1049 UX-1050
         UX-1051 UX-1052 UX-1053 UX-1054 UX-1055
filed    UX-1056 (back after a reveal does not re-fold), UX-1057 (the
         twin table drops a certified lower-bound mark), UX-1058 (the
         narrow-rail toggle is unreachable by keyboard); one bookkeeping
         line (macro_micro Perfetto top margin, 129 px of 7,600)
open     UX-1045 (no track ran)
index    dev_close_task.py --counts: 1019 scenarios, 21 open, 998 closed
spread   dev_touching.py --spread: 33-172 of 647 test files
```

## The J3 re-base

`UX-1044`'s merged tree read red on `test_the_document_is_a_journey.py`'s
`J3` (`both_scale`, 390): `21.01 > 20.34 + 0.5`. Cause: `a3eeb2cb`'s wider
fold label wraps two `h2`s at 390 that did not wrap before. Re-measured
per styleguide §3l on the merged tree and recorded in `UX-1044`'s
Outcome; the guard's bound moved with the measurement, not the code.

## The lock port

`4ae90534` ports `#298`'s lock refresh (coverage `7.16.2`) onto this
branch's lockfile, so `pip-audit`'s freshness diff reads clean instead
of citing a stale coverage pin.

## The scanner, red on both pull requests

`github-advanced-security`'s check ("requested model is not supported")
read red on both `#297` and `#298` alike - GitHub's Copilot scanner,
not a check either pull request's own commits touch. Commented on both;
a rerun returned 403.

## Budgets after the merge

```text
page (golden)         140,343 / 150,000 B
macro_micro landed       7,471 /   7,600 px
xl_both landed                    7,447 px
390 golden               8,347 /   8,500 px
390 macro_micro         11,208 /  11,400 px
```

`make push-check` returned 0 on `10cde1d2`; pushed.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| implementer | sonnet | UX-1051 one resting rule for select/text | — | — | — | — |
| implementer | sonnet | UX-1043 toggle gutter reserved with flex | — | — | — | a browser test file needed a tiers.py row before it had one |
| implementer | sonnet | UX-1048 accent guard reads each grade's sentinel | — | — | — | a hard-coded hex equal to an accent still passes by value |
| implementer | sonnet | UX-1047 the page's one h1 names the run | — | — | — | runDisplayName climbs on any literal "run" |
| implementer | sonnet | UX-1052 viewer JS ships gzipped under PAGE_BUDGET_B | — | — | — | — |
| implementer | sonnet | UX-1046 UX-1044 rail discloses current chapter; one fold | — | — | — | grade guard LOOKS omits font-weight |
| implementer | sonnet | UX-1049 one landed-height bound per size class | — | — | — | compact bound re-measured at integration, 13.5 -> 13.0 |
| implementer | sonnet | UX-1053 UX-1050 two-plane volume at scale | — | — | — | — |
| implementer | sonnet | UX-1042 pointer travel is a budget | — | — | — | — |
| implementer | sonnet | UX-1054 the first Tab starts at the top | — | — | — | nav.js mark() scrollIntoView moved the focus start |
| implementer | sonnet | UX-1055 copy-rows/top-n one place, DOM order | — | — | — | — |
| verifier | sonnet | verify UX-1043 UX-1051 | — | — | — | new browser test files need a tiers.py row |
| general-purpose | opus | integrate: merge tracks, tiers rows, re-measure budgets, push-check | — | — | — | github-advanced-security red on #297 and #298 alike (Copilot scanner, not this round's) |
| general-purpose | opus | walk 10cde1d2: macro_micro + 1,202 two-plane, 1440/390 | — | — | — | every round row held; 3 pre-existing findings filed UX-1056-1058 |

Token, call and wall figures are unknown for this round's tracks - no
transcript was recoverable at close; the ledger marks them rather than
guessing (`UX-757`-adjacent, the same convention `UNPRICEABLE_ROUND_WAIVER`
names for round 101).

Three walk findings, all pre-existing, filed as `UX-1056`-`UX-1058`;
every round row held on the walk.
