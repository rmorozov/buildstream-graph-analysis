# Audit round 14: the polish verified, and the docs read as a stranger

Run on 2026-08-19, same retained environment as rounds 10-13. Round
13's polish filings (UX-125..UX-133, plus the sibling's own UX-134)
landed in seven commits; this round verified them hands-on and ran the
round's assigned lens — a fresh-eyes read of the entire user-facing
documentation corpus (3,094 lines across eight documents) asking one
question: is it simple, concise and consistent?

## The polish, verified as a user

The centerpiece ran exactly as designed. On a fresh copy of
`examples/06`, with **zero user-invented paths**:

```text
$ bga snapshot -- bst --builders 4 --max-jobs 4 build all.bst
Capturing into <project>/.bga/runs/20260819T185549Z
This is the first snapshot of this project - make your change and run
the same command again, and the comparison against it is automatic.
$ cp optimized/elements/lib-*.bst elements/    # the macro fix
$ bga snapshot -- bst --builders 4 --max-jobs 4 build all.bst
Verdict: IMPROVED  (total duration -10.99s, -25.8%, 42.60s -> 31.61s)
```

`bga doctor` probes rather than checks presence (the bwrap probe is a
real sandboxed command; the plugin diagnosis distinguishes
missing-package from undeclared-in-project); `bga cache-logs .` now
takes the project you have and bare invocation lists the tree;
`@last`/`@prev` resolve everywhere in `cli.py` and fail outside a
project with a named error and exit 2. `make test` with live bst:
**1689 passed, 0 failed**. Verification discipline this round was the
best yet — UX-129 not only fixed its own headline but *corrected round
13's fdsdk-gap finding* against five published refs (the "+11 minute
contradiction" was a comparison against the fastest cell of a 901.8s
spread), UX-131's status guard caught its own author within the hour,
and UX-130's falsification table genuinely falsified the old test.

## The findings (UX-140..UX-145)

The spine produced its third round of High findings, now concentrated
in the *fallback* paths of an otherwise-sound SEIZE rewrite:

- **UX-140** — when SEIZE is unavailable the spine survives as a
  wrapper returning `128+WTERMSIG`: the exact `WIFSIGNALED`-vs-
  `WIFEXITED` confusion its own file documents as wrong, on the one
  branch every no-ptrace environment takes, with no seam and no test.
- **UX-141** — UX-130 deleted the `initial` restart site UX-128 had
  guarded; both `[initial]` failure-injection tests now pass
  vacuously (one inflating the bst tier pin), while the new `attach`
  site — the restart that runs once per process, ~127k times on fdsdk
  — has no coverage at all.
- **UX-142** — `bga doctor` hardcodes `all.bst`, so the flagship
  preflight false-FAILs essentially every real project, freedesktop-sdk
  included; it passes CI because all nine examples ship one — a
  fixture convention read back as a world fact.
- **UX-143/144/145** — the degrade path resumes group-stopped
  tracees; the annotation convention proved too narrow for its own
  worked example within one range (UX-130 deleted UX-118's mechanism,
  unannotated); and snapshot's sticky flags apply silently.

## The docs, read as a stranger (UX-135..UX-139)

The corpus is accurate — fourteen rounds of enforcement made it so —
and it is **organized by accretion**: each feature shipped with its
own section, and nobody's job was ever to re-teach the old ones.
Measured:

- Journey A's reader types their first command on *their* project
  ~2,100 words into the README, behind three fixture demos and someone
  else's build (`UX-135`).
- `bga baseline` appears **zero times** in the two most-read docs,
  which still teach its superseded three-flag assembly exclusively;
  two guides print correlate output the tool no longer produces
  (`UX-136` — each claim verified by grep this round).
- Eleven duplicate clusters, three already internally drifted,
  including the same lesson taught with two different noise figures
  (`UX-137`).
- "Sandbox tax" and "toll" alternate mid-paragraph; "cold" means two
  unrelated things in one reference doc (`UX-138`).
- Journey B has no page — the CI owner assembles gates, comment,
  baseline and workflow from four documents — and two files listed as
  "guides that tell you what to type" are a retired-era transcript and
  a case study (`UX-139`).

A tight pass reaches ~2,250 lines from 3,094 with every cut a
relocation, not a deletion of evidence.

## Standing

The MVP verdict stands and the loop is now *pleasant*: doctor →
snapshot → snapshot is the two-command story the project wanted, and
it works as measured above. The remaining post-MVP arc is exactly the
two threads this round filed — make the docs as simple as the tool
just became (`UX-135`..`UX-139`), and make the spine's failure paths
as honest as its data (`UX-140`..`UX-143`). The process observation of
the round: the corpus's *accuracy* is enforced and held; its *shape*
had no owner until now, and shape is what a new user meets first.
