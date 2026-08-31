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

