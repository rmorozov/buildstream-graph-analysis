# Round 108 — three tracks, and a CI step that cut the history it had asked for

Run on 2026-09-07.

Four rows closed, two filed. Three were the round's planned tracks;
the fourth is what the round found while trying to make CI green.

## The tracks

`UX-771` derives the section-numbering population instead of naming
three paths, `UX-772` teaches the register to read a **dateline**
rather than a document's first date, and `UX-773` sweeps a browser and
profile that a `SIGKILL`ed xdist worker leaves behind. Each ran as an
`implementer` on `sonnet`; `UX-771`'s verifier found a section id
matching inside a longer one and the track was amended before merging.

`UX-772`'s own verifier is the one worth reading back: the first pass
fixed `document_date()` and then filtered the population on
`document_date() is not None`, which is the same silent skip the row
was filed on, moved one layer down. The population now reds on an
unwaived `None`.

The merge widened that population again, for a reason that belongs to
the fourth row: this branch's register carries 71 rounds where the
track's base carried 32, so rounds 7-9, 19 and 22 met the guard for
the first time. Each is waived with a measured reason rather than a
boundary — 7-9 state no date at all, 19 is a two-day round with a
commit on each day, 22 has a retroactive documentation commit.

## The fourth row

`UX-781`. The register guard was red on CI and green here, and the
job's own step list said why: step 10 ran the whole suite green, step
13 ran `git fetch --no-tags --depth=200`, step 27 re-ran the small
tier and failed. A depth fetch **creates** a boundary on a complete
clone — 1,541 commits to 855, measured — so every step after it read
a truncated history. The checkout had asked for `fetch-depth: 0`
sixteen steps earlier.

Two guards were in position and neither fired, both for the same
reason. `test_ci_asks_for_the_history_these_guards_read` asserts
`"fetch-depth: 0" in workflow` — it reads the checkout, not what the
job then does to the clone. And `is_shallow()`, closed two commits
earlier as `UX-776`, tests whether a boundary's parent **object** is
absent; on this truncation nothing was deleted, so it read `False` on
a repository git had already stopped walking.

That is three proxies in a row for one question — the marker's
existence, then object presence — each committed as the fix for the
last. `is_shallow()` now asks whether a commit in `.git/shallow` is an
ancestor of `HEAD`, which is the traversal itself.

The workflow clause reads **jobs**, not the file: `agent-config`
checks out at the default depth and the same flag deepens there, so a
grep would red on a correct line. A second clause fails if that
distinction ever stops existing.

## What was not done

`UX-782` is filed and open. The register's population still comes from
commit subjects reachable from `HEAD`, and reachability is a property
of the clone — 71 rounds from `git log` against 63 from the documents
and ledger, which are identical in every checkout. Closing it means
deciding whether the dates move onto the documents, and that trades a
clone-dependent answer for a tautological guard unless something else
is built to fail. It did not belong inside a CI fix.

`UX-774`, `UX-775` and `UX-777`-`UX-780` remain open from round 107's
review.

One derived figure moved in a way worth naming rather than just
rewriting. `CLAUDE.md`'s shape advisory now reads 261k judgement
against 256k bounded, over 27 of 39 runs; last round it was 242k
against 256k over 24 of 36. The sentence's point — that the two shapes
cost about the same, so the label is not buying what it claims — still
holds, but the sign flipped, and a reader who remembers the old figure
should know it was four runs of drift and not a correction.

`tests/tiers.py` lost `UX-773`'s new file from `MEDIUM`. The track
placed it there on a class argument (it boots a real Chrome), and the
tier guard reads measured duration, which is 0.7s — under the 1.0s
floor. The rule in this repository is the duration, so the duration
decides; if CI records it slower the drift machinery moves it back,
which is what that machinery is for.

## Agents

Five runs — three `implementer`, two `verifier`, all on `sonnet`.
`UX-781` is the session's own, not a track: it is the judgement about
what CI's own step list meant.

| | |
|---|---|
| implementer | 3 tracks; `UX-771` amended before merging, `UX-772` and `UX-773` merged as they landed |
| verifier | 2 runs; one MERGE-with-a-named-fix (`UX-771`), one HOLD (`UX-772`) |

Both verifier findings changed what shipped. `UX-771`'s: a section id
matched inside a longer one, fixed with a lookbehind and a fourth
mutation. `UX-772`'s is the more expensive one — the track's first
pass filtered its population on `document_date() is not None`, which
skips exactly the documents the row was filed about. Four rounds were
passing silently. The population reds on an unwaived `None` now.

`UX-773` merged without a verifier and its own guard then reddened in
this round's gate. That is the cost of the missing run, and it is
recorded here rather than in the row: the standing rule is a verifier
per merged track, and this round ran two for three.
