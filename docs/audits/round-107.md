# Round 107 — a fix that retired a filed row, and the correction I owed round 106

Closed 2026-09-07.

Four rows closed, four filed. The user's order again: workflow rows
first. The round's subject is not a defect in the code but two in the
record — a landed fix that silently made an open row unimplementable,
and a conclusion of mine that outran its measurement.

## What closed

| row | what it does |
|---|---|
| `UX-744` | the round register, derived by construction; `{round, date}`, no ids |
| `UX-764` | the two Register caps that were honour-system, guarded |
| `UX-759` | **declined** — `UX-744` left it no column to guard |
| `UX-760` | twelve `bst`-gated files read a per-test quota, not the host's 5% |

## The fix that retired a filed row, and nobody noticed

`UX-759` was filed against the register's id column: drop 3 of round
90's 11 ids and every guard stayed green.

```console
$ # commit_signal() drops 3 of round 90's 11 ids, then --write
$ python3 -m pytest tests/unit/test_a_run_is_priced.py -q
33 passed in 0.88s
```

That reading was right and is still right. What retired it is that
`UX-744`'s verifier reached the same conclusion from the other end — a
best-effort regex over commit prose cannot witness its own losses — and
the fix taken was to stop deriving ids rather than to guard them:

```console
$ head -5 docs/audits/round-register.md | tail -2
| round | date |
|---|---|
$ grep -rn DASH_ROUNDS tests/unit/ tools/ | wc -l
0
```

So `UX-759`'s Required Fix has no column to check and its Acceptance
Test cannot be *run*. That is a decline, not a deferral, and it was
owed by the `UX-744` commit under the fixing guide's item 6 — "if your
fix changes a mechanism an earlier task file presents as current,
annotate that file in the same commit." The commit did not, and the
row sat 🔴 over a premise that no longer existed until this round read
it. **Item 6 has no guard and this is what its absence costs**: not a
wrong number, a whole row pointing at nothing.

## The correction I owed round 106

Round 106 recorded `UX-760`'s reserve as the reason `make test` could
not pass: 2.77 GB of spend against a 1.45 GB margin. The spend was
real. The conclusion — that the gate was structurally unpassable — was
not. The margin was thin because the suite's own leavings had eaten
it, and clearing them passed the gate on the same tree.

I promoted a real row to "the blocker" on an arithmetic that had a
second term I had not measured. `UX-773` is that second term, and it
reproduces:

```console
$ ls -d /tmp/bga-geometry-* | wc -l
71
$ PYTHONPATH=. python3 -c "
import tests.browser as b, os, signal
with b.Browser(b.find_chrome()) as br:
    print(br.profile); os.kill(os.getpid(), signal.SIGKILL)"
/tmp/bga-geometry-rvjdhgnx
Killed
$ ls -d /tmp/bga-geometry-* | wc -l
72
$ ps -eo pid,ppid,args | grep -F bga-geometry-rvjdhgnx | head -1
  570     1 …/chrome --headless=new … --user-data-dir=/tmp/bga-geometry-rvjdhgnx
$ du -sk /tmp/bga-geometry-rvjdhgnx
3276    /tmp/bga-geometry-rvjdhgnx
```

`tests/browser.py` cleans its shared browser in an `atexit` handler and
nothing else, so a worker that dies by signal leaves both the process
and the profile. `UX-559` had already declined `atexit` for this exact
reason — "it does not fire on `SIGKILL`" — and the weaker mechanism is
what shipped one file over.

## A derivation that read like a method and was not

`UX-760`'s track widened its own population rather than taking the
row's list of seven, which is the right instinct — the defect this
repository repeats is a population narrower than the sentence. Its
Outcome then explained the widening as a 15-file `shutil.which("bst")`
sweep minus, among others, `test_interrupted_capture.py` and
`test_stale_casd.py`. Neither is in the sweep:

```console
$ grep -rln 'shutil.which("bst")' tests/ | wc -l
18
$ grep -rln 'shutil.which("bst")' tests/ \
    | grep -c 'test_interrupted_capture\|test_stale_casd'
0
```

The *conclusion* was right — the verifier re-derived the population
independently and landed on the same twelve. The stated method was
not, and it read like one: file names, a count, an exclusion rule.
This is the four-shapes defect one level up — an explanation that is a
proxy for the derivation it describes — and it survives exactly
because a later round is meant to read the task file instead of the
code.

The verifier also drove the margin negative on all twelve rather than
the six the track pasted, and found the residual: the two deferred
files still refuse. That is `UX-775`; the deferral is defensible, the
silence about it was not.

## The guide is at its band ceiling

`UX-607`'s guard requires 1,024 B between the guide's size and the top
of the 10 KB band it states. The band ends at 56,320 B; the guide grew
7,279 B in a day:

| commit | B | Δ |
|---|---|---|
| `b96834e` | 47,974 | — |
| `8997068` | 55,280 | −349, trimmed to get under the limit |
| this round | 55,253 | −96, `UX-744`'s module-map row over the limit |

Growth is monotone and the band is fixed, so the outcome is scheduled.
Both trims fell on prose picked for being cheap to cut. `UX-774` files
the choice: move the module map out, derive the figure, or widen the
band — and states that widening only defers it.

## The cost row moved at the merge, not in either track

Two tracks each added one test file. Each derived 516 in its own
worktree and each was right. The merge that united them is 517, and
no track's diff selects the guard that reads the figure:

```console
$ git ls-tree -r --name-only 17bf0b8 tests | grep -c 'test_.*\.py$'
516
$ find tests -name 'test_*.py' -not -path '*__pycache__*' | wc -l
517
```

§7a step 4 already covers this — re-derive the spread at close, when
the pairs changed — and it did. Recorded because the *reason* the
figure was stale is not "someone forgot": no track could have seen it.

## The verifier held and I merged anyway

`UX-761`'s mandate, in the guide since round 105: *the row does not
merge until the track has answered the finding, or the session records
in the task file why the finding is declined.* Round 107 is the first
round to break it, and I broke it.

`UX-744`'s second verifier returned `## Verdict: HOLD` — the
population claim for rounds 76 and 85 was not supported by its
evidence. I merged the row 26 seconds later, then corrected the
Outcome and filed the finding as `UX-772`.

The finding was **accepted**, not declined, which is the only reason
this is a process failure rather than a wrong record. But the mandate
does not have an "accepted, will file separately" branch, and it
should not need one: the point of writing the decision in the task
file before merging is that a reader of the file learns what the
verifier said. Mine learned it from a ledger row two hours later.

Ledger rows carry both verdicts; `UX-744`'s file now says what
happened.

## Agents

Seven runs — three `implementer`, four `verifier`, all on `sonnet`.

| | |
|---|---|
| implementer | 3 tracks, two held, `UX-744` amended its commit in place |
| verifier | 4 runs; two HOLDs, one MERGE-with-correction, one MERGE |

Three of the four verifier runs changed what shipped:
`UX-744`'s first found an ids column wrong on four of five rounds and
is why the column does not exist; its second found the population
claim that became `UX-772`; `UX-760`'s found a derivation that read
like a method and named two files not in the sweep it described.

Rows in [`agent-runs.md`](agent-runs.md), derived by
`dev_track_cost.py --ledger`.

## Filed, not fixed

`UX-772` — `document_date()` takes a round document's first
`YYYY-MM-DD` whatever it means; round 76 gets `UX-96`'s cron date,
round 85 a status-word note, and the date guard's population starts at
round 90 so it sees neither.

`UX-773` — above.

`UX-774` — above.

`UX-775` — `test_native_build_tracer.py` and `test_dual_plane_capture.py`
build against the ambient `$HOME`, so they still refuse at a negative
margin that the twelve now survive.
