# Round 76 — the eight rows left open

Input: everything `README.md` still lists open after round 75 —
`UX-92`, `UX-96`, `UX-500`, `UX-507`, `UX-510`..`UX-513`. Two of them
are the backlog's oldest rows, both parked on evidence a date would
supply, and the date has passed: `UX-96`'s monthly cold cron first fires
`2026-09-01`, and `UX-92`'s deferral was last re-checked at n=6 on
`2026-08-25`. The round opens by re-running both rather than reading
what the last round wrote about them.

## Decomposition

Derived per the `decompose` skill. One row per item; the four shared
files (`README.md`, `closed.md`, `tiers.py`, `ci_reference.json`) are
the orchestrator's, at the end.

| item | surfaces | guards (input classes) | track |
|---|---|---|---|
| `UX-92` | task file only (a re-check, not a mechanism) | none — the evidence is the published refs | first, alone; it is a measurement |
| `UX-96` | `tools/bst_baseline_set.py` (option added, message) · `docs/guides/ci-comment.md` (§3.10) | `test_baseline_set.py` (mismatch on a ref-name field · on a field the ref name cannot carry · no mismatch) | first, alone — the same measurement run |
| `UX-512` | `tests/unit/test_the_context_map_is_the_tree.py` | itself (artifact exemption · source exemption · a source exemption that really is missing) | parallel |
| `UX-513` | `tests/unit/test_a_slow_file_says_which_file.py` | itself (clean tree · `tiers.py` uncommitted · a one-module diff) | parallel |
| `UX-511` | `docs/guides/real-project.md` | `test_docs_links_and_commands.py` (undated retired reading · dated block) | parallel |
| `UX-507` | 223 task files' `**Topic:**` header | `test_docs_links_and_commands.py` (`TOPIC_UNKNOWN` gone) · `dev_close_task.py --check` | last — it rewrites 223 files and conflicts with any row that moves |
| `UX-510` | `.claude/agents/implementer.md` · `decompose` skill §3 | `test_the_agent_configuration_holds.py` (the brief states its base) | parallel |
| `UX-500` | `docs/audits/round-76.md` (this file) | none | spans the round; Regime A round 2 of 3 |

**gap:** `UX-500` still cannot close. Round 75 was Regime A round 1 and
this is round 2; the row stays open by design, and this file records the
round's figures so round 3 has three samples to read rather than one.

**gate:** one PR, opened before the first commit (`UX-426`, `verify`
§7), one `make test` here.

**Two departures from the table, both decided mid-round.**
`UX-514` and `UX-515` were filed while working `UX-92` and `UX-513` and
are not in it — `UX-515` had to be *fixed* here rather than filed and
left, because it is red on `main`. And `UX-507` ran as an `implementer`
track rather than last-and-serially: it is one surface (224 task files)
and nothing else in the round touches it, and `UX-510`'s acceptance
test asks for a track launched against a brief that names its base.
Running the two together discharges that clause on real work rather
than on a made-up errand.

## The two parked rows, re-run

Both were parked on the same thing — a published capture history that
has since grown by three refs (`33302016575` incremental,
`33490577715` cold, and `32615919649` was already counted).

`git ls-remote origin 'refs/heads/captures/*'`, 2026-09-02:

```text
captures/fdsdk/953683fb-cold-b4j4-32133112003            dispatched by a human
captures/fdsdk/953683fb-cold-b4j4-33490577715            the monthly cron
captures/fdsdk/953683fb-incremental-b4j4-32064333551
captures/fdsdk/953683fb-incremental-b4j4-32113933158
captures/fdsdk/953683fb-incremental-b4j4-32122941503
captures/fdsdk/953683fb-incremental-b4j4-32177690506
captures/fdsdk/953683fb-incremental-b4j4-32223468993
captures/fdsdk/953683fb-incremental-b4j4-32615919649     the weekly cron
captures/fdsdk/953683fb-incremental-b4j4-33302016575     the weekly cron
```

Nine captures, **one commit**. That single fact is `UX-92`'s whole
answer and `UX-96`'s second clause at once: the schedule now produces
captures unattended, and it produces them of the same commit, because
what it re-captures is a pinned ref rather than a moving branch.

## What the round found that it was not looking for

Three of the seven items were re-checks or small guard fixes, and each
turned over something the filing did not name.

**`UX-96`'s acceptance was red.** The helper had not been run against
the published refs since round 11, and the population drifted under it:
one of the seven incrementals is a spine capture, `bga baseline` refuses
the set correctly, and the remedy it named — narrow the glob — cannot be
carried out, because the ref name carries four of the seven homogeneous
fields and `trace_spine` is not one of them.

**`main` was red, from a commit CI pushed itself.** `96970dc`,
the reference-adopt step, wrote the `samples` key `UX-496` introduced,
and `--record` carries the committed reference's readings — so
record-then-compare stopped being the identity a clause had asserted
since `UX-420`. Filed and closed as `UX-515`. Nothing in the tool was
wrong; a clause was standing on a property the tool no longer had, one
axis further out than `UX-512` and `UX-513`: those read the working
tree, this read a file CI rewrites.

**`UX-92`'s deferral had no end.** Four re-checks — n=3, 5, 6, 7 — each
closed on "no capture of a different commit yet", implying the next one
might supply it. The workflow pins `fdsdk_ref` and `schedule:` cannot
supply inputs, so no scheduled run ever will. `UX-514` turns the wait
into a decision.

That is three defects of one shape in one round: **a claim that was true
when it was written and is now held up by something outside the code**.
`UX-512` (bytecode on disk), `UX-513` (the developer's uncommitted
diff), `UX-515` (a file CI rewrites) and `UX-92`'s deferral (a schedule
that cannot change) are the same failure at four distances.

## The round, closed

Seven rows closed — `UX-96`, `UX-507`, `UX-510`, `UX-511`, `UX-512`,
`UX-513`, `UX-515` — one re-checked and left open (`UX-92`), and four
filed (`UX-514`, `UX-515`, `UX-516`, `UX-517`; `UX-515` was filed and
closed in the same round because it is red on `main`).

```text
make test    5867 passed, 27 skipped, 475.88s (0:07:55)
make lint    clean
```

The one failure on the first full run was the cadence guard —
26 rows closed since review 10 against a bound of 25 — which is the
repository asking for a review rather than a defect. Review 11 is in
`architecture-review.md`; it filed `UX-516` and `UX-517` and produced
no code, per that document's rule.

## `UX-500`, Regime A round 2

| | round 75 | round 76 |
|---|---|---|
| items closed | 15 | 7 |
| tracks in parallel | 3 | 1 |
| commits | 20 | 10 |
| commits per closed item | 1.33 | 1.43 |
| track merges | 3 picks, 1 conflict | 1 pick, 0 conflicts |
| defects the regime produced | 2 | 0 |
| defects only CI could catch | 3 | 0 so far |

The parallel track cost **two** commits for one item, not one: the pick,
and then a commit the orchestrator had to add because `UX-507`'s
acceptance named a guard that does not discriminate. That is not a track
defect — the orchestrator would have found the same thing working
serially — but it is where the 1.43 comes from, and a round with one
track and one such follow-up is not evidence that parallel is dearer
than serial. Round 3 decides.

What is new and does not fit the table: **`main` was red at the start of
this round from a commit no human wrote** (`UX-515`). The batch gate as
`UX-500` frames it — one PR, one merge, one `make test` — assumes the
merge base is green. It was not, and only running the suite here found
it. Whatever round 3 concludes about the batch gate, it has to say what
happens when CI's own commit is the thing that broke.
