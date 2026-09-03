# Architecture and documentation review

A round type, and its log. Feature audits happen here on a cadence —
twenty-eight rounds of them — and documentation review did not, which
is why one drifted a whole axis and the other did not (`UX-241`).

## What a review is

| | |
|---|---|
| **input** | everything that landed since the last row in the log below |
| **output** | filings, in `docs/backlog/scenarios/` — and this document's next row |
| **produces no code** | a review that fixes what it finds is a fix session wearing a review's name, and stops being able to see the next thing |
| **done when** | every item on the checklist has been answered with a measurement or a filing |

The stream table in
[`../contributing/fixing-guide.md`](../contributing/fixing-guide.md)
§6a carries it beside the other six.

## The checklist

Per architecture chapter, per guide:

1. **Does the code still do what it says?** Not "is it plausible" —
   open the module the chapter names and check the mechanism.
2. **Does every published contract have a home?**
   `test_the_documents_keep_up_with_the_contracts.py` guards the
   mechanical half (`UX-233`); the review asks whether the *prose*
   around each one is still true.
3. **Is any figure invalidated?** `git grep` the number. A figure a
   later round moved and an earlier document still quotes is the defect
   `UX-132` named.
4. **What shipped since the last review that no document names?** The
   inventories are `bga --help`, `schemas.names()`, and the closed rows
   added since the last log entry.
5. **Does each document's own "last updated" claim match reality?**
   `git log -1 --date=short -- <file>` against what the file says.

The spec's Part text is out of scope: it is ground truth, and a review
that finds it wrong files against it rather than editing it.

## The cadence, and why it is measured in closed rows

The trigger is a number, not a memory:
`tests/unit/test_the_review_has_a_cadence.py` reddens when more than
**25 scenarios** have closed since the last row below.

Closed rows rather than commits, because a commit is not a unit of
change here — one round is anywhere from one to nine of them — and
because the count is in the tree, so the guard needs no git and gives
the same answer on every machine. 25 is chosen against the drift that
was actually missed: the viewer axis ran from `UX-193` to `UX-226`, 34
closed rows, with nothing in the process to notice. A bound below that
would have caught it; a bound at it would only just have.

## The log

<!-- UX-332: the commit column is gone. It cited the branch commit each
     review ran against, and this repository merges pull requests - so a
     hash that names a branch tip is only as durable as the branch.
     Measured on the four rows it carried: three of the four are **not
     reachable from `origin/main`**, so a reader with an ordinary clone
     cannot resolve them, and the one that is (`b17d741`) is reachable
     by luck of which pull request kept its commits rather than by
     anything the column guaranteed.

     "Closed rows at review" is the merge-stable identity and was
     already here: a count in the tree, what the cadence guard measures
     distance in, and immune to any merge strategy. -->

| review | date | closed rows at review | findings |
|---|---|---|---|
| 1 | 2026-08-23 | 237 | `UX-245`, `UX-246`, `UX-247` |
| 2 | 2026-08-24 | 263 | `UX-273`, `UX-274` |
| 3 | 2026-08-25 | 290 | `UX-294`, `UX-295` |
| 4 | 2026-08-26 | 318 | `UX-322`, `UX-323` |
| 5 | 2026-08-28 | 346 | `UX-352`, `UX-353` |
| 6 | 2026-08-29 | 379 | `UX-386`, `UX-387` |
| 7 | 2026-08-29 | 406 | `UX-416`, `UX-417` |
| 8 | 2026-08-30 | 432 | `UX-446`, `UX-447` |
| 9 | 2026-09-01 | 458 | `UX-471`, `UX-472` |
| 10 | 2026-09-01 | 484 | `UX-492`, `UX-493` |
| 11 | 2026-09-02 | 510 | `UX-516`, `UX-517` |
| 12 | 2026-09-02 | 537 | `UX-548`, `UX-549`, `UX-550`, `UX-551`, `UX-552` |
| 13 | 2026-09-03 | 560 | `UX-563`..`UX-586` — every document group read against the tree; [`round-82.md`](round-82.md) |
| 14 | 2026-09-03 | 587 | four filings — the registry row `UX-565` falsified, two hard gates no document names, a Python floor in no prose, and a verification-log clause read against the entry below it; [`round-83.md`](round-83.md) |

### Review 11 — 2026-09-02

Twenty-six rows since review 10, which is what tripped the cadence —
round 75's tail and all of round 76. Run against `architecture.md`, the
three guides, and the eight published contracts.

**1. Does the code still do what it says?** The window shipped one CLI
change: `bga baseline --exclude` (`UX-96`). `architecture.md:56`
describes the command as "refusing a set whose captures are not
comparable", which is still what it does — the table carries one line
per command, not per option, so it is not wrong. The chapters this
window touched are `capture-workflow.md`'s cold-mode paragraph, which
`UX-96` corrected from the same measurement that falsified it, and
`real-project.md`'s Step 3, rewritten by `UX-511`.

**2. Does every published contract have a home?** Eight schema ids
against both inventories:

```text
analyze/v4   architecture=4 spec=4      store/v1            architecture=1 spec=2
blast/v2     architecture=1 spec=2      store-aggregate/v1  architecture=1 spec=2
compare/v2   architecture=1 spec=2      sweep/v1            architecture=1 spec=2
correlate/v2 architecture=1 spec=2      whatif/v1           architecture=5 spec=2
```

None is zero, and no contract version moved this window.

**3. Is any figure invalidated?** One, and it is this round's own doing.
`UX-507` emptied the `unclassified` bucket, and `UX-501`'s Outcome
states "**223 of the 489** closed rows predate the header" as a fact
about the tree. Filed as `UX-517`. `git grep -n '223 ' -- docs README.md`
returns one other hit and it is the task id `UX-223`.

**4. What shipped since the last review that no document names?**
`--exclude` reaches `docs/design/capture-workflow.md` and nothing else.
That document's own header says it is *not* the usage guide and points
a CI owner at `ci-comment.md` — which teaches a `bga baseline` block
that exits 6 on this repository's published refs and offers no next
line. Filed as `UX-516`.

**5. Does each document's own "last updated" claim match reality?** No
document carries one:

```text
architecture.md      claims: none   git: 2026-09-01
ci-comment.md        claims: none   git: 2026-08-28
real-project.md      claims: none   git: 2026-09-02
capture-workflow.md  claims: none   git: 2026-09-02
fixing-guide.md      claims: none   git: 2026-09-01
README.md            claims: none   git: 2026-09-02
```

Nothing to contradict, which is the answer `UX-492` and `UX-511` chose
deliberately: the blocks carry a capture's date rather than the file's.

**Produced no code**, per this document's own rule. Both findings are
filings.

### Review 3 — 2026-08-25

Twenty-seven rows closed since review 2, which is what tripped the
cadence. Run against `docs/design/architecture.md`, the three guides
and the seven published contracts.

**1. Does the code still do what it says?** The CLI table checked
against `cli.create_parser()`: twelve subcommands, twelve rows, plus
the alias row `UX-67` added — no drift. The viewer section checked
against `bga/viewer/`: the schema-driven claim, the width rule and the
presets are all still what the modules do, and the chapters `UX-286`
added were missing from it and were written in by `UX-247` the same
day.

**2. Does every published contract have a home?**

```text
contract              named in architecture.md   named in a guide
analyze/v2                     4                        2
blast/v1                       1                        1
compare/v1                     1                        1
correlate/v1                   1                        1
store-aggregate/v1             1                        1
store/v1                       1                        1
whatif/v1                      3                        0
```

Six of seven are reachable from a guide. `whatif/v1` is not — the
*command* is documented in two guides and the *contract* in none, so a
consumer holding a payload stamped with it has nowhere to look. Filed
as `UX-295`.

**3. Is any figure invalidated?** One, and it was this round's own:
`UX-285` and `UX-286` recorded their after-measurements against
"macro_micro" when the export measured was the golden
`mixed_task_kinds` fixture. Corrected in place, with a note in `UX-285`
saying so — the two fixtures are different documents and a reader
comparing rounds would have been comparing two runs.

Direction 13's own figures (48 sections, 18.8 and 20.1 screens) are
*not* invalidated: they are dated round-38 measurements and the round
that moved them is named beside them.

**4. What shipped since the last review that no document names?** The
inventories: `bga --help` (twelve subcommands, nineteen aliases),
`schemas.names()` (seven contracts) and the twenty-seven closed rows.
The commands and contracts are covered. The **modules are not** — the
architecture names `app.js` and `chapters.js` and none of the other
ten viewer modules, including the 2,411-line `views.js` that draws
every section. Filed as `UX-294`.

**5. Does each document's "last updated" claim match reality?**
`architecture.md` claims 2026-08-25 and was last changed 2026-08-25.
It is still the only document making the claim, which is what `UX-247`
recorded — and that clause is now guarded rather than checked by hand,
which is why this review could answer it in one command.

**No code was written in this review.** `UX-294` and `UX-295` are the
output, plus this row.

### Review 1 — 2026-08-23

The first one, run against `docs/design/architecture.md` and the three
live guides. Three findings, each measured:

**The architecture's CLI table is two subcommands behind.** Checked
against `cli.create_parser()`:

```text
subcommands in `bga --help`, absent from "## Real current CLI surface":
  blast    (shipped round 19, UX-172)
  whatif   (shipped round 28, UX-230)
```

`--explain` (`UX-229`) appears nowhere in the document either, although
the provenance mechanism it prints is described. Filed as `UX-245`.

**The end-to-end guide never reaches the command for its own last
step.** `docs/guides/real-project.md` walks capture → read → go inside
→ join → act → gate, and `bga whatif` — which prices the act step — is
named nowhere in it. Filed as `UX-246`.

**The architecture's own Verification Log is stale about itself.** It
says *"Updated 2026-08-18 (after `UX-76`)"*; `git log` says the file
was last written on 2026-08-23, with five commits touching it since
that line was written. A log that does not move when the document does
is worse than no log, because it is read as a claim. Filed as `UX-247`.

**What was checked and found current:** every published schema id
appears in spec Part 32.5 and the architecture inventory (guarded since
`UX-233`); the three planes' chapters match the modules they name; the
33% five-capture noise figure and the band derived from it are the ones
the round-9 audit measured; `docs/guides/cli.md` names every subcommand
and every `tools/` alias. `optimization-walkthrough.md` names almost no
command, which is correct — it is a tombstone pointing at
`real-project.md` (`UX-139`), not a guide.

### Review 2 — 2026-08-24

Twenty-six rows closed since review 1 — `UX-248`..`UX-272`, the
contract-versioning round, the first recorded release, and rounds 34-36
of the viewer axis. Run against `docs/design/architecture.md` and
`docs/contributing/fixing-guide.md`. Two findings, and one recurrence.

**The rule that draws every nested value is written in one task file.**
Round 36 replaced 34 `<details>object</details>` cells with a rule that
chooses inline / bounded table / fold by **width, not depth**, and it
now governs every object- or array-valued field in every published
schema. Where a maintainer would find it:

```text
$ git grep -c "width, not depth" -- docs/
docs/backlog/scenarios/UX-0267-...md:1
```

The architecture's viewer chapter describes the *hint* half of
schema-driven rendering in detail — `bga:quantity`, `bga:columns`,
`bga:rail` — and says nothing about what becomes of a field's value, so
a schema author reading the chapter learns that adding a field is free
and does not learn that its shape decides its rendering. Same shape as
`UX-244`. Filed as `UX-273`.

**The context map is guarded on `bga/` and `tools/` and nowhere else.**
`UX-239` regenerated §6 of the fixing guide and gave it a guard;
`_real_modules()` globs two roots, so the **Tests and docs** block has
been unguarded prose ever since, and it has drifted exactly as far as
an unguarded figure does:

```text
map says                                    tree says
tests/unit/  218 files, ~3,100 tests        240 files, 3,327 tests
closed.md    the 233 closed rows            263 closed rows
entries named under tests/:  5              real entries:  12
```

The seven absent entries include both harnesses this axis just built —
`tests/dom_shim.mjs` (`UX-264`) and `tests/cdp.mjs` + `tests/browser.py`
(`UX-257`) — so a session that needs to assert something about the page
is pointed at neither, which is how twenty-five inline shims got
written in the first place. Filed as `UX-274`.

**`UX-247` recurred, wider.** The architecture's Verification Log still
opens *"Updated 2026-08-18 (after `UX-76`)"*; `git log -1 --date=short`
now says `2026-08-24`, with **12** commits touching the file since that
line was written — five at review 1. The finding is unchanged and the
gap grew by six days and seven commits while the item sat open, which
is the argument for its clause 2 (guard the mechanical half) rather
than for re-editing the date by hand a third time.

**Review 1's three findings are all still open** (`UX-245`, `UX-246`,
`UX-247` — all 🔴). A review that files and never closes is a review
that produces a longer list, not a truer document; that is a fact about
this round's ordering rather than a finding, but the next review should
read it as one if it is still true.

**What was checked and found current:** the contracts table names all
nine published schemas and the mechanical half is guarded
(`test_the_documents_keep_up_with_the_contracts.py`, 6 passed); the
`producer` block and the release mechanism (`UX-249`..`UX-252`) reached
`architecture.md`, `docs/guides/cli.md` and
`docs/contributing/release-guide.md`; the viewer chapter's CSP
paragraph is current to `UX-265`, naming the pre-flight, the private-
network header and the style-attribute consequence, which is round 34's
work correctly landed in prose; the `bga/` and `tools/` halves of the
context map pass their guard (7 passed) and gained `contracts.py`,
`producer.py` and `bga_release_notes.py` in the rounds that shipped
them. `UX-245`'s measurement is unchanged — `bga blast` and `bga whatif`
are still the two rows the CLI table lacks, and `--explain` still
appears nowhere — so it needs no re-filing, only doing.

### Review 4 — 2026-08-26

Twenty-eight rows closed since review 3, which is what tripped the
cadence — and it tripped mid-round, on the closure of `UX-315`, which
is the mechanism working: the trigger is a number in the tree rather
than a memory.

**1. Does the code still do what it says?** The CLI table checked
against the parser and against `bga --help`, by running every command
the table names and every command the tool has:

```text
rows in the architecture's table   18   all name a real command
commands that work                 20
missing from the table              2   bga view, bga timeline
```

Filed as `UX-322`. It is a recurrence of `UX-245` — the same table, two
commands behind, three reviews later — and this time the two missing
are `bga view`, the entry point for the whole viewer axis from `UX-193`
to `UX-320`, and `bga timeline`, `UX-298`'s native Perfetto emitter.
Both are named in the document's prose and absent from the list built
to be read as a list. The filing asks for a guard as well as the rows,
because a hand-maintained table against a parser that knows the answer
will drift a fourth time.

**2. Does every published contract have a home?**

```text
contract              architecture   guides
analyze/v2                      4        2
blast/v1                        1        1
compare/v1                      1        1
correlate/v1                    1        1
store-aggregate/v1              1        1
store/v1                        1        1
whatif/v1                       5        1
```

Seven of seven, both columns. Review 3's one finding here — `whatif/v1`
documented as a command and not as a contract — is closed by `UX-295`,
and this is the check confirming it.

**3. Is any figure invalidated?** One, and it is the round-41 claim
this round spent two items on. `docs/audits/round-41.md` line 86 still
states, unqualified, that "175 KB of the 196 KB page is commented
JavaScript, because `--export` inlines modules verbatim". Both halves
are false: `_uncommented` has stripped comments since `UX-205`,
`UX-320` measured the page at 89% code, and `UX-307` this round
removed what was actually left — 153 B. Nothing in the file marks it.
Filed as `UX-323`.

It is not an inert error. It is the stated reason the `UX-287` ratio
threshold went 4x → 3.5x, and the threshold has since moved again to
3.3x — twice restated against a misattributed cause. `architecture.md`
was checked and is **not** affected: it reports the falsification
rather than repeating the claim.

**4. What shipped since the last review that no document names?** The
inventories: `bga --help` (20 commands), `schemas.names()` (7
contracts) and the twenty-eight closed rows. The contracts are
covered; the commands are `UX-322`. The viewer module map, which
review 3 filed as `UX-294`, gained `tablefocus.js` in round 44 and it
was written into the map in the same round — so the guard `UX-294`
produced is holding, which is what a closed finding should look like
one review later.

**5. Does each document's "last updated" claim match reality?**
`architecture.md`'s Verification Log carries a round-44 entry dated
2026-08-26 and the file was last changed 2026-08-26. It remains the
only document making the claim, and `UX-247`'s guard now checks it
rather than a reviewer doing so by hand — this review confirmed the
guard is in the suite and green rather than re-deriving its answer.

**No code was produced by this review**, per the rule above. The two
findings are filings.

### Review 6 — 2026-08-29

Thirty-three rows closed since review 5 — the furthest past the bound
of any review so far, because round 61 landed eight items before the
guard was answered. Run at 379 closed rows, against `bga/`, `tools/`,
the architecture document, the specification's Part 32, the docs index
and the four guides.

**Checklist item 5 — currency claims.** Clean. Neither
`docs/design/architecture.md`'s `2026-08-16` nor `docs/README.md`'s
`2026-08-15` is a "last updated" claim: the first dates an audit round
and the second a closed tracker. No document asserts a currency it
does not have.

**Checklist item 3 — invalidated figures.** Clean, and one moved
correctly. `git grep` on the figures round 61 changed — the two export
bounds and the contract count — found each restated where it lives and
quoted nowhere else. `docs/README.md`'s "Eighteen ids" was the one
count in prose and moved to twenty with the table it counts, held by
`test_the_count_matches_the_inventory`.

**Checklist item 4 — what shipped that no document names.** Four
capabilities: `resource_pressure` and `process_outcomes` (`UX-379`,
`UX-378`), the redundancy findings cap (`UX-375`) and the census's
unassessable count (`UX-376`). Three are the page half of `UX-383`,
already filed. The fourth is a documentation gap of the same shape and
is folded into `UX-386` below, because the sentence that would have to
name them is the sentence that finding is about.

**Checklist item 2 — is the prose around each contract still true?**
One finding, `UX-386`. Two documents call `plane2/v2` "per-element
reductions"; measured on the committed fixture, 3 of its 24 top-level
keys are element-keyed. The sentence has been wrong since `UX-297`
retired the per-process record list — "and nothing else" was about what
was removed and reads as a claim about the shape of what is left — and
`UX-378`/`UX-379` moved the ratio further in the round that found it.

**Checklist item 1 — does the code still do what it says?** One
finding, `UX-387`. `tools/dev_close_task.py --check` is the fast
command a contributor runs before committing a closure and it does not
check the property `UX-131` created it for: reproduced deliberately,
a tree with a task file at 🔴 and its index row at 🟢 gets
`0 problem(s)` from `--check` and a failure from the suite. Round 61
hit it live on `UX-382`.

**What this review did not do, and did.** A review produces no code.
It produced none. But the full-suite run it started with was red on six
clauses — all of them round 61's own, and all of them invisible to the
targeted runs each item had been verified with — and those were fixed
in their own commit before the review's own findings were filed. The
distinction the log cares about: the fixes are the round's, the
findings are the review's.

### Review 5 — 2026-08-28

Twenty-eight rows closed since review 4, which is what tripped the
cadence — on `UX-344`'s closure, mid-round again. Run against
`docs/design/architecture.md`, `docs/design/roles.md`, the three
guides, `docs/README.md` and the eight published contracts.

**1. Does the code still do what it says?** The CLI table is now
guarded (`test_the_architecture_names_the_commands.py`, `UX-322`'s
answer to three reviews of the same drift): 21 rows, 21 commands, and
the guard is green in the suite rather than re-derived here. The
viewer chapter was read against `bga/viewer/` after the round that
moved most of it, and one sentence does not survive the module:

```text
$ node -e 'import("./bga/viewer/chapters.js").then(
      m => console.log(m.CHAPTERS.length, m.CHAPTERS.map(c => c.id).join(",")))'
8 decide,change,compare,time,machine,elements,believe,run

architecture.md:718   groups them into seven chapters
```

Filed as `UX-352`. It has been eight since `3c4a96b`, the commit that
introduced the module and wrote the sentence, so this is not drift —
the number was never true, and three reviews read past it. The filing
asks for a guard rather than a correction, on the same argument
`UX-322` made: a count in prose is read by nothing but a human.

**2. Does every published contract have a home?**

```text
contract               architecture   guides
analyze/v4                        4       12
blast/v2                          1        2
compare/v2                        1        1
correlate/v2                      1        3
store-aggregate/v1                1        1
store/v1                          1        2
sweep/v1                          1        1
whatif/v1                         5        2
```

Eight of eight, both columns — `sweep/v1` is new since review 4
(`UX-339`) and arrived documented. The prose check found the other
finding: `docs/design/roles.md`'s "bga today" column serves role R2
with `correlate/v1`, which `UX-341` superseded in round 51. Every
other document says v2, or says v1 is read-never-written; this one is
present tense and points a reader at a payload nothing writes. Filed
as `UX-353`, with the guard's population widened to the one design
document that names a contract id — which is why the mechanical half
missed it.

**3. Is any figure invalidated?** Two candidates, one of them a
finding. `architecture.md`'s chapter bullet also carries "forty-eight
sections averaging 0.24 screens" and "18.51 screens to 18.10", which
`UX-347` moved a long way — but both are attributed to `UX-286`,
round 39, and a dated measurement a later round moved is a record.
The chapter count in the same bullet is not dated and is `UX-352`.

The second candidate is this document. Review 4's own text says the
page/data ratio threshold "has since moved again to 3.3x"; it is
**2.8x** now, moved by `UX-342`'s reclassification and this round's
`UX-348`. That sentence is a dated row in a log rather than a claim
about today, so it is not re-filed — but the current number is written
here, where the next review will read it, and
`tests/unit/test_the_report_you_can_attach.py` carries the split that
justifies it round by round.

**4. What shipped since the last review that no document names?** The
inventories: `schemas.names()` (8 contracts, all homed, see above),
the architecture's command table (guarded), and the twenty-eight
closed rows. `analyze` went to **v4** this round (`UX-344`) and the
version reached `architecture.md`'s contracts table, the spec's Part
32 registry, `docs/README.md`, `CHANGELOG.md` and two guides in the
same round. The viewer module map and the `bga/`/`tools/` context map
pass their guards (37 passed), and `bga/viewer/` gained no module this
round — the three items moved code inside the ones that exist.

**5. Does each document's "last updated" claim match reality?**
`architecture.md`'s Verification Log is still the only document making
the claim; its newest entry reads "Updated 2026-08-28 (after
`UX-344`)" and `git log -1 --date=short` on the file returns
2026-08-28. `UX-247`'s guard checks this, and this review confirmed
the guard is in the suite and green rather than re-deriving it.

**No code was produced by this review**, per the rule above. The two
findings are filings.

## Review 7 — 2026-08-29, at 406 closed rows

Input: the twenty-seven rows closed since review 6 — round 63's tail
(`UX-383`–`UX-387`) and the whole of round 64 (`UX-388`–`UX-410`, plus
`UX-400`, `UX-401`, `UX-402`, `UX-404`). The axis of the round is the
*reader*: what reaches a browser, what a control does, and what a guard
freezes.

**1. Does the code still do what it says?** The two chapters this
round moved under are `The viewer axis (rounds 21-26)` and
`The published contracts`. Opened both against the modules they name.

The viewer chapter's `bga view` bullet describes the server's document
table and says "**two** endpoints take a parameter -
`blast.json?target=` and `whatif.json?elements=`". `tools/bga_view.py`
now has three: `UX-394` added `?run=<stamp>`, which builds and caches
another snapshot's documents on demand. The chapter is not wrong about
the two it names; it is a count that a round moved. Filed as
**`UX-416`**, with the guides that carry the same sentence.

The contracts chapter's `analyze/v4` row survives `UX-407`, which
published `restructuring` into that document: the versioning rule
written three paragraphs below the table says an *addition* does not
bump the version, and the row describes what the contract is for
rather than enumerating its keys. Not filed.

**2. Does every published contract have a home?** Eight printable
contracts, twelve unprintable or superseded, and the mechanical half is
green:

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
8 passed in 0.21s
```

The prose around each was re-read. `plane2/v3`'s row still counts "21
of its 24 top-level blocks answer for the whole run and 3 are keyed by
element uid"; `bga/plane2.py`'s `DESTINATIONS` now declares 25 entries
and `resource_pressure` is declared-and-absent from the committed
fixture by design, so the row's 24 is the number a capture writes and
the two are consistent. Not filed.

**3. Is any figure invalidated?** Yes, and it is the biggest single
drift this cadence has caught. `docs/guides/cli.md`'s `--export`
section says:

> Measured on `examples/06`'s real 46 s two-plane capture: **158 KiB**,
> of which the page is 90,611 B.

Re-measured on a fresh 28 s two-plane capture of the same project,
taken by `UX-402`'s journey guard:

```text
example 06 cold export: total=518,578 B (506 KiB)
  source (modules+css) = 282,247 B
  contract (schemas)   =  81,681 B
  data (payload+trace) = 154,650 B
```

3.2x the total and 3.1x the page — and a third term the sentence has no
word for, the embedded contracts, which `UX-342` split out in the guard
and `UX-404` grew again this round. Filed as **`UX-417`**.

The page/data ratio review 6 recorded as "2.8x" now reads 3.81
(source over data, `macro_micro`) and 15.06 on `golden`, which is the
same story from the other end: the source half grew by six rounds of
viewer work while the golden fixture's data did not. That sentence sits
in a dated log row rather than as a claim about today, so per review
4's own precedent it is not re-filed — the current numbers are written
here, where the next review will read them.

**4. What shipped since the last review that no document names?** The
inventories: `schemas.names()` is eight and all eight are homed (item 2
above); `bga --help` gained no subcommand this round. Of the
twenty-seven closed rows, the capability that reaches no document is
`UX-394`'s run selector — filed above as `UX-416`. Two guards' own
declarations are new and internal (`TERMINAL_ONLY` in `app.js`,
`CONTRACT_RUNS` in the unit census) and are documented where they live,
which is the rule for a mechanism no user meets.

**5. Does each document's "last updated" claim match reality?**
`architecture.md`'s Verification Log is still the only document making
the claim. Its newest entry reads "Updated 2026-08-25 (after
`UX-296`)"; `git log -1 --date=short -- docs/design/architecture.md`
returns **2026-08-29**. The file moved this round without the log
gaining an entry — which `UX-247`'s guard permits, because the guard
asserts the newest *dated* entry is not in the future rather than that
every edit adds one. Recorded here rather than filed: the entries are
re-groundings, not a changelog, and this round re-grounded nothing in
that document.

**No code was produced by this review**, per the rule at the top. Both
findings are filings.

## Review 8 — 2026-08-30, at 432 closed rows

Input: the twenty-six rows closed since review 7 — round 68's tail
(`UX-411`–`UX-420`), round 69 (`UX-421`–`UX-428`, `UX-432`, `UX-439`)
and round 70 so far (`UX-441`, `UX-442`, `UX-431`, `UX-434`, `UX-430`).
Two axes: **the instrument that checks the suite** (the drift gate, its
reference, its log) and **the trace the handoff carries**.

**1. Does the code still do what it says?** The chapters these rounds
moved under are the viewer/Perfetto boundary and the published
contracts. Opened `tools/bga_timeline.py` against the flow paragraph at
`architecture.md:1117`, which names `dependency_edges` /
`_plane1_flows` / `_plane2_flows`: all three still exist and still do
what the paragraph says, and `_plane1_flows`'s return changed shape
this round (`UX-431`) without changing what the paragraph claims about
it. The streaming-render paragraph at line 663 — "the timeline is
*offered* from a file test and rendered at the first request for its
bytes" — is still exactly true, and is the reason `UX-443` had to be
filed rather than fixed.

**2. Does every published contract have a home?**
`test_the_documents_keep_up_with_the_contracts.py` is green over eight
schemas. The prose: `docs/spec/trace-dictionary.md` gained two
sentences this round (`UX-434`) stating that `depth` collides with
`slice.depth` and that `on_critical_path` is the text `true`/`false` —
both are facts a reader writing a query needs and neither was there
before, which is the half a mechanical guard cannot check.

**3. Is any figure invalidated?** One, and it is this round's own debt.
`docs/design/styleguide.md` §3g opens "`tools/bga_view.py:601` carries
**the only bound** the Perfetto handoff has", and `docs/guides/cli.md`
publishes the export ceilings as a two-row table whose second row calls
the trace's byte figure "the only part either ceiling singles out".
`UX-430` added a third bound, in tracks, five hours earlier. Both
sentences were true when written; neither is now. Filed as **`UX-446`**
rather than annotated in place, because the fix is a table that cannot
fall behind the constants again rather than one more sentence.

`git grep` over the other figures round 70 moved — the two export
bounds, the page half, `flows_dropped` — finds each quoted only where
it was measured, and §4e's `flows_dropped` example is a quotation of
the defect with a "closed in round 70" note beside it.

**4. What shipped since the last review that no document names?**
`bga --help`'s twelve subcommands are all in `cli.md`; `schemas.names()`
is eight and all eight are homed. Two mechanisms are not:

- `TRACE_TRACK_BUDGET` — part of `UX-446` above, since the ceiling and
  the table are one fix.
- **The route by which `tests/ci_reference.json` gets refreshed.**
  `UX-420` built the reference, `UX-427` made CI print the numbers and
  `UX-441` moved them into an artifact — and `git grep
  ci-reference-candidate -- docs .claude` returns nothing. The tool
  tells a contributor to "re-record with `--record` and commit" on a
  machine whose seconds `UX-418` established cannot be compared to
  CI's. Filed as **`UX-447`**.

`bga timeline --planes` / `--only-element` are documented (`cli.md`, by
the item that added them); `CI_DRIFT_RUNS`'s rule is in the `verify`
skill; `graph_depth` is a column name inside one query and needs no
home beyond the dictionary row that explains why it exists.

**5. Does each document's "last updated" claim match reality?**
`architecture.md`'s Verification Log is still the only document making
the claim, and its newest dated entry is 2026-08-26 (after `UX-309`)
against a file that moved 2026-08-30. Same reading as review 7's:
`UX-247`'s guard asserts the newest entry is not in the future rather
than that every edit adds one, the entries are re-groundings rather
than a changelog, and this round re-grounded nothing in that document.
Recorded here rather than filed, for the second review running - if a
third repeats it, the convention itself is what needs deciding.

**No code was produced by this review.** Both findings are filings, and
the one that is this round's own §3.10 debt is filed rather than
quietly fixed, so the next round can see that the debt existed.

## Review 9 — 2026-09-01, at 458 closed rows

Input: the twenty-six rows closed since review 8 — round 70's tail
(`UX-441`, `UX-442`, `UX-444`, `UX-445`, `UX-440`, `UX-453`), round 71
(`UX-454`, `UX-449`, `UX-450`, `UX-443`, `UX-448`, `UX-451`, `UX-452`,
`UX-446`, `UX-447`) and round 72 (`UX-457`, `UX-455`, `UX-456`,
`UX-462`, `UX-463`, `UX-464`, `UX-466`). One axis dominates: **where
fixtures come from**, and the instruments that say whether they cover
anything.

**1. Does the code still do what it says?** The chapter these rounds
moved under is the one at `architecture.md:91`, which opens *"One
script in `tools/` is not part of that pipeline and needs no `bst` at
all"* and then describes `gen_synthetic_scale_run.py`. Opened the
module: everything the paragraph says about it is still true — 1202
elements, 14 levels, 16 builders, byte-reproducible under `--seed`.
What is no longer true is the sentence's *first six words*. Round 72
added `tools/bga_gen_project.py`, which is in `tools/`, is not part of
that pipeline, and needs `bst` to build what it writes — the opposite
of the property the sentence generalises. Filed as `UX-472`.

**2. Does every published contract have a home?**
`test_the_documents_keep_up_with_the_contracts.py` is green over eight
schemas. The prose: round 72 nearly added a ninth by accident.
`tools/bga_gen_project.py` first stamped `project-spec/v1`, and
`test_the_contract_inventory_is_derived.py` reddened — `bga.contracts`
walks the `bga` package, so an id in `tools/` needs an owner there
(`UX-248`, and `run_store.OWNED` is the precedent). The right answer
turned out to be that a dev tool's *input* format is not part of the
release surface at all, so it takes a plain `spec_version: 1` and
claims no contract id. That is the mechanical guard doing exactly what
the review is meant to check by hand, one round earlier.

**3. Is any figure invalidated?** One, and it is in the first file
every session reads. `CLAUDE.md`'s tree map says
`docs/backlog/scenarios/   421 task files`; the tree has **468**, and
`closed.md` has 458 rows. Forty-seven out — `UX-132`'s defect in the
day-one summary. Filed as `UX-471`, with the observation that it is
the only figure in that file which decays on every close, so the fix
is probably to remove it rather than to guard it.

Checked and *not* invalidated: `UX-463`'s covering-set table, which
`UX-464` corrected in the same round rather than leaving to a review
(`certified-headroom` moved from T3 to T1, and "five specs for ten
findings" was annotated as looser than it read); and the census
figures, which live only in the rows that measured them.

**4. What shipped since the last review that no document names?**
Four tools: `dev_finding_coverage.py`, `dev_trace_coverage.py`,
`bga_gen_project.py` and `tests/fixtures/topologies.py`'s covering
set. All four are on the fixing guide's §6 context map — that guard
held. None is in `docs/design/architecture.md`, which is the second
half of `UX-472`. `bga --help` gained nothing: all four are dev
instruments, correctly outside the CLI.

**5. Does each document's own "last updated" claim match reality?**
Only this document carries dated rows, and its last row is the one
above. `docs/design/architecture.md` last changed 2026-08-31 and makes
no dated claim about itself. No drift.

**Deliberately not filed.** The trace census reports
`trace.spans[].task_key` as dropped because the trace decomposes it;
that reads like a finding and is not one, and `UX-466`'s docstring
already declares it. A review that filed it would be filing against a
declared limit, which is how a backlog fills with rows nobody can
close.

## Review 10 — 2026-09-01, at 484 closed rows

Input: the twenty-six rows closed since review 9 — round 72's tail
(`UX-465`, `UX-467`, `UX-458`, `UX-468`, `UX-480`, `UX-482`) and round
73 (`UX-459`, `UX-460`, `UX-473`, `UX-477`, `UX-479`, `UX-475`,
`UX-478`, `UX-474`, `UX-484`, `UX-471`, `UX-472`, `UX-481`, `UX-469`,
`UX-470`, `UX-476`, `UX-487`, `UX-486`, `UX-483`, `UX-485`, `UX-488`).
Two axes: **what a plane can capture and what its records carry**, and
**the sentences the graph-shape findings print**. The second is where
both findings are.

**1. Does the code still do what it says?** Three chapters moved under
this round and all three were checked against the modules:

- the spine's counters, `architecture.md:274` — *"the spine records
  `minflt`/`majflt` from the `/proc` read it already did, and
  `inblock`/`oublock` from the task's own"*. Opened `spine.c`:
  `read_cpu_times` parses both fault counts out of the `stat` buffer it
  already read, and `read_io_blocks` reads `/proc/%d/task/%d/io`. True,
  including the word *task's own*, which is the distinction `UX-487`
  had to make after `/proc/<pid>/io` folded in reaped children.
- the trace dictionary's `resource` row against `bga_timeline.py`'s
  `task_resources`: the four queue names and the `UX-469` reference
  are what the emitter writes.
- `what-the-viewer-answers.md` says *seventeen questions*;
  `bga/viewer/questions.js` holds 17. No drift.

**2. Does every published contract have a home?**
`test_the_documents_keep_up_with_the_contracts.py` — 8 passed. The
prose: this round published no new contract id. `dev_plane_capability.py`
and `dev_refresh_analysis.py` claim none, correctly — they are dev
instruments over `tools/` and `tests/fixtures/`, and neither emits a
document anybody consumes.

**3. Is any figure invalidated?** Yes, and by this round's own work.
`UX-0479`'s Outcome says *"golden's 406,000 stands"*; `UX-0469` moved
it to 411,000 hours later in the same round and did not annotate the
earlier file, which fixing guide §3.6 asks for and
`git grep 406,000 docs/backlog/scenarios` would have found. Filed as
`UX-493`.

Checked and *not* invalidated: `CLAUDE.md`'s task-file count, which
`UX-471` removed rather than guarded — the grep is empty, and the fix
held; `macro_micro`'s 458,000, which the tree still carries; and the
finding-census lines, which live only in the rows that measured them
and are dated by the row they sit in.

**4. What shipped since the last review that no document names?** Two
tools, `dev_plane_capability.py` and `dev_refresh_analysis.py`. Both
are on the fixing guide's §6 context map. Neither is in
`architecture.md`, and that is the *stated* policy there — the census
paragraph at `architecture.md:134` says dev instruments "are listed
with the rest in the fixing guide's §6 context map rather than here".
Checked whether the same paragraph's *count* had gone stale, since
that is the shape `UX-472` was filed for one review earlier: it says
"two censuses exist to say what a clone can actually reach" and names
the finding and trace censuses. `dev_plane_capability.py` does not
answer that question — it compares a plane's capability with its
records — so the sentence is still true and is **not** filed. `bga
--help` gained nothing.

**5. Does each document's own "last updated" claim match reality?**
No document outside this one carries a dated self-claim; this one's
last row is the one above. No drift.

**The finding that matters most is in the front door.** `README.md`
introduces its real-project block as *"verbatim"* and then prints, at
line 170:

```text
    Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains, so
```

`UX-475` closed this round and split that slot in two, and **neither**
branch can produce that line any more: `mesh-graph` now carries
`{off_path} of them off the critical path`, and a graph with none
prints `chain-graph` and a different sentence entirely. `UX-326` made
printed sentences contracts; this is one, quoted as evidence, in the
file an outside reader meets first. Filed as `UX-492`. Nothing caught
it because the block came from a real 3614-second freedesktop-sdk run
that no guard can re-run — which is also the hard part of fixing it.

**Deliberately not filed.** `UX-0075` and `UX-0076` quote the same old
sentence, and `planted-defect-walk-round-72.md` quotes it as the defect
it was reporting. All three are inside closed history, where the
sentence is correct as history; §3.6 is about a figure a document
presents as *current*. A review that filed those would be asking a
later round to rewrite the record of what was true when it was
written.

## Review 13 — 2026-09-03, at 560 closed rows

Input: the twenty-three rows closed since review 12 (`UX-538`..
`UX-562`, rounds 80-81), and — the user's brief — every document in
the tree, read against the implementation by five researchers. The
full round is [`round-82.md`](round-82.md); this row answers the
checklist.

**1. Does the code still do what it says?** Where a guard reads the
sentence, yes, to the digit: the CLI table, the contract inventory,
the viewer's 23 rows, the trace dictionary's 37 keys, the spec's Part
32, the README's block. Where none does, no: `architecture.md:3`
counts 75 scenarios, `capture-workflow.md` is three steps and eight
files behind its yml, `ingestion-pipeline.md` confirms its facts on a
`bst` this machine no longer has, the spec's Part 29 is wired to
`None`, and `roles.md` denies a mechanism that shipped two rounds
ago. `UX-569`..`UX-572`, `UX-565`, `UX-580`.

**2. Does every published contract have a home?** Yes — 23 ids in the
spec, the architecture inventory and `docs/README.md`, guarded both
ways, and the 32.6 layout row-for-row against a real capture. What
the guard leaves unheld: 32.1 lists 6 input fields where the loader
reads 24, and 32.4's key list omits four `AnalysisResult` fields
(`UX-568`).

**3. Is any figure invalidated?** Thirteen in the process layer alone
— `analyze/v2` in §3.7, a small tier at 11 s that runs 22 s, "421
task files" in the researcher agent, "fourteen questions",
"twelve contracts", a 34 KB guide at 38 KB (`UX-584`); the question
count three ways in the guides (`UX-576`); two byte figures for one
trace (`UX-578`); spec:1714's "all three" (`UX-566`).

**4. What shipped since the last review that no document names?**
Nothing new in `bga --help` since review 12. Older and unnamed:
`tools/native_trace/`'s four members and `dev_run.sh`, in neither
map (`UX-573`); Part 28's `fetch_build_overlap`, published and named
by no test (`UX-568`).

**5. Does each document's own "last updated" claim match reality?**
The ingestion document's "against `bst` 2.7.0" is its dated claim,
and the machine runs 2.8.0 (`UX-571`); the styleguide's §7 ledger
dates seven sections as unguarded that have been guarded since
rounds 59-70 (`UX-582`); the round-history table has no row for
round 81 (`UX-583`).

**The finding that matters most:** the tool moved faster than prose,
and every drift above is in a sentence no guard reads. The filings
do not ask for the prose to be rewritten — they ask for each
sentence to derive from, or be dated against, the thing it copies.

## Review 14 — 2026-09-03, at 587 closed rows

Input: the twenty-seven rows closed since review 13 — `UX-563`..
`UX-588` and `UX-592`, which is round 83 executing round 82's slate —
and the commits between them, `b100beb..ff3e08e`. Round 83 was a round
of guards: 23 new files under `tests/unit/`, most of them reading a
document against the tree. The full round is
[`round-83.md`](round-83.md); this row answers the checklist.

**1. Does the code still do what it says?** Where a guard reads the
sentence, yes. The 106 files under `tests/unit/` that open a path
below `docs/` were run as one selection: **1786 passed, 13 skipped, 2
failed**, and neither failure is a chapter wrong about a mechanism —
one was this row's own absence, the other `architecture.md`'s opening
counting 598 scenario files against git's 601. Both are repaired here
and the same selection is **1788 passed, 13 skipped, 0 failed**; the
second was repaired by `dev_close_task.py --check --write`, which the
merge runs again, because every filing below moves that count.

Where no guard reads the sentence, one is now false, and it is this
round's own doing. 32.7.2's mapping row says `duration_variability` is
*"computed as `DiagnosticsResult.duration_variability`, reaching no
consumer - not a `signals` key"*. `UX-565` writes
`signals['duration_variability']` at `bga/analyzer.py:2163`, publishes
it under `elements`, and draws two columns from it in
`bga/viewer/element.js`. `UX-564` wrote the row and `UX-565` falsified
it inside one round, from two tracks that branched from the same
commit and merged in that order — and the row's own guard cannot see
it, because the clause it checks is the one naming a `signals[...]`
key and this cell names none. The Part-index guard *did* see it:
`test_every_part_has_a_guard.py` carries a comment saying Part 29 left
its allowlist "in the same round". One of the two records moved.

**2. Does every published contract have a home?** Yes, and nothing
moved. `bga.contracts`: **23 emitted ids, 9 superseded, 3 read and
never written**, 8 printable and 15 not — the figures both
`architecture.md`'s log and `docs/README.md`'s table carry, each
guarded. `schemas.names()` is the same eight live ids as at review 13,
`analyze/v5` among them. The one commit that touched `bga/schemas.py`
this window added keys, which 32.5's own rule makes an addition rather
than a bump. Every superseded id a live document names is presented as
read-and-never-written, checked row by row.

**3. Is any figure invalidated?** Not by a number this round moved:
`dev_close_task.py --figures` over the whole diff reports 5 figures
removed and 4 still written, and all four sit in closed rows where
they are history — `UX-584`'s Outcome annotates the one that was
current. The figures a document presents as current were re-measured
and hold: 56 `analyze/v5` top-level properties, 22 modules in
`bga/viewer/`, 17 questions in `questions.js`, and `rules.md`'s
*"it is 40 KB"* against a 41,358-byte guide.

**4. What shipped since the last review that no document names?**
`bga --help` gained no command. Two mechanisms did, and neither has a
home. `UX-567` added `occupancy_within_capacity` to `hard_gates`,
which a real run now publishes six members of; Part 33.1 lists three
plus the blame-chain one, and neither that gate nor
`run_identity_consistent` is named anywhere in the spec or in the 36
tracked `.md` files outside `docs/backlog/` and `docs/audits/`.
`UX-588` guards a Python floor that `pyproject.toml` sets at `>=3.9`
and CI matrixes to 3.12 — and those same 36 documents, the README's
Install section included, name no Python version at all.

**5. Does each document's own "last updated" claim match reality?**
One document carries a currency claim, and its date was right while
its sentence was not. `architecture.md`'s Verification Log said
*Updated 2026-09-03 (after `UX-549`), covering round 81's three
changes to this document*, and `git log -1 --date=short --` on that
file also gives 2026-09-03 — so `test_the_verification_log_is_true.py`,
which reads the date and not the item, stayed green across two further
changes by `UX-569`. A round-83 entry is added by this review. Every
other dated string in the tree is a capture's date or a "Written"
date, which `UX-492` and `UX-511` chose deliberately.

The same guard's other half does not discriminate either, found by
mutating the entry this review wrote. `_claimed()` returns a **fixed
1200-character window** from the newest entry's date, and
`test_the_entry_says_what_it_was_grounded_in` looks for
*"re-grounded in"* anywhere inside it. Measured: the newest entry is
1045 characters and the phrase occurs at offsets **237 and 1169** — the
second belongs to the entry below. Deleting the clause from the newest
entry leaves the test green. It was already so at review 13's tree, at
800 and 837. Any entry shorter than about 1186 characters is checked
against its predecessor's sentence.

**The finding that matters most:** round 82 found prose that had
drifted from the tool, and round 83 gave that prose guards. What is
left is the same shape one layer up — a decision written in two places
where only one of them is read. Part 29's mapping row and its
allowlist row said the same thing, and `UX-565` moved one. Part 33.1
and `hard_gates` say the same thing, and `UX-567` moved one. Neither
is a sentence nobody reads: both are inside the registry the last
review built to stop exactly this.
