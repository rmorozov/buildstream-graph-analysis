"""UX-195: the same page, as one file.

Direction 7's second delivery mode. `bga view --export report.html`
inlines the run's payloads into the static page and writes one
self-contained artifact — no port, no server, no network — for a CI
artifact, for "send me your report", and for the archive a pruned
snapshot leaves behind.

**The property under test is that it is the same page.** Not a second
renderer, not a simplified one: the identical `app.js`, reading its
payloads inline instead of over http, decided in one place. So the
guards below render the *exported file* through the same Node harness
`UX-193` renders the served payload with, and compare.

Measured, on the two runs the item names:

    1,202-element synthetic   report.json   816,573 B
    golden run                report.json    14,797 B
    the page itself (7 files)               39,119 B

At 1,202 elements the payload is 21x the page, which is Direction 7's
own test of whether the viewer stayed thin.
"""
import base64
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""
_RAW = """START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""


# UX-287: two bounds, because an export has two halves that grow for
# different reasons. Each is a measurement plus headroom, and each says
# which run it is a bound *for*.
#
#   the page      171,388 B on every run (modules 152,424 + css 17,135
#                 + 1,829 of scaffolding) - grows with source
#   golden   (4)  261,604 B   -> of which data 90,216
#   macro_micro (11) 299,695 B -> of which data 128,307
#
# The synthetic 1,202-element run exports at ~1.07 MB and is not
# committed (`UX-189`), so it is measured in the Outcome rather than
# guarded here.
#
# **The bounds moved once, and the split is what made that legible.**
# Round 39's viewer work (`UX-279`, `UX-280`, `UX-283`, `UX-284`,
# `UX-289`, `UX-292`) took the page 162,909 -> 171,388 B: modules
# +7,788, stylesheet +691. The data grew +2,653 in the same round, all
# of it schema descriptions the page shows as tooltips - which the
# companion guard below proves is documents rather than payload.
#
# That attribution is the difference between a bound that moves on a
# measurement and one that rises whenever it is exceeded, which is what
# `UX-287` was filed about. The page budget did *not* redden - it had
# 612 B left - and the totals did, which is the split working: source
# growth shows in every total and cannot hide behind content.
#
# **Round 41 moved the page bound**, and this is the first time it has
# moved since the split was drawn - which is what it is for. `UX-302`
# added two viewer modules (`shapes.js`, the style guide's §1 dispatch
# table as code; `rawjson.js`, the per-section "view as JSON" toggle)
# and the CSS for the toggle: modules 158,365 -> 163,177 (+4,812),
# stylesheet 17,428 -> 17,995 (+567). Measured either side of the
# change, on the committed runs:
#
#   page          177,624 -> 183,006 B   (+5,382, all source)
#   golden        274,979 -> 280,294 B   (+5,315)
#   macro_micro   314,158 -> 319,473 B   (+5,315)
#
# The page moved by what the source moved by, on both runs, which is
# the split doing its job: nothing here is content growth wearing a
# page's clothes. The guard below measures the page on its own
# synthetic snapshot, which reads 57 B more than the committed runs,
# and that gap predates these items.
#
# **And again for `UX-303`/`UX-304`**, in the same round:
#
#   page          183,006 -> 196,615 B   modules +12,005, styles +1,590
#   golden        280,294 -> 294,976 B   of which data +1,073
#   macro_micro   319,473 -> 334,155 B   of which data +1,073
#
# `drawings.js` is the +12,005: §2's two controls, and the header
# comment that argues for the boundary a self-built strip may not
# cross. **The export inlines modules verbatim, comments included** -
# so this repository's commenting convention is a byte cost every
# reader pays, and 175 KB of the 196 KB page is commented JavaScript.
# Recorded rather than acted on: `EXPORT_BUDGET_B` is 8 MiB and a
# 295 KB attachment is not a problem, but the next round that wants
# the page smaller should start here rather than at the payload.
#
# `UX-312` and `UX-314` moved the page by **+13,255 B**, all of it
# checked-in viewer source and none of it data:
#
#     questions.js   10,748 -> 18,238   (+7,490)  seven new questions
#     perfetto.js     8,329 -> 11,785   (+3,456)  Perfetto's own CSP,
#                                                 quoted where it is used
#     app.js        103,023 -> 104,875  (+1,852)  the transport decision
#     index.html      1,703 ->  2,160     (+457)  the save-it-yourself route
#
# So the numbers below move again, and the reason is the one the
# backstop's docstring already gives: a byte count cannot tell a
# feature from a library, and the guards that can - `the page is the
# modules and nothing else` and `no module looks like a vendored
# library` - both pass on this page. Nothing crept in.
#
# The comment share is the real lever and it is still `UX-307`'s: this
# very block is bytes every reader of an exported report pays for.
#
# **Round 44 (`UX-320`) moved the page again, and corrected the claim
# above.** The +44,601 B of checked-in viewer source this round added:
#
#     app.js        104,875 -> 118,215  (+13,340)  grades, folds, focus,
#                                                  the described value
#     drawings.js    12,545 ->  21,421   (+8,876)  the size scale, the
#                                                  twin, the tick row
#     style.css      34,575 ->  43,052   (+8,477)  §2a/§2b/§3a's rules
#     tablefocus.js       0 ->   6,692   (+6,692)  table focus, new module
#     views.js       98,792 -> 102,947   (+4,155)  the graded figures
#     shapes.js       6,541 ->   8,082   (+1,541)  `shapeOf`
#     index.html      2,160 ->   3,103     (+943)  the actions group
#     viewstate.js   10,686 ->  11,263     (+577)  `tf=` in the fragment
#
# And the correction, which matters more than the numbers. The round-41
# note above says "**The export inlines modules verbatim, comments
# included** ... 175 KB of the 196 KB page is commented JavaScript".
# **It does not.** `tools/bga_view.py`'s `_uncommented` has stripped
# whole-line and block comments from the inlined copy since `UX-205`.
# Measured on the exported page this round:
#
#     page     223,276 B
#       js     198,058 B   89%   trailing `//` comments ~114 B
#       css     22,247 B   10%
#       rest     2,971 B
#
# So the page is code. `UX-307`'s remaining scope is those ~114 B plus
# whatever a real minifier would buy - not the 175 KB the old note
# promised - and a round that wants the page smaller should start from
# this measurement rather than from that sentence.
#
# **Round 45 (`UX-307`) took them, and the estimate above was low.** The
# stripper is literal-aware now, so it reaches trailing comments as well
# as whole-line ones: **153 B**, not ~114, across four sites in three
# modules. Measured on the golden export, which is the fixture the bound
# below is set against:
#
#     page     223,227 B  ->  223,074 B     -153
#     data      98,374 B      98,374 B        +0
#     html     321,770 B     321,617 B      -153
#
# That is 0.07% of the page, and `UX-307` says so in its own Outcome
# rather than presenting the pass as a size win. What the pass actually
# bought is that the export's stripper knows a comment from a string -
# four URL constants and one regex literal in the same bundle look
# exactly like comments and are not.
#
# The +1,073 of *data* on both runs is the two `bga:distribution`
# hints and one `bga:series`, with their descriptions - the schema the
# page carries, which is the half the companion guard below proves is
# documents rather than payload.
# **Round 47 (`UX-334`) moved the page, and CI found what the bound was
# really measuring.** The console work added a viewer module and the
# commentary that argues for it:
#
#     page          223,362 -> 225,002 B   (+1,640, all source)
#     data           98,951 ->  98,986 B      (+35, the payload manifest
#                                              `run.json` now publishes)
#     golden        322,313 -> 323,988 B   (+1,675)
#     macro_micro   361,749 -> 363,424 B   (+1,675)
#
# The page moved by what the source moved by, on both runs - the split
# doing its job again. But the golden bound had **12 B of headroom** on
# the checkout it was last measured on, and it failed in CI at 324,022:
#
#     path len   20  ->  323,829 B
#     path len   61  ->  324,075 B
#     path len  111  ->  324,375 B
#
# The export embeds the run's absolute path - `run.json`'s `run` key and
# the analyze document both carry it - so **the number is a function of
# where the repository is checked out**, at roughly 5 B per character.
# A CI runner's checkout is 34 B of path longer than the container this
# was measured on, and that is the whole of the difference.
#
# Exporting from a copy at a fixed path was tried and declined: the
# committed runs sit inside a store, so `payloads()` finds a
# `compare.json` and a `store.json` beside them that a copy in `tmp_path`
# does not have - measured, macro_micro exports 363,424 B in place and
# 340,467 B copied. The bound would stop bounding the report the fixture
# actually produces.
#
# So the bounds below carry **~4 KB of headroom instead of 12 B**, which
# is about 800 characters of run path, and this note is what stops the
# next reader from reading a tight number as a tight measurement.
# **Round 48 (`UX-335`) moved the page again**, and the page budget is
# the guard that saw it - which is what it is for. Section-boundary
# error containment is new source and nothing else:
#
#     controls.js     2,816 ->   5,289   (+2,473)  `contained`, the
#                                                  failure card, and the
#                                                  measurement that
#                                                  argues for them
#     views.js      103,573 -> 105,711   (+2,138)  the two null-row
#                                                  sites stating their
#                                                  absence
#     app.js        120,600 -> 121,942   (+1,342)  nine renderers routed
#                                                  through `contained`
#
#     page          225,002 -> 227,498 B   (+2,496, all source)
#     data           98,986 ->  98,986 B       (+0)
#     golden        323,988 -> 326,484 B   (+2,496)
#     macro_micro   363,424 -> 365,920 B   (+2,496)
#
# Data did not move by a byte, on either run, which is the split saying
# what it exists to say: this round added code, not payload.
#
# The budget moves to 230,000 - the same ~2.5 KB of headroom the two
# export bounds carry, rather than the 998 B it had left after
# `UX-334`. A budget with one round's growth left in it reddens on the
# next round whatever that round does, and a guard that always reddens
# is a guard nobody reads.
#
# **Round 49 moved both halves, one each**, and the split named which
# item did which. Measured on a checkout whose path is the same length
# as this one's, so the numbers are comparable to the round above
# rather than to a temporary directory:
#
#                       round 48    UX-338    UX-339
#     page               227,498   228,528   228,528   (+1,030, +0)
#     data (golden)       98,986    99,291   101,906     (+305, +2,615)
#     golden             326,484   327,819   330,434
#     macro_micro        365,920   367,255   369,870
#
# `UX-338` is the one round in this note's history that moved *both*:
# +1,030 B of source, where the join merges into the element table and
# a preset gates itself on what it declares it draws, and +305 B of
# payload, because that declaration - `requires` - travels in the
# embedded `schemas.json` where the page can read it.
#
# `UX-339` moved the page by **zero bytes** and the payload by 2,615 on
# both runs, which is what a new contract looks like from here:
# `sweep/v1` is the twelfth document in the embedded inventory and no
# line of viewer source knows it exists. A ceiling could not have told
# that from 2,615 B of new code; the split can, and that is the whole
# argument for keeping it.
#
# Round 52 moved the page again, and the split says the same thing the
# other way round - all of it is source:
#
#                       UX-339    UX-346    UX-347
#     page             228,528   231,478   236,271   (+2,950, +4,793)
#     data (golden)     101,906    89,148    89,148  (-12,758, +0)
#     golden           330,434   320,626   325,419
#     macro_micro      369,870   337,760   342,553
#
# `UX-346` is the declaration channel (`bga:inline`, its two reasons,
# and `describedTerm`'s exception path) plus the twenty-four
# declarations, which are payload rather than page - and the *data*
# fell 12,758 B on the golden run, because the schemas travel with the
# document and `UX-345` removed a key from them.
#
# `UX-347` is the chapter fold: seven `answer` functions reading
# published fields, the open/shut control, the reveal every anchor goes
# through, and the CSS for all of it. Both companion guards stayed
# silent - every byte is a checked-in module, and none of it resembles
# a vendored library.
#
# Round 53 moved both sides, and in opposite directions:
#
#                       UX-347    UX-344    UX-348
#     page             236,271   236,271   239,610   (+0, +3,339)
#     data (golden)     89,148    85,387    85,387   (-3,761, +0)
#     golden           325,419   321,658   324,997
#     macro_micro      342,553   338,285   342,498
#
# `UX-344` is payload rather than page: lifting the two namespaces and
# publishing `provenance` once took 3,761 B off the golden run's data,
# and not a byte off the modules. `UX-348` is the other way round - the
# worked Perfetto example, its declared answer shape, and the offline
# blast section that spells the published command are all page, and
# both companion guards stayed silent: every byte is a checked-in
# module and none of it resembles a vendored library.
# Round 56 moved the page and not the data:
#
#                       before   UX-356
#     page             244,088  249,694   (+5,606)
#     data (golden)     85,356   85,356   (+0)
#     golden           329,444  335,050
#     macro_micro      369,740  375,346
#
# `UX-356` is the join's withheld fields reaching a reader: the
# `JOIN_EVIDENCE` declaration, `joinDetail`, the advice and evidence
# blocks in `elementSection`, and their styles. Every byte is a
# checked-in module and both companion guards stayed silent - and the
# *data* did not move at all, which is the point: nothing was added to
# the payload, twenty-three sentences it already carried stopped being
# withheld. 5,606 B of page to stop dropping thirteen of twenty-eight
# published fields is the trade, and the bounds are restated rather
# than the sentences left in `script#bga-report` to fit a number
# nobody argued.
# Round 56, second move - `UX-361`:
#
#                      UX-356   UX-361
#     page            249,694  260,369   (+10,675)
#     data (golden)    85,356   86,152   (+796)
#     golden          335,050  346,521
#     macro_micro     375,346  386,817
#
# Two new drawings and their styles - `decomposition` and `interval`,
# the shapes a strip and a sparkline cannot make - plus the resolver
# that reads their declarations. The *data* moved this time, by 796 B
# on the golden run: the two hints travel in the schemas, which travel
# with the document, and a declaration a consumer can read is worth
# more than the bytes (`UX-201`'s argument, and `UX-342`'s).
#
# This is the third page rise of the round, and the largest. It is also
# the last: `UX-360` is next and sets the volume budget these three
# restatements have been standing in for.
# Round 59, `UX-372`:
#
#                      UX-361   UX-372
#     page            260,369  267,286   (+6,917)
#     data (golden)    86,152   91,401   (+5,249)
#     golden          346,521  358,687
#     macro_micro     386,817  409,439
#
# The readers. `docs/design/roles.md` had named eight since round 27
# and no payload said which one an answer served, so the page opened
# with one question answered once for whoever was looking. The page
# half is `decision.js`'s picker and its lead block, the fragment key
# in `viewstate.js` and five lines of CSS; the data half is the
# `readers` index and the schema's prose for it, which every export
# carries. Both companion guards below stayed **silent** - every added
# byte is a checked-in module or a declared contract, and none of it
# resembles a vendored library - which is the check this procedure
# asks for rather than assuming. So: "a round landed", looked at.
#
# The three intervening restatements (`UX-338`/`UX-339`, `UX-356`,
# `UX-361`) each moved this number too; this is the fourth of the
# viewer axis and the first since `UX-360`'s volume budget landed. The
# volume budget is what bounds what a *reader* meets; this bounds what
# the file weighs, and they are different questions.
# `UX-399` moved the page half by 1,922 B, **all of it source** - the
# data half is 95,549 B (golden) and 148,380 B (macro_micro) either
# side of the change. What it buys is measured in styleguide §6c:
# `content-visibility: auto` on the sections inside a chapter, and the
# rail's `IntersectionObserver` scrollspy. Layout cost on the fully
# expanded page stops tracking the document - 6.4 -> 25.9 ms as a run
# grows from 2,441 to 23,040 nodes, against ~2 ms at every size - which
# is what `UX-397` was going to buy with a 400 KB dependency. Neither
# companion guard below spoke: every added byte is a checked-in module,
# and 1,922 B does not resemble a vendored library.
#
#     page            269,531 -> 271,453   (+1,922, source)
#     golden          365,080 -> 367,002
#     macro_micro     417,911 -> 419,833
# `UX-388` moved the page half by a further 1,266 B, again **all
# source**: an empty population now renders its heading and one line
# instead of vanishing, so the renderer gained the branch and the
# stylesheet two rules. The data half is unchanged at 95,549 B (golden)
# and 148,380 B (macro_micro) - nothing was added to any payload; what
# changed is that three of golden's keys and two of macro_micro's now
# reach a reader at all.
#
#     page            271,453 -> 272,719   (+1,266, source)
#     golden          367,002 -> 368,268
#     macro_micro     419,833 -> 421,099
# `UX-390` moved it by 954 B, all **source**, and this is the first
# rise since `UX-360`'s volume budget that buys a page which is
# *smaller* to read: `attribution` and `attribution_hints` were the
# same eight bucket names in two `<h2>` sections, and they are now one.
# The bytes are `bga:explained_by` in `format.js` with its rationale,
# the row rendering in `structured.js`, the `DRAWN_ELSEWHERE` entry,
# and four lines of CSS. The data half is unchanged - 18,786 B
# (golden) and 74,119 B (macro_micro) either side - because nothing was
# added to any payload; what changed is where two published keys are
# drawn. Neither companion guard spoke: every added byte is a
# checked-in module, and 954 B does not resemble a vendored library.
#
#     page            273,635 -> 274,589   (+954, source)
#     golden          373,214 -> 374,209
#     macro_micro     428,547 -> 429,542
# `UX-392` spent 584 B of it within the old bound - the filter and the
# Top-N preset now narrow the same set in one pass - and `UX-393` the
# remaining 2,652, all **source**: the rail gains a step
# bar - next section, previous section, back to the top - with its
# rationale, the cursor that makes two presses move two sections, the
# bracket-key accelerator and eight lines of CSS. It is in the rail
# rather than in a banner precisely so that `UX-347`'s distance budget
# and `UX-360`'s volume budget do not move, and neither did: the
# reading column is unchanged and the data half is 18,786 B (golden)
# and 74,119 B (macro_micro) either side. Neither companion guard
# spoke.
#
#     page            274,589 -> 277,825   (+3,236, source)
#     golden          374,209 -> 377,445
#     macro_micro     429,542 -> 432,778
# `UX-394` moved it by 2,923 B, all **source**: the run selector, the
# `?run=` every document fetch now carries, and six lines of CSS. The
# data half is unchanged - 18,786 B (golden) and 74,119 B
# (macro_micro) either side - because nothing was added to any
# payload; the run list is `store.json`, which a *served* page already
# had and an export never has, which is why the export renders no
# selector at all.
#
#     page            279,297 -> 282,220   (+2,923, source)
#     golden          379,706 -> 382,629
#     macro_micro     435,039 -> 437,962
#
# `UX-413` moved it again, and again all of it **source**: the bound a
# long table opens at is now decided on the total rather than on
# whether the table has a column worth ranking by, which needs a
# `First 40 rows` option for the tables that have none, and cards get
# the same bound through `boundCards`. Measured with this module's own
# instrument (`export` then `_embedded`), before and after:
#
#     page            282,543 -> 283,964   (+1,421, source)
#     golden          382,864 -> 384,218
#     macro_micro     438,227 -> 439,581
#
# Neither companion guard spoke: the contract half is 81,623 B either
# side (no declaration changed) and the data half moves only with
# `run_instance`, which is why the two totals move by exactly what the
# page did.
# `UX-431`: 284,584 -> 285,704. `UX-434`: -> 285,928, after 286,195
# tripped this and 267 B of prose and whitespace came back out.
#
# `UX-444` is why it moves now, and it is not that the page grew. The
# budget had a companion - the ratio in
# `test_the_data_dwarfs_the_page_on_a_report_worth_measuring` - and the
# procedure for that companion was "the largest round number the claim
# still carries against the *permitted* page". Applied literally, that
# is `floor(run_data / PAGE_BUDGET_B)`: a derived quantity, restated by
# hand every time this number moved, and written out in **three**
# places. It moved 4.0 -> 3.9 -> 3.3 -> 2.9 -> 2.8 -> 2.6 -> 2.5 -> 2.4
# over eight rounds, and every one of those was a transcription rather
# than a judgement.
#
# So the two now say different things. This is the **ceiling**: what a
# reader downloads, `UX-360`'s judgement, moved with a measurement and a
# record. `DATA_DWARFS_PAGE` below is the **claim**, a round number
# chosen once for what "dwarfs" means, which no longer has to be
# rewritten when this one moves.
#
#     page today                289,551 B   (after UX-448)
#     growth over rounds 69-71    +8,521 B  across three rounds
#     this budget                300,000 B  ~3 rounds of headroom
#
# Sized so a change is measured against a budget rather than negotiating
# with it, and so a framework arriving - hundreds of kilobytes at once,
# which is what the pair of guards is for - still trips it immediately.
PAGE_BUDGET_B = 300_000

#: `UX-444`: the claim, stated once. **The run's data is at least twice
#: the page a reader is permitted to download.**
#:
#: Direction 7's sentence is that the data is what an export weighs.
#: Two is where "dwarfs" stops being the right word for it, and that is
#: a judgement about the word rather than a transcription of this
#: quarter's measurement - which is what the eight previous values of
#: this constant were.
#:
#: Measured at 1,000 elements: **686,497 B of data against 2.0 x
#: 300,000 = 600,000**, with 86,497 B to spare. `PAGE_BUDGET_B` can
#: reach 343,248 before this needs revisiting, which is the point - the
#: ceiling moves on its own schedule and the claim does not follow it.
#:
#: What it still catches, and what already catches it better: a
#: framework arriving is hundreds of kilobytes of vendor code landing at
#: once, which `test_no_module_looks_like_a_vendored_library` finds *by
#: shape* - long lines, no comments - and does not need a threshold for.
#: This is the same event by weight, kept because two instruments for
#: one event is cheap and the shape one can be evaded by inlining.
DATA_DWARFS_PAGE = 2.0
MACRO_MICRO = "tests/fixtures/macro_micro/run"
COMMITTED_EXPORTS = [
    # `UX-299` moved both of these by ~300 B: `run.json` now publishes
    # `trace_inline_max_bytes`, the one threshold that decides both
    # whether this file inlines the trace and whether the served page
    # copies it through itself. A number the page must not keep a second
    # copy of, so it travels in the payload.
    # `UX-302` moved both again, by 5,315 B: the §1 dispatch table and
    # the "view as JSON" toggle are two new modules and their styles.
    # Source, not content - see the split above.
    # `UX-338` and `UX-339` moved both again, by 3,950 B - 1,030 of
    # source and 2,920 of payload, split between the two items in the
    # note above. The bounds are restated rather than the twelfth
    # contract left unpublished to fit a number nobody argued.
    # `UX-370` moved this one by 741 B, all of it **contract**: golden
    # has no Plane 2 report, so it carries none of the three new keys -
    # what grew is the embedded schema's prose for them, which every
    # export carries whether or not the run has the data. That split is
    # the whole reason `test_the_data_dwarfs_the_page` counts contract
    # separately, and it is why this bound moved less than the other.
    # `UX-372` moved this one by 5,151 B - 2,904 of source and 2,247
    # of contract, the split the note on `PAGE_BUDGET_B` above sets
    # out. Golden publishes two readers of the five, so most of the
    # data half is the schema's prose, which travels whether or not a
    # run has the rows.
    # `UX-371` moved this one by 567 B, all of it **source**: the
    # decision chapter now decides whether the ranking rule is shared
    # by every top action, states it once below the list when it is,
    # and suppresses the per-row copies. Nothing was added to the
    # payload - the data half is 89,154 B either side of the change -
    # so the composition guard below still accounts for every embedded
    # byte, and this is the case that split exists to tell apart.
    # `UX-380` moved both by 1,253 B, all of it **source**: the query
    # library gains the `graph-levels` question, which is a module the
    # page carries. Nothing was added to the payload - the data half is
    # 91,591 B either side of that commit.
    # `UX-382` moved both by 850 B - 143 of source and 707 of
    # **contract**. The source is `element.js`'s note on the one
    # resolved record; the contract is two `description` strings saying
    # which map each of the join's denormalised fields was copied from.
    # Golden has no `element_join` at all and still carries that prose,
    # which is the same fact `UX-370`'s note above records: the schema
    # travels whole whether or not a run has the rows.
    # `UX-383` moved this one by 3,248 B, **all of it contract**: the
    # schema sentences for `cpu_time`, `peak_memory` and
    # `resource_pressure` and for the six fields the join row gained.
    # The page half is 269,212 B either side of the change, so nothing
    # was added to the source - and golden has no Plane 2 at all, which
    # is why its whole move is prose. Same fact as `UX-370`'s note
    # below: the schema travels whole whether or not a run has the rows.
    # `UX-399` moved this one by 1,922 B, all of it **source** - the
    # scrollspy and the two stylesheet rules; see the note on
    # `PAGE_BUDGET_B` above for what they buy and what they cost.
    # `UX-407` moved both by contract and by data, and barely by
    # source. The restructuring synthesis - the one paragraph that
    # names a whole restructuring, which `correlate/v2` published and
    # the page never read - is now a key of `analyze/v4` too, declared
    # once for both contracts:
    #
    #     source       273,340 -> 273,635   (+295, two comments)
    #     contract      76,895 ->  79,107   (+2,212, the declaration)
    #     data (golden) 18,786 ->  18,786   (+0: no Plane 2, no finding)
    #     data (m_m)    71,587 ->  72,425   (+838, the finding itself)
    #
    # The contract half travels whether or not a run has the rows,
    # which is the fact `UX-370`'s and `UX-382`'s notes above record -
    # and it is why golden, which has no Plane 2 at all and gains no
    # data, still moves by 2,507 B. Neither companion guard spoke:
    # 295 B of source is two comments on `structured.js`, and nothing
    # here resembles a vendored library.
    # `UX-389` moved both again, and again mostly by contract. Six
    # Plane 2 blocks that answer *did the instrument see everything* -
    # whether the ptrace spine ran, how many processes were traced,
    # which elements could hide a static binary - now travel in
    # `plane2_coverage` instead of stopping at a terminal:
    #
    #     source       273,635 -> 273,635   (+0)
    #     contract      79,107 ->  80,793   (+1,686, the declarations)
    #     data (golden) 18,786 ->  18,786   (+0: no Plane 2, no blocks)
    #     data (m_m)    72,425 ->  74,119   (+1,694, the blocks)
    #
    # Not one byte of source: the blocks render through the machinery
    # that was already there, which is `UX-193`'s property and the
    # reason a schema addition costs no viewer change.
    # `UX-390`: +995 B, all source; see the note on `PAGE_BUDGET_B`.
    # `UX-393`: +3,236 B, all source; see the note on `PAGE_BUDGET_B`.
    # `UX-396`: +789 B, all **contract** - `attribution` declares its
    # eight parts as a `bga:decomposition`, and a declaration travels
    # with every export whether or not a run has the numbers. The page
    # half is 277,825 B either side: no new instrument was drawn, which
    # is the Out of Scope this item was held to.
    # `UX-397`: +486 B, all source - the handoff group moves into the
    # rail, with the rationale and eight lines of CSS.
    # `UX-395`: +986 B, all source - `questions.js` gains the sentence
    # that says which trace format a canned query needs and why an
    # empty result is the format's, plus the two declarations it reads.
    # `UX-394`: +2,923 B, all source; see the note on `PAGE_BUDGET_B`.
    # `UX-419`: +620 B here too, all source - see the note on the
    # `macro_micro` bound below. 384,838 leaves 162 B of headroom, so
    # the bound moves with the measurement rather than being ridden to
    # its edge by the next change.
    # `UX-431`: +1,120 B on both, **all of it source** - `questions.js`
    # gains the paragraph that says what the dependency graph's edges
    # became, and the sentence per reason one did not become an arrow.
    # The data half is 100,264 B (golden) and 155,617 B (macro_micro)
    # either side of the change, and that is not an accident worth
    # hiding: neither committed export carries a timeline at all, so
    # neither publishes `trace_flow_losses` and the new paragraph does
    # not render in either. The measurement is what says so - the guard
    # that exercises it is `TestTheLostEdgesAreAccountedFor`, on
    # `with_timeline`, which is the only committed fixture with a
    # `build.log`.
    # `UX-434`: +320 B on both, all source - see the note on
    # `PAGE_BUDGET_B` above for what the query bought and what it cost.
    # `UX-433`: +1,841 B on both, all **source** - `debug.exe` and the
    # `cost-by-executable` pivot it made possible. No payload: neither
    # committed export carries a timeline, so neither has a Plane 2
    # slice to annotate.
    # `UX-448`: +3,284 B (golden) and +3,415 B (macro_micro), split
    # by measurement rather than by assertion:
    #
    #                        page      golden data   macro_micro data
    #     before          286,739 B      101,520 B          156,885 B
    #     after           289,551 B      101,992 B          157,488 B
    #                      +2,812 B         +472 B             +603 B
    #
    # The page half is the `executables-in-element` entry, `queriesFor`
    # and `investigationsFor`, and the paste loop that draws one query
    # block per grain. The +472 B both exports share is the two
    # `trace_queries` declarations in the embedded contract; the extra
    # 131 B on `macro_micro` is the published array itself, on the one
    # `latent-heavies` finding and its provenance record. Golden has no
    # such finding, which is why its data moves by the contract alone -
    # the two numbers differing by exactly the payload is what says the
    # split is measured and not apportioned.
    # `UX-477` moved this one by 7,932 B, and **the page half did not
    # move at all** - 291,588 B before and after, measured by this
    # file's own splitter. The whole of it is data, because the golden
    # run changed which branch it takes: `chain_share`'s denominator is
    # the task horizon now, and four back-to-back tasks that used to
    # read `scheduler_bound` at 0.875 (on BuildStream's startup, not on
    # their graph) read `chain_bound` at 1.000. The chain-bound arm
    # publishes `time-concentration`, `joint-saving`,
    # `optimization-horizon` and `latent-heavies` with their evidence
    # where the other published one `blast-radius-ranking`. Rows rather
    # than prose, which is the half an export is supposed to be made
    # of. The recorded 391,543 B was itself 2,037 B stale; measured
    # before this change it was 393,580 B, so the old bound had 420 B
    # of headroom rather than the ~4 KB the note above claims.
    # `UX-479` moved this one by 1,654 B and **the page half did not
    # move at all** - 291,588 B before and after. Golden gains
    # `blast-radius-reach`, which the chain-bound arm published nothing
    # in place of: 1,485 B of it is the finding and 169 B its
    # provenance record, which cites two scalars rather than the map
    # (see the note on `macro_micro`'s bound below). The recorded
    # 401,512 B was 152 B stale, so the bound had 4,336 B of headroom
    # rather than 4,488, and has 2,682 B now.
    # `UX-469` moved both by 2,228 B - 2,114 of **source** and 114 of
    # payload. The source is the `resource-queues` question, its
    # `returns` table and the note above it, which the page carries as
    # a module; the payload is `resource-queues` joining `stalls` in
    # the `trace_queries` of two findings, `wait-category` and
    # `capacity-recommendation`. Measured with this module's own
    # instrument, before and after:
    #
    #     page            291,588 -> 293,702   (+2,114, source)
    #     golden          405,037 -> 407,265   (data 113,449 -> 113,563)
    #     macro_micro     454,942 -> 457,284   (data 163,354 -> 163,582)
    #
    # The recorded 403,318 B was 1,719 B stale - rounds 73's four
    # finding items grew it inside the bound and none of them restated
    # it - so the old bound had 963 B of headroom rather than 2,682.
    # 411,000 leaves 3,735 B.
    ("golden", GOLDEN, 411_000),                       #  407,265 B
    # `UX-297` moved this one by 385 B before that: the two-plane run
    # publishes `plane2_coverage.source`, which says which shape of
    # Plane 2 report served its numbers and what that costs to open. A
    # sentence a reader of a gigabyte capture needs, and the bound is
    # restated rather than the sentence trimmed to fit a number nobody
    # argued.
    # `UX-300` moved both again, by ~2.6 KB: the embedded
    # `store-aggregate/v1` now carries what the store weighs - a
    # `snapshot_bytes` distribution per host class and a document-level
    # total - which is the page telling a reader what their disk holds
    # without their having to go and ask a second command.
    # `UX-370` moved this one by 11,517 B: 741 of contract, as above,
    # and ~10.8 KB of this run's own Plane 2 measurements -
    # `by_binary`, `binary_cost` and `configure_phase`, which were
    # published in `plane2.json` beside the run and reached no reader.
    # Data rather than page, which is the half an export is supposed to
    # be made of.
    # `UX-372` moved this one by 5,849 B - the same 2,904 of source and
    # 2,945 of data. More data than golden because `macro_micro`
    # publishes all five readers where golden publishes two, which is
    # the rows rather than the prose.
    # `UX-380` and `UX-382` moved this one by the same 2,103 B, split
    # the same way - see the two notes on golden above. Both halves of
    # that move are prose rather than rows, so the two bounds moved by
    # an identical amount, which is what a source-and-schema change
    # looks like from here.
    # `UX-383` moved this one by 5,307 B: the same 3,248 of contract as
    # golden, plus **2,059 of this run's own measurements** - the CPU
    # each element burned and the run's own CPU, peak-memory and
    # pressure totals, published in `plane2.json` beside the run and
    # reaching no reader in a browser. Data rather than page, which is
    # the half an export is supposed to be made of.
    # `UX-399` moved this one by the same 1,922 B of source as golden:
    # the page half is one file and both exports carry all of it.
    # `UX-407`: +3,345 B, split in the note above the golden bound -
    # 2,212 of contract, 838 of data (this run has the chain), 295 of
    # source.
    # `UX-389`: +3,380 B, split in the note above the golden bound.
    # `UX-390`: +995 B, all source.
    # `UX-393`: +3,236 B, all source. `UX-396`: +789 B, all contract.
    # `UX-419`: +620 B, all **source** - `boundGroups` and `boundPairs`,
    # the bound a map section never had. Both committed fixtures move by
    # the same 620 and the page half moves with them (283,964 ->
    # 284,584), which is the signature of source: no control is rendered
    # here at all, because neither fixture publishes a map over
    # `TABLE_OPENS_BOUNDED_ABOVE` keys. That is the same absence that
    # let the defect live - the bound is measured by `UX-400`'s sweep at
    # 120 keys, not by a fixture.
    # `UX-431`: +1,120 B, all source - the same paragraph as golden;
    # the split is in the note above that bound.
    # `UX-448`: the split is in the note above golden's bound.
    # `UX-479` moved this one by 3,316 B, past the 450,000 bound, and
    # again **the page half did not move** - 291,588 B before and
    # after. Measured with this file's own splitter:
    #
    #                        page      golden data   macro_micro data
    #     before          291,588 B      110,076 B          158,276 B
    #     after           291,588 B      111,730 B          161,592 B
    #                          +0 B       +1,654 B           +3,316 B
    #
    # Split by payload key on `macro_micro`: findings +1,485 B,
    # provenance +1,777 B, readers +53 B, document_shape +1 B.
    #
    # The provenance half was **+4,955 B** on the first attempt, three
    # times the finding it explains, because both blast claims cited
    # `elements.blast_radius` - the whole map - and `record` inlines
    # whatever a path resolves to. Neither claim had ever fired on a
    # committed capture (both fixtures are chain-bound; that arm was
    # closed), so the duplication was latent and this item's first run
    # reddened fifteen guards with it, among them "every numeric leaf
    # declares a unit" and "no map is keyed by data it cannot
    # describe". Both blast claims now cite one scalar per element they
    # name - `elements.blast_radius[base.bst].downstream_count` - which
    # is `UX-288`'s rule kept rather than negotiated. The general form,
    # a builder that will inline the next population just as happily,
    # is `UX-483`.
    #
    # The recorded 447,039 B was 2,825 B stale: measured before this
    # change it was 449,864 B, so the bound it was riding had 136 B of
    # headroom, not the ~3 KB the number claimed. 458,000 leaves
    # 4,820 B, which is what "moved with a measurement" means here.
    # `UX-469`'s +2,228 B (the note on `golden` above has the split)
    # leaves this one at 457,284 B and **716 B of headroom**. Not moved
    # here because it is not tripped, and a bound moved without a
    # measurement that forced it is the negotiation this file exists to
    # prevent - but the next round to add a module will trip it, and
    # the figure it needs is this one rather than the stale 453,180.
    ("macro_micro", MACRO_MICRO, 458_000),             #  457,284 B
]


def _embedded(path):
    """The bytes of documents the page carries, so the rest is the page."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return sum(len(found) for found in re.findall(
        r'<script type="application/json"[^>]*>(.*?)</script>', text, re.S))


@pytest.fixture
def snapshot(tmp_path):
    snap = tmp_path / "20260821T120000Z"
    snap.mkdir()
    (snap / "build.log").write_text(_WRAPPED)
    shutil.copytree(GOLDEN, snap / "run")
    os.remove(snap / "run" / "expected_output.json")
    with gzip.open(snap / "plane2.log.gz", "wt") as handle:
        handle.write(_RAW)
    return snap


@pytest.fixture
def exported(snapshot, tmp_path):
    from tools.bga_view import export

    path = tmp_path / "report.html"
    result = export(str(snapshot / "run"), str(path))
    return path, result


class TestItNeedsNothingButItself:
    def test_no_reference_reaches_the_network_or_the_filesystem(self, exported):
        """An export opens from a download folder, a CI artifact viewer,
        or an email attachment. Anything it would have to fetch is
        simply not there."""
        text = exported[0].read_text()
        for url in re.findall(r'(?:src|href)="([^"]+)"', text):
            assert url.startswith(("#", "data:", "mailto:")) or \
                url.startswith("https://ui.perfetto.dev"), (
                    f"{url} would have to be fetched")

    def test_no_relative_module_import_survives(self, exported):
        """A browser refuses a relative `import` over `file://`, so the
        two modules are concatenated into one inline block."""
        text = exported[0].read_text()
        assert not re.search(r"""import\s.*from\s+["']\./""", text)
        assert "openInPerfetto" in text, "perfetto.js was not inlined"
        assert "renderFindings" in text, "app.js was not inlined"

    def test_every_payload_is_present_as_a_block(self, exported):
        found = set(re.findall(r'id="bga-([a-z]+)"', exported[0].read_text()))
        assert {"report", "schemas", "run"} <= found, found

    def test_the_blocks_are_named_the_way_the_loader_looks_them_up(
            self, exported):
        """The one that bit: `payloads()` keys by *url*
        (`report.json`), the loader looks up by *name* (`bga-report`).
        Getting it wrong is silent — the block is simply never found and
        the page falls through to `fetch`, which works when served and
        fails on `file://`, so the export looks fine everywhere except
        where it is used."""
        text = exported[0].read_text()
        assert 'id="bga-report"' in text
        assert 'id="bga-report.json"' not in text

    def test_a_payload_containing_a_script_tag_cannot_end_the_block(
            self, snapshot, tmp_path, monkeypatch):
        """An element named after an html file is not hypothetical, and
        a `</script>` anywhere in a payload would end the block early -
        everything after it becoming markup.

        Injected at the `payloads` seam. The first draft set `run_id` in
        `run-context.json` and asserted on the output; `run_id` is
        *computed*, so the string never reached the payload and the test
        passed without exercising the escape at all.
        """
        import tools.bga_view as view

        monkeypatch.setattr(view, "payloads", lambda run: {
            "report.json": {"schema": "analyze/v2", "section": None,
                            "run_id": "a</script><script>alert(1)</script>",
                            "total_duration_us": 1}})
        path = tmp_path / "r.html"
        view.export(str(snapshot / "run"), str(path))
        text = path.read_text()

        assert "alert(1)</script>" not in text, "the block was ended early"
        assert "<\\/script>" in text, "nothing was escaped"
        block = re.search(r'id="bga-report">(.*?)</script>', text)
        assert json.loads(block.group(1).replace("<\\/", "</"))["run_id"] == \
            "a</script><script>alert(1)</script>", "the payload was mangled"


@needs_node
class TestItRendersTheSameThing:
    """The exported file, parsed and rendered by the same harness the
    served payload goes through."""

    def _render_export(self, path):
        script = _EXPORT_HARNESS % json.dumps(str(path))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=90)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_it_renders_the_runs_findings_and_sections(self, exported):
        rendered = self._render_export(exported[0])
        assert "findings" in rendered["sections"], rendered["sections"]
        assert rendered["severities"], "no severity reached the page"

    def test_it_renders_what_the_served_page_renders(self, exported, snapshot):
        """Same payload, same schema, same renderer - so same output.
        A second renderer would show up here as a difference."""
        from tools.bga_view import payloads, schemas_payload

        run = str(snapshot / "run")
        payload = payloads(run)["report.json"]
        schema = schemas_payload()[payload["schema"]]

        served = subprocess.run(
            [node, "--input-type=module", "-e",
             _SERVED_HARNESS % (json.dumps(payload), json.dumps(schema))],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=90)
        assert served.returncode == 0, served.stderr

        assert self._render_export(exported[0])["sections"] == \
            json.loads(served.stdout)["sections"]


class TestTheTimeline:
    def test_it_travels_inline_as_a_data_url(self, exported):
        """So the Perfetto button works from `file://`: `fetch` handles
        `data:` URLs, and the handshake never needed a server."""
        text = exported[0].read_text()
        block = re.search(r'id="bga-trace">"(data:application/gzip;base64,'
                          r'([A-Za-z0-9+/=]+))"', text)
        assert block, "no inline trace"
        # `UX-298`: a Perfetto trace, not a JSON array. `Trace` is
        # `repeated TracePacket packet = 1`, so the first byte of the
        # stream is that field's tag - `(1 << 3) | 2`.
        assert gzip.decompress(base64.b64decode(block.group(2)))[:1] == b"\x0a"
        assert exported[1]["has_timeline"] is True

    def test_a_run_without_one_says_so_rather_than_shipping_a_dead_button(
            self, tmp_path):
        from tools.bga_view import export

        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        result = export(str(run), str(tmp_path / "r.html"))

        assert result["has_timeline"] is False
        # UX-329: which absence, not just that there is one. This run is
        # a copy of the golden fixture with no Plane 2 report anywhere
        # near it, and the sentence it used to get - "no raw Plane 2
        # log" - describes a *captured* run whose log was dropped. A
        # reader cannot tell a machine that never traced from a
        # measurement missing only its timeline, and those are the two
        # things this sentence was covering.
        from bga import plane2

        assert result["omitted"] == plane2.NOT_CAPTURED, result["omitted"]
        run_block = re.search(r'id="bga-run">(.*?)</script>',
                              (tmp_path / "r.html").read_text())
        assert json.loads(run_block.group(1))["has_timeline"] is False

    def test_an_oversized_timeline_is_dropped_and_the_reason_recorded(
            self, snapshot, tmp_path, monkeypatch):
        """Recorded, not silent: the report is still worth having, and
        a user who wanted the timeline needs to know where it went."""
        import tools.bga_view as view

        monkeypatch.setattr(view, "TRACE_BUDGET_B", 8)
        result = view.export(str(snapshot / "run"), str(tmp_path / "r.html"))
        assert result["has_timeline"] is False
        assert "ceiling" in result["omitted"]
        assert 'id="bga-trace"' not in (tmp_path / "r.html").read_text()


class TestNoRecordCarriesAPopulationTwice:
    """`UX-483`: an embedded provenance record cites this document; it
    must not copy a population out of it.

    `record` used to inline whatever a path resolved to. For a scalar
    that is right and reads better for it. For a population it is a
    second publication of a document the report already carries, and
    `UX-479` measured what that costs the moment a claim does it:
    `macro_micro`'s provenance grew **4,955 B** against the finding's
    own 1,485, and fifteen guards - unit declarations, the leaf-depth
    ceiling, the golden snapshot - went red together.

    Those two claims were narrowed. This is the rule underneath, and it
    **counts rather than reads**: no clause here knows which paths the
    claims cite, only that no row carries a container and that the
    whole record list stays a small fraction of what it explains.
    """

    #: The largest scalar any evidence row carries today, with room.
    #: Measured over every cited path on both scales - 26 on
    #: `macro_micro` and 11 at 1,202 elements - where the widest is
    #: **18 B** (`elements.zero_slack_share`, a float). 400 leaves room
    #: for a claim that cites a sentence rather than a number, and is
    #: still two orders below the population that opened `UX-483`.
    EVIDENCE_VALUE_MAX_B = 400

    #: **One record**, not the list and not its share of the report.
    #: Measured on three runs, largest record each:
    #:
    #:     golden         11 records,  7,671 B  (26.7% of the report)
    #:                    largest   959 B  blast-radius-reach
    #:     macro_micro    15 records, 10,676 B  (13.6%)
    #:                    largest 1,077 B  blast-radius-reach
    #:     scale (1,202)   9 records,  6,153 B  ( 1.0%)
    #:                    largest   902 B  diagnosis
    #:
    #: The *share* is 26.7% to 1.0% across those three and measures the
    #: report's size, not the records'. The largest single record is
    #: 902-1,077 B on all of them and does not move with the graph,
    #: which is the quantity that explodes when one record inlines a
    #: population: `UX-479` measured **+4,955 B on one record** the
    #: moment two claims cited `elements.blast_radius`. 2,000 leaves
    #: room for a claim that cites a sentence and is still less than
    #: half of that.
    RECORD_MAX_B = 2_000

    def _records(self, run):
        from tools.bga_view import payloads

        return payloads(str(run))["report.json"].get("provenance") or []

    @pytest.mark.parametrize("label,run", [(l, r) for l, r, _b
                                           in COMMITTED_EXPORTS])
    def test_no_evidence_row_carries_a_container(self, label, run):
        carried = []
        for record in self._records(run):
            for row in record.get("evidence") or []:
                if isinstance(row.get("value"), (dict, list)):
                    carried.append((record["claim"], row["path"],
                                    len(json.dumps(row["value"]))))
        assert carried == [], (
            f"{label}: provenance row(s) carrying a whole container - the "
            f"record cites this document and a copy publishes that "
            f"population twice (UX-483): {carried}")

    @pytest.mark.parametrize("label,run", [(l, r) for l, r, _b
                                           in COMMITTED_EXPORTS])
    def test_no_evidence_value_is_bigger_than_a_number(self, label, run):
        """The size half, which catches by weight what the shape clause
        catches by type - a very long *string* is not a container and is
        still not a citation."""
        heavy = []
        for record in self._records(run):
            for row in record.get("evidence") or []:
                if "value" not in row:
                    continue
                size = len(json.dumps(row["value"]))
                if size > self.EVIDENCE_VALUE_MAX_B:
                    heavy.append((record["claim"], row["path"], size))
        assert heavy == [], (
            f"{label}: evidence value(s) over {self.EVIDENCE_VALUE_MAX_B} B; "
            f"the widest one measured when this was written was 18 B: "
            f"{heavy}")

    @pytest.mark.parametrize("label,run", [(l, r) for l, r, _b
                                           in COMMITTED_EXPORTS])
    def test_no_single_record_weighs_what_a_population_weighs(
            self, label, run):
        """Counting rather than reading: no clause here knows which
        paths the claims cite, only that no one record grew to the size
        of the thing it is supposed to be citing."""
        heavy = sorted(
            ((len(json.dumps(record)), record["claim"])
             for record in self._records(run)), reverse=True)
        assert heavy, f"{label}: the report publishes no provenance at all"
        size, claim = heavy[0]
        assert size <= self.RECORD_MAX_B, (
            f"{label}: the `{claim}` record is {size:,} B, over the "
            f"{self.RECORD_MAX_B:,} this is kept to. The largest measured "
            f"when this was written was 1,077 B, and the one population "
            f"UX-479 inlined added 4,955 B to a single record")

    def test_a_cited_container_is_thinned_rather_than_dropped(self):
        """The other direction, so the rule is a distinction and not a
        deletion: a path that resolves to a container is still
        *published* - path, `resolved: true` and the shape it found -
        because a reader following the chain has to know the rule read
        something rather than nothing."""
        from bga import provenance

        document = {"elements": {"blast_radius": {
            f"e{i}.bst": {"downstream_count": i} for i in range(40)}}}
        assert isinstance(
            provenance.resolve(document, "elements.blast_radius"), dict)
        # Through `record` itself, with a claim whose only path is that
        # map - the real builder, not a re-implementation of its rule.
        provenance._CLAIMS["probe-483"] = (
            ("elements.blast_radius",),
            provenance._unconditional("probe"), ())
        try:
            built = provenance.record({}, "probe-483", "finding", document)
        finally:
            del provenance._CLAIMS["probe-483"]
        [only] = built["evidence"]
        assert only["resolved"] is True, only
        assert "value" not in only, only
        assert only["elided"] == "dict[40]", only


class TestTheSizeDiscipline:
    """Direction 7's rule is a *ratio*: "the data, not the page, is what
    an export weighs". It was guarded by an absolute byte ceiling, and
    across rounds 23, 24 and 25 that ceiling was crossed three times by
    ordinary feature work - the decision panel, the rails, the table
    tools, the view state, the element object - and raised twice.

    A number that moves every time a feature lands is not measuring the
    feature; it is measuring the calendar. So the third time, what is
    measured changed instead of the number:

    1. **Composition** - the page *is* the checked-in modules plus the
       stylesheet and nothing else. This is the one that can tell 6 KB
       of new feature from 6 KB of vendored library, which is what the
       rule was always about.
    2. **The ratio, on a report big enough for it to mean something** -
       Direction 7's sentence as written.
    3. **A loose absolute backstop**, kept deliberately far above the
       current page so that crossing it means something structural
       happened rather than that a round landed.

    Measured today: eight modules at 85,579 B comment-stripped,
    `style.css` at 10,822 B, `index.html` at 1,433 B.
    """

    def test_the_page_is_a_backstop_away_from_where_it_is(self, exported):
        """The loose one, raised in round 26 and - deliberately - given
        the instrument it was standing in for.

        This number has now been crossed in rounds 23, 24, 25 and 26,
        and raised each time. UX-218 named that failure exactly: *a
        number that moves whenever a feature lands is measuring the
        calendar*. The reason it kept being raised is that its stated
        job - "crossing it means something structural happened rather
        than that a round landed" - was one it could not actually do. A
        byte count cannot tell a feature from a library.

        Measured when round 26 crossed it:

            page (data removed)   123,785 B
              modules             109,913 B
              style.css            12,552 B
              index.html            1,433 B
              accounted           123,898 B  = 100.1% of the page
            export total          184,934 B  = 2.20% of the 8 MiB budget

        Every byte is a checked-in module. Nothing crept in, the ratio
        guard still holds at 1,000 elements, and the export is a fortieth
        of what an attachment may weigh. So the backstop fired, someone
        looked, and the answer was "a round landed" - four times.

        Raised to 200,000 and joined by `test_no_module_looks_like_a
        _vendored_library` below, which checks the thing this number was
        a proxy for. If the absolute fires again it should be because
        that one is silent and something genuinely odd is happening.

        It fired a fifth time, at 204,308 B, when `UX-312` and `UX-314`
        landed - and the check the paragraph above describes did its
        job. Both companion guards stayed **silent**: every added byte
        is a checked-in module (`questions.js` +7,490 for seven new
        canned questions, `perfetto.js` +3,456 for Perfetto's own CSP
        quoted where it is used, `app.js` +1,852, `index.html` +457),
        and none of it resembles a vendored library. So this is the
        fifth "a round landed", looked at rather than assumed, and the
        number moves to 210,000.
        """
        html = open(exported[0], encoding="utf-8").read()
        # Every `<script type="application/json">` block and the trace
        # blob are *data*. What is left is the page.
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        assert len(page) < PAGE_BUDGET_B, (
            f"the exported page is {len(page)} B with its data removed - "
            f"that is a structural change, not a feature. Check "
            f"`test_the_page_is_the_modules_and_nothing_else` and "
            f"`test_no_module_looks_like_a_vendored_library` first.")

    def test_no_module_looks_like_a_vendored_library(self):
        """What the byte ceiling was a proxy for, measured directly.

        Direction 7's rule is about what the page *is*, not how big it
        got. Hand-written modules are line-wrapped source with comments;
        vendored or minified code is not - it arrives as a small number
        of enormous lines and almost no comment. That difference is
        visible, and unlike a byte count it does not move when a feature
        lands.
        """
        import tools.bga_view as view

        offenders = []
        for name in view._module_order():
            source = open(os.path.join(view.ASSET_DIR, name),
                          encoding="utf-8").read()
            lines = source.splitlines() or [""]
            longest = max(len(line) for line in lines)
            commented = sum(1 for line in lines
                            if line.lstrip().startswith(("//", "/*", "*")))
            if longest > 400:
                offenders.append(f"{name}: a {longest}-character line")
            if len(source) > 4_000 and commented / len(lines) < 0.05:
                offenders.append(
                    f"{name}: {commented}/{len(lines)} commented lines")
        assert offenders == [], (
            f"these do not look like the hand-written modules this page is "
            f"supposed to be: {offenders}")

    @staticmethod
    def _weigh(tmp_path):
        """`(code, contract, run_data)` of an export at 1,000 elements.

        `UX-367` pulled this out of the ratio clause so the clause that
        checks the ratio is not a second page bound measures the same
        export the ratio does. Two clauses with two instruments would be
        exactly the shape of defect they exist to hold.
        """
        import tools.bga_view as view

        from tests.fixtures.topologies import linear_chain, write_run_dir

        run = write_run_dir(tmp_path, linear_chain(1000))
        out = tmp_path / "big.html"
        view.export(str(run), str(out))
        html = out.read_text(encoding="utf-8")
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        schemas = re.search(
            r'<script type="application/json" id="bga-schemas">(.*?)'
            r"</script>", html, re.S).group(1)
        # `UX-342`: the schemas are apparatus, not this run's data -
        # identical for every run of a given contract set, so they sit
        # beside the modules and the stylesheet rather than beside the
        # measurements.
        return len(page), len(schemas), len(html) - len(page) - len(schemas)

    def test_only_one_number_bounds_the_page(self, tmp_path):
        """`UX-367`: the clause the fix above is falsifiable by.

        Every bound in this class implies a maximum page size. There
        must be exactly one of those anybody has to reason about -
        `PAGE_BUDGET_B`, which has a stated procedure for moving and a
        record of every time it moved. A second, tighter one arrived by
        accident when the ratio was written against the **measured**
        page, and it took four rounds and a 78 B margin to notice.

        Asserted two ways, because the arithmetic one alone would pass
        a rewritten clause that reintroduces the disguise with a looser
        constant that later tightens.
        """
        import inspect

        _code, _contract, run_data = self._weigh(tmp_path)
        # `UX-444`: the constant, not a copy of it. It was a copy for
        # eight rounds - "it exists so the two ceilings cannot drift
        # apart silently, which means it moves whenever that one does" -
        # and a number kept in step by hand in three places is the drift
        # this repository fixes more often than anything else.
        implied = run_data / DATA_DWARFS_PAGE
        assert implied >= PAGE_BUDGET_B, (
            f"the ratio clause permits a page of {implied:,.0f} B while "
            f"PAGE_BUDGET_B permits {PAGE_BUDGET_B:,} B - the ratio is "
            f"the real ceiling again, and it is the one nobody wrote "
            f"down. Raise it or lower PAGE_BUDGET_B; do not leave two")

        source = inspect.getsource(
            TestTheSizeDiscipline
            .test_the_data_dwarfs_the_page_on_a_report_worth_measuring)
        claim = source.split("assert run_data", 1)[1].split(", (", 1)[0]
        assert "code" not in claim, (
            f"the ratio asserts against the measured page again "
            f"({claim.strip()!r}). On a fixture whose data is fixed by "
            f"construction that is an absolute page bound wearing a "
            f"ratio's name - assert against PAGE_BUDGET_B, which is the "
            f"page's one number")

    def test_the_data_dwarfs_the_page_on_a_report_worth_measuring(
            self, tmp_path):
        """Direction 7's sentence, on a report the sentence is about.

        The small fixtures invert it and always did - on `examples/06`
        the data is 70,754 B against an 82,386 B page - which is a
        property of small reports, not of the viewer, and is why the
        absolute ceiling was the wrong instrument.

        Measured at the scale the rule names (1,000 elements, the
        figure Direction 7 quotes at 1,202): **691,401 B of data
        against a 97,488 B page, 7.1x**. The threshold is set below
        the measurement so that ordinary growth does not trip it and a
        framework arriving does - a guard set at the measurement is a
        guard that fails on the next commit.

        **Re-measured at round 41** (`UX-303`), because it tripped:
        765,103 B of data against a 196,340 B page, **3.90x**. The page
        has doubled since the ratio was set and the data at this scale
        has not, so 4x no longer has headroom.

        **Re-measured at round 44** (`UX-320`), because it tripped
        again - and because the reason round 41 recorded was wrong.
        That note said "the export inlines every module verbatim,
        comments included ... 175 KB of the 196 KB page is commented
        JavaScript". It does not: `_uncommented` has stripped
        whole-line and block comments from the inlined copy since
        `UX-205`. Measured on this page:

        ```text
        page     223,276 B
          js     198,058 B   89%   trailing `//` comments ~114 B
          css     22,247 B   10%
          rest     2,971 B
        data     764,900 B   3.43x
        ```

        So the page is **code**, and `UX-307`'s remaining scope is the
        ~114 B of trailing comments plus whatever a real minifier would
        buy - not the 175 KB the old note promised. The threshold moves
        to **3.3x** with that correction, and the honest statement is
        that this ratio has now moved twice for one cause: the viewer
        grows features and the synthetic run's data does not grow with
        it. What the guard still catches is what it was built for - a
        framework arriving is hundreds of kilobytes of vendor code
        landing at once, which `test_no_module_looks_like_a_vendored_library`
        catches by shape and this catches by weight.

        **Round 45 (`UX-307`) took the trailing comments, and the
        estimate above was low: 153 B, measured, not ~114.** The
        threshold stays at 3.3x, and that is a deliberate refusal
        rather than an oversight. `UX-307`'s acceptance test asks for
        the ratio to be "restated upward with the new measurement",
        which was written when the item was believed to be worth
        175 KB. On this fixture it moves the ratio from 3.4266x to
        3.4289x - the fourth decimal place. Tightening a threshold on
        that would be manufacturing a significance the measurement
        does not have, and the next round to trip this guard would
        inherit a number nobody could account for.

        **Round 52 (`UX-342`) corrected what sits on each side, and the
        threshold moves with the classification rather than with a
        failure.** The embedded schemas were counted as *data*. They are
        not: they were byte-identical across two different runs, which
        is how `UX-342` found them, and a quantity that does not vary
        with the run belongs on the fixed side beside the modules and
        the stylesheet. So the ratio is the run's own data over
        everything that is the same for every run. Measured on this
        fixture, before and after that round:

        ```text
                             before      after
        page (modules, css)  228,291    228,291
        embedded schemas      83,669     43,981
        fixed cost           311,960    272,272
        run's own data       684,801    684,801   <- unchanged
        run data / fixed       2.195      2.515
        old data/page          3.366      3.192
        ```

        The numerator is identical because `UX-342` removed no data - it
        removed 39,688 B of contract for documents the page can never
        hold. Under the old metric that reads as a *regression*, which
        is the tell that the old metric was measuring the wrong thing.

        **`UX-343` moved it a second time in the same round, and twice
        is the signal to stop patching and measure the thing the guard
        is actually for.** Declaring a unit for every number means
        writing a sentence for each (`UX-220`), which grew the embedded
        contract by 23,011 B - so a rule that counts contract as fixed
        cost now falls whenever the schema says *more*, which is the
        opposite of what this guards.

        What it guards is a **framework arriving**: hundreds of
        kilobytes of vendor code landing at once. So the three
        quantities are separated and the ratio is the run's data over
        the viewer's **code** - not over the contract, which is prose,
        and not over both. Measured on this fixture across all three
        states:

        ```text
                            pre-UX-342   post-UX-342   post-UX-343
        code (modules, css)    228,291      228,291       228,423
        contract (schemas)      83,669       43,981        66,992
        this run's data        684,801      684,801       685,026
        data / code              2.999        2.999         2.999
        data / code+contract     2.195        2.515         2.319
        ```

        The code side is **invariant** across both rounds, because
        neither touched it - which is what a metric for "did the page
        balloon" should do. The combined ratio moves under both, in
        opposite directions, for reasons that have nothing to do with
        the page ballooning.

        The bound is **2.9x**. The contract's own size is reported in
        the failure message rather than bounded here: `UX-342`'s guard
        holds it to the schemas the page can resolve, and `UX-220`
        requires each to carry a sentence, so the two rules between them
        already say what it may contain.
        """
        code, contract, run_data = self._weigh(tmp_path)
        # `UX-348`: 2.8, measured at 685,355 B against 239,610 B of
        # code - 2.860x. The page grew 3,339 B for the worked Perfetto
        # example and the blast command an export can run; the run's
        # data did not move, because a linear chain of a thousand
        # elements publishes the same measurements either way. The
        # claim the bound carries is "the data dwarfs the page", and
        # 2.86x is what that looks like at this scale.
        #
        # `UX-356`: 2.6, measured at 685,355 B against 249,400 B -
        # 2.748x. Same run, same data, 5,606 B more page for the
        # element join's withheld fields. The claim still holds with
        # 175% of margin, and the bound is restated rather than the
        # sentences left unrendered to fit a number nobody argued.
        #
        # **Two rounds in a row have moved this in one direction**, and
        # against a synthetic run whose data is fixed by construction -
        # so the ratio measures the page alone and a third restatement
        # would make it a record of the page's growth rather than a
        # bound on it. That is `UX-360`'s volume budget, which is what
        # should catch the next one; this number is not it.
        #
        # `UX-367` took the note above at its word and found what it was
        # pointing at. On a fixture whose data is a constant,
        # `run_data > 2.6 * code` **is** an absolute page bound:
        #
        #     685,327 / 2.6  =  263,587 B of page, at most
        #     PAGE_BUDGET_B  =  265,000 B of page, at most
        #
        # Two absolute page bounds in one class, 1,413 B apart, and the
        # tighter one was the shadow - unnamed, unstated, and forbidden
        # by its own comment from being moved. `UX-369` landed 78 B
        # under it. The next viewer item would not have fitted, and the
        # failure would have read as a ratio when it was a byte count.
        #
        # So the page's size is `PAGE_BUDGET_B`'s job - one number, with
        # the procedure above for moving it - and this clause goes back
        # to asserting the claim it is named for, against the page the
        # backstop **permits** rather than the page that happens to be
        # here today. It can now fail for two reasons and both are worth
        # looking at: the analysis published less, or the permitted page
        # grew by a third. Neither is "a round landed".
        #
        # 2.5 rather than 2.6 because 2.5 is the largest round number
        # the claim carries against the permitted page: 685,327 against
        # 2.5 x 265,000 = 662,500, with 22,827 B to spare. This is a
        # restatement, and the reason is not that the page grew - it is
        # that the bound was two bounds and this was the wrong one.
        #
        # `UX-390`: 2.4. `PAGE_BUDGET_B` rose to 276,000 B and the
        # largest round number the claim still carries against the
        # *permitted* page is 2.4 - measured, 686,497 B of data against
        # 2.4 x 276,000 = 662,400, with 24,097 B to spare. That is the
        # procedure the paragraph above sets out, applied: the number
        # follows the backstop rather than the backstop being trimmed
        # to fit a ratio nobody argued, and `UX-367`'s clause below
        # holds the two from becoming two ceilings again.
        #
        # `UX-444` stopped applying that procedure. Eight restatements
        # in, every one of them `floor(run_data / PAGE_BUDGET_B)`, the
        # number was a transcription rather than a claim. It is now
        # `DATA_DWARFS_PAGE` - argued once, for what "dwarfs" means, and
        # not rewritten when the ceiling moves.
        assert run_data > DATA_DWARFS_PAGE * PAGE_BUDGET_B, (
            f"{run_data} B of this run's data against a page permitted "
            f"{PAGE_BUDGET_B} B ({run_data / PAGE_BUDGET_B:.3f}x, bound "
            f"{DATA_DWARFS_PAGE}x) - Direction 7's rule is that the data is "
            f"what an "
            f"export weighs, and at this scale it should not be close. "
            f"The page here measures {code} B and the embedded contract "
            f"{contract} B, which this ratio deliberately does not "
            f"count: it is prose, and it grows when the schema says "
            f"more. If the page is what moved, "
            f"`test_the_page_is_a_backstop_away_from_where_it_is` is the "
            f"clause that owns that")

    def test_the_page_is_the_modules_and_nothing_else(self, exported):
        """What the ceiling is really guarding: that the page is the
        checked-in modules plus the stylesheet, and that nothing else
        crept into it. A ceiling alone cannot tell 4 KB of new feature
        from 4 KB of vendored library; this can.
        """
        import tools.bga_view as view

        html = open(exported[0], encoding="utf-8").read()
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        accounted = sum(len(view._inline_module(name))
                        for name in view._module_order())
        accounted += len(view._uncommented_css(
            open(os.path.join(view.ASSET_DIR, "style.css"),
                 encoding="utf-8").read()))
        accounted += len(open(os.path.join(view.ASSET_DIR, "index.html"),
                              encoding="utf-8").read())
        # The export rewrites the page around those bytes, so an exact
        # equality would be asserting the glue. Anything the modules do
        # not account for is what this is looking for.
        assert len(page) - accounted < 4_000, (
            f"{len(page) - accounted} B of the page comes from neither "
            f"the modules nor the stylesheet")

    def test_the_page_itself_stays_within_its_budget(self, exported):
        """`UX-287`: the half of the size a run cannot change.

        The old backstop asserted a single constant against the golden
        export and had moved five times, always to accommodate the run
        it was measured against - a bound that rises whenever it is
        exceeded is a record, not a limit. Worse, it was measured on a
        **four-element** run, so it bounded the one quantity that barely
        varies while the quantity it was named for went unwatched.

        Measured across all three runs this repository can produce:

        ```text
        run             elements     bytes      data   modules     css   other
        golden                 4   294,976    98,361   175,182  19,585   1,848
        macro_micro           11   334,155   137,540   175,182  19,585   1,848
        ```

        The page is **196,615 B on every run**. That is the number a
        ceiling can honestly guard: it grows when *source* grows, and no
        amount of content can mask it. The totals below guard the other
        half, per fixture - so content can no longer hide behind the
        page, nor the page behind content.
        """
        page = exported[1]["bytes"] - _embedded(exported[0])
        assert page < PAGE_BUDGET_B, f"the page itself is {page} B"

    def test_the_page_costs_the_same_whatever_the_run(self, tmp_path):
        """What justifies splitting the bound in two. If the page's cost
        varied with the run, "the page" would not be a thing to bound
        separately and this whole structure would be wrong."""
        from tools.bga_view import export

        fixed = {}
        for label, run in (("golden", GOLDEN), ("macro_micro", MACRO_MICRO)):
            path = tmp_path / f"{label}.html"
            result = export(str(run), str(path))
            fixed[label] = result["bytes"] - _embedded(path)
        assert len(set(fixed.values())) == 1, (
            f"the page is not run-independent: {fixed}")

    @pytest.mark.parametrize("label,run,bound", COMMITTED_EXPORTS)
    def test_each_committed_run_exports_within_its_stated_bound(
            self, label, run, bound, tmp_path):
        """`UX-287`'s acceptance: the bound is asserted against a run
        whose size is representative, and it is stated *for that run*.

        **The decision the item asked for**, since the 11-element export
        is 288,404 B and the old ceiling was 260,000: the export is not
        too big. A self-contained HTML report at 288 KB - or at 1.04 MB
        for 1,202 elements - is well inside what a ticket or a mail
        client takes, and `tools/bga_view.py`'s own `EXPORT_BUDGET_B` of
        8 MiB is the limit that reflects the use. The old number was not
        a judgement about attachments; it was the size of a four-element
        run at the moment somebody wrote it down.
        """
        from tools.bga_view import export

        path = tmp_path / f"{label}.html"
        result = export(str(run), str(path))
        assert result["bytes"] < bound, (
            f"{label} exports {result['bytes']} B from a "
            f"{len(os.path.abspath(run))}-character run path, over its "
            f"stated {bound} B - see the note above on what the path costs")
        assert result["over_budget"] is False

    def test_the_data_is_the_documents_and_the_schemas(self, exported):
        """The backstop's other half, and the one that actually
        discriminates: every byte of embedded data is a document the
        page renders. A ceiling cannot tell 10 KB of new contract from
        10 KB of embedded font; this can, and it is why raising the
        ceiling above is a measurement rather than an argument."""
        import json

        html = open(exported[0], encoding="utf-8").read()
        blocks = re.findall(
            r"<script[^>]*type=\"application/json\"[^>]*>(.*?)</script>",
            html, flags=re.S)
        assert blocks, "no data blocks - the export stopped embedding"
        for block in blocks:
            # Every one parses as JSON. A blob that is not a document
            # would land here as something else.
            json.loads(block)
        data = sum(len(block) for block in blocks)
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        assert len(html) - len(page) - data < 4_000, (
            f"{len(html) - len(page) - data} B of embedded data is not one "
            f"of the JSON documents the page renders")

    def test_a_file_over_budget_is_reported_not_refused(
            self, snapshot, tmp_path, monkeypatch):
        import tools.bga_view as view

        monkeypatch.setattr(view, "EXPORT_BUDGET_B", 100)
        result = view.export(str(snapshot / "run"), str(tmp_path / "r.html"))
        assert result["over_budget"] is True
        assert os.path.exists(tmp_path / "r.html"), (
            "it refused to write a report the user asked for")


class TestTheCommandLine:
    def test_it_writes_the_file_and_says_where(self, snapshot, tmp_path):
        path = tmp_path / "out.html"
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["view", str(snapshot / "run"), "--export", str(path)],)],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
        assert result.returncode == 0, result.stderr
        assert path.exists()
        assert json.loads(result.stdout)["bytes"] == path.stat().st_size
        assert "needs no server" in result.stderr

    def test_it_never_starts_a_server(self, snapshot, tmp_path, monkeypatch):
        import tools.bga_view as view

        def refuse(*args, **kwargs):
            raise AssertionError("--export bound a port")

        monkeypatch.setattr(view.http.server, "ThreadingHTTPServer", refuse)
        monkeypatch.setattr(view.webbrowser, "open", refuse)
        assert view.main([str(snapshot / "run"), "--export",
                          str(tmp_path / "r.html")]) == 0


class TestTheCiWiring:
    def test_the_ci_docs_teach_attaching_it(self):
        text = open("docs/guides/ci-comment.md", encoding="utf-8").read()
        assert "--export" in text, (
            "the CI page posts the comment but never mentions the artifact")


_COMMON_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function makeNode(tag) {
  const node = _makeNode(tag);
  return node;
}
function collect(root) {
  const sections = [], classes = new Set(), severities = new Set();
  let text = "";
  (function walk(node) {
    text += " " + node.text;
    if (node.className) String(node.className).split(/\\s+/).forEach(c => c && classes.add(c));
    if (node.attrs["data-section"]) sections.push(node.attrs["data-section"]);
    if (node.attrs["data-severity"]) severities.add(node.attrs["data-severity"]);
    node.children.forEach(walk);
  })(root);
  return { sections, classes: [...classes], severities: [...severities], text };
}
"""

# The export is run the way a browser runs it: its own inline module,
# its own inline JSON blocks, no filesystem beyond the one file.
_EXPORT_HARNESS = _COMMON_SHIM + """
import { readFileSync } from "node:fs";
const html = readFileSync(%s, "utf-8");

const blocks = {};
for (const m of html.matchAll(
    /<script type="application\\/json" id="bga-([a-z]+)">([\\s\\S]*?)<\\/script>/g)) {
  blocks[m[1]] = m[2].replace(/<\\\\\\//g, "</");
}
const nodes = {};
for (const name of Object.keys(blocks)) {
  const node = makeNode("script");
  node.textContent = blocks[name];
  nodes[`bga-${name}`] = node;
}
const root = makeNode("main");
nodes["report"] = root;

globalThis.document = {
  createElement: makeNode,
  getElementById: (id) => nodes[id] ?? makeNode("div"),
};
globalThis.fetch = () => { throw new Error("the export fetched something"); };

const source = html.match(
  /<script type="module">([\\s\\S]*?)<\\/script>/)[1];
const mod = await import(
  "data:text/javascript;base64," + Buffer.from(
    source + "\\nexport { render, inlined, load };").toString("base64"));

// Through `load`, not `inlined`: the first draft rendered
// `inlined("report")` directly, so deleting the inline-first branch
// from `load` entirely left every render guard green - the loading
// path was never on the wire. `fetch` above throws, so anything not
// answered inline fails here.
const payload = await mod.load("report");
const schemas = await mod.load("schemas");
mod.render(payload, schemas[payload.schema], root);
console.log(JSON.stringify(collect(root)));
"""

_SERVED_HARNESS = _COMMON_SHIM + """
const payload = %s, schema = %s;
globalThis.document = { createElement: makeNode, getElementById: () => makeNode("div") };
const mod = await import("./tests/viewer.mjs");
const root = makeNode("main");
mod.render(payload, schema, root);
console.log(JSON.stringify(collect(root)));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
