"""UX-238: which tier each test file is in, measured rather than guessed.

Google's small/medium/large/enormous, adapted to what this suite
actually does. **The measured duration is the rule**; the descriptions
below say what tends to be slow, not what decides:

* **small** - pure Python over in-memory fixtures. No subprocess, no
  node, no real tool. The **default**: a file not listed below is
  small, which is right for 164 of 224 files.
* **medium** - spawns a process (the `bga` CLI, a node harness) or
  writes a run directory. Seconds, not milliseconds.
* **large** - builds scale fixtures, streams traces, drives real
  process trees. Tens of seconds each.
* **enormous** - needs a real `bst`/`bwrap` build. That tier already
  existed as the `bst` marker and keeps its name; `bst-tests` in CI is
  the job that runs it.

Measured with `pytest tests/ --durations=0`, summed per file over
setup+call+teardown, on the container that produced round 29:

```text
3102 passed, 3 skipped in 373.14s
160 files    18.2s   small    (5% of the time, 73% of the files)
 53 files   184.0s   medium
  7 files   159.0s   large    (43% of the time, 3% of the files)
```

Re-measured 2026-08-25 (round 39), after CI killed the small tier at
its 90s budget:

```text
small tier before   130.4s   24 files at or above the medium floor,
                             one of them 61.7s on its own
small tier after     16.4s   the same 2,431 tests, none of them moved
                             out of the suite - only out of the tier
```

The drift is the mechanism working as designed and nobody reading it:
a file joins `small` by default, so twenty-four of them crossed the
floor one at a time and only the aggregate budget could see it. It saw
it.

Re-measured 2026-08-27 (round 47, `UX-336`), and the same drift had
happened again — fourteen files over the medium floor, one of them
above the *large* one:

```text
small tier before   81.7s test time, 33s wall at -n auto   103 files
small tier after    35.5s test time, 11s wall at -n auto    89 files
```

The whole suite moved with it, and the parallelism is the larger half:

```text
full suite, single process   642s   4,131 passed, 18 skipped
full suite, -n auto          194s   4,131 passed, 18 skipped   3.3x
skip census                  identical between the two, reason for reason
```

Re-measured 2026-08-28 (round 56), and CI caught it the way the design
says it should — the small tier's own timeout, not a review:

```text
                  wall at -n auto   wall single-process   CI budget
small tier before           74.3s                236.4s    90s / 120s
small tier after             8.6s                 22.3s
```

Both CI steps were over, not just the one that reported: the parallel
step is budgeted at 90s and the single-process step at 120s, and the
tier was at 74s and 236s. The parallel step failed first and `bash -e`
stopped the job before the second could say so.

Twelve files, and this time the cause has a name rather than being
twelve independent drifts. `UX-359` ruled that a guard measures the
page a *user* gets — an exported page, booted in a real Chromium — and
converted fourteen guards to it. That is the right rule and it is why
round 55's defects were findable at all; it also means those files now
do what `test_the_page_has_geometry.py` does, and belong where it is.
The twelve were 213s of the tier's 214s: every other file in the
default tier is under a second, so the split is not a judgement call.

`-n auto` is how every tier runs now (`make`'s `PYTEST_XDIST`). The
tiers still matter: they are what `make test-small` selects, and 11s is
a different kind of loop from 33s.

**The lists are the exceptions, not the taxonomy.** Adding a test file
costs nothing here unless it is slow, and a slow one that is not listed
is caught by the small tier's own wall-clock budget rather than by
review - see `test_the_tiers_are_a_partition.py`.

A file moves tier when its *measurement* moves, not when it feels
slower. Re-measure with the command above before editing either list.
"""
import pathlib
import re

# Above this, a file is `large`. Below `MEDIUM_CEILING_S`, it is small.
LARGE_FLOOR_S = 15.0
MEDIUM_FLOOR_S = 1.0

# `UX-522`: the census set - guards whose subject is the **tree**, so
# no diff can point at them. `dev_touching.py` unions these into every
# selection, because a grep from the diff can never reach them and
# round 75 measured what that cost: of five defects the per-item suite
# caught, `test-touching` could not have named two, and both were this
# class (`UX-503`'s register cap, `UX-502`'s skip census - the first
# and second rows below by that route).
#
# Derived, not typed. `test_the_selector_carries_the_census.py` recomputes
# it: a file that walks a path rooted at the repository **and** that a
# grep from any non-`__init__` source module never selects. Adding a
# guard of this shape without listing it here reddens that file.
#
# Measured: 272 tests, **10.80s at `-n auto`** - what every
# `test-touching` run now pays to stop being wrong about this class.
CENSUS = (
    "tests/unit/test_a_guard_reads_only_what_a_clone_has.py",
    "tests/unit/test_capture_ref_patterns.py",
    "tests/unit/test_every_direction_names_its_reader.py",
    "tests/unit/test_every_skip_reason_is_declared.py",
    "tests/unit/test_one_factory_builds_every_table.py",
    "tests/unit/test_the_agent_configuration_holds.py",
    "tests/unit/test_the_canned_prose_reads_as_written.py",
    "tests/unit/test_the_dom_shim_is_one_instrument.py",
    "tests/unit/test_the_palette_is_validated.py",
    "tests/unit/test_the_register_is_terse.py",
    "tests/unit/test_the_viewer_modules_have_a_home.py",
)


# `UX-418`: **the floors are seconds on one machine, and a report from
# another cannot be compared to them.** Not in any form.
#
# The numbers beside every entry below were measured on a developer
# container. Three CI runs of the drift step taught, in order, that they
# do not travel:
#
# 1. It called three medium files large at 20.4-21.5s; here they are
#    11.3-13.5s single-process. A fixed slack was the first answer, and
#    was wrong by a factor on the first foreign clock it met.
# 2. A scale derived from the report was the second answer, and is
#    wrong too. Measured on CI, the **median** listed file runs at
#    1.05x its recorded number - while `test_report_stays_readable_at_scale`
#    runs at 1.61x and `test_marginal_efficiency_gate` at 1.73x. Neither
#    had grown: here they are 1.05-1.10x their records. The difference
#    is *per file*, so no single scale exists to find.
#
# 3. Comparing **rank** rather than seconds was the third answer, on the
#    argument that the order survives a change of machine. It does not:
#    `test_report_stays_readable_at_scale` is recorded below all 22
#    `LARGE` files here, and on CI it read 25.3s - above 11 of them.
#
# `UX-420` could not reconcile the two figures in 2 and 3. Its file,
# `tests/unit/test_output_schemas.py`, is recorded at 5.7s below, and
# re-measured single-process while UX-420 was being written it read
# 7.1s wall - so CI's 25.3s is x3.5-4.4 of the record, not the x1.61
# item 2 states. One of the two was taken over the file and the other
# over the single test, or the -n auto contention on the runner is not
# uniform across a file; nothing in the repository says which, and
# settling it needs another CI run rather than a re-reading.
#
# **Neither conclusion rests on the figure.** Item 2 is a statement
# about the *spread* between the median and the outliers, which three
# separate ratios support, and item 3 needs only that the ordering
# changed. `UX-420`'s rule reads neither number: it compares CI to CI,
# and never opens this file's records at all.
#
# So the check against these floors runs where they mean something
# (`make test-tiers`) and not in CI, where these seconds describe a
# different machine. That is the distinction this file already drew
# once and `UX-418` had to learn again.
#
# For three rounds `SMALL_TIER_BUDGET_S` below was the CI-side guard
# that did the work, sized against CI's own clock. `UX-421` retired it:
# a wall-clock step budget cannot separate *a runner four seconds
# slower than its siblings* from *a fifteen-second file in the default
# tier*, and by round 67 its window was a second wide either side. It
# is now `SMALL_TIER_BACKSTOP_S`, a hang-catcher, and the per-file rule
# below does the job it was doing.
#
# `UX-420` gave CI the other half - `tests/ci_reference.json`, one full
# run's per-file totals taken *on the runner*, so a later run is read
# against CI rather than against these numbers. One machine against
# itself over time is the only comparison the three failures above
# leave standing.


def recorded():
    """`{path: seconds}` for every listed file, read off its own line.

    Every entry in `LARGE` and `MEDIUM` carries the measurement that put
    it there as a trailing comment, and has since `UX-238` - the lists
    have always been a record as well as a selector. `UX-418` made the
    record readable, because a step comparing a foreign clock to these
    floors needs the numbers the floors were taken with.

    Parsed from this module's own source rather than kept in a second
    structure: two copies of a measurement is how the copies disagree,
    which is the defect `test_the_tiers_are_a_partition.py` exists for
    one level up.
    """
    source = pathlib.Path(__file__).read_text(encoding="utf-8")
    return {found.group(1): float(found.group(2)) for found in
            re.finditer(r'^\s*"(tests/[^"]+)",\s*#\s*([\d.]+)s\s*$',
                        source, re.M)}

# `UX-363`: the two wall-clock budgets, and the measurement they are
# sized against.
#
# The budgets are CI timeouts, so they are set from **CI's** clock, not
# this container's. Measured on the last green run before this item
# (`209812e`, `test (3.12)`), beside the same tier locally:
#
# ```text
#                       CI       local    ratio
# parallel (-n auto)  23.76s      8.5s     2.8x
# single process      21.37s     21.7s     1.0x
# ```
#
# Parallel is *slower* than single-process on CI, which is why the two
# numbers below are not ordered the way they read: a two-core runner
# spends more on four workers than it saves. Locally the ratio is 2.6x
# the other way. A single budget for both would therefore be sized
# against a machine neither step runs on.
#
# **What sizes them.** For three rounds the budget stayed at 90s while
# each re-tier moved the tier further below it, until a file two large
# floors over could land in the default tier and trip neither step. So
# the rule is now stated as an inequality and *checked*, in
# `test_the_tiers_are_a_partition.py`:
#
#   measured  <  budget  <  measured + LARGE_FLOOR_S
#
# The left half says the budget is reachable in normal running; the
# right half says one large file landing in the default tier trips it,
# which is the whole job. Both budgets carry ~1.5x of the measurement,
# and re-measuring is what moves them - not a commit that needed room.
# Two numbers per step, not one, because the runner varies. The first
# green run under these budgets came in at 20.5s and 13.8s against the
# 23.8s and 21.4s measured the run before - a 1.5x spread on the same
# step. Each half of the inequality needs the measurement that makes it
# hard:
#
# * `slowest < budget` - checked against the **slowest** run, or the
#   budget reds on an ordinary bad day.
# * `budget < fastest + LARGE_FLOOR_S` - checked against the **fastest**
#   run, or a large file slips into the default tier on a good one.
#
# A single measurement satisfies the first and quietly fails the second,
# which is this item's own defect one level down: the bound looked sized
# because it was compared against the number that made it look sized.
#
# The two together leave a window, and the budget goes inside it rather
# than at either edge - at an edge, one ordinary run either reds the
# build or reds this guard:
#
# ```text
#             window                    chosen
# parallel    (23.8, 35.5)                33.0
# 1 proc      (21.4, 28.8)                27.0
# ```
#
# **Re-measured 2026-08-29, on all four interpreters of one CI run**
# (round 61, PR #177). The figures above were taken at `UX-363`'s own
# landing; the tier has since grown from 2,486 tests to 2,595, and the
# single-process step hit `timeout 27` on `test (3.9)` - killed with
# the last file at 100%, so its true figure is above 27.0 and unknown.
# Every number below is one green step's own summary line:
#
# ```text
#          parallel (33)   1 proc (27)
# 3.9          25.23        killed at 27.0
# 3.10         25.85          25.83
# 3.11         23.91          23.13
# 3.12         17.34          17.03
# ```
#
# Two things that table says, beyond the failure that produced it.
#
# **The two steps now cost the same.** The comment in `ci.yml` has the
# single-process step as the faster of the two - 13.8-21.4s against
# 20.5-23.8s, "on a two-core runner four workers cost more than they
# save". On this run they are within a second of each other on every
# interpreter and `-n auto` is the *slower* of the pair each time. The
# premise held when the tier was 2,486 sub-second tests; it does not
# now, and the two budgets are correspondingly close rather than six
# seconds apart.
#
# **The window is closing, and it is arithmetic rather than bad luck.**
# `slowest < budget < fastest + LARGE_FLOOR_S` has a solution only
# while `slowest - fastest < LARGE_FLOOR_S`, and the spread between the
# slowest and fastest run above is 8.8s of a 15.0s floor. It is the
# *spread*, not the total, that closes this: the small tier can grow
# for a long time yet, but the day two jobs of one run are fifteen
# seconds apart, no budget satisfies both halves. Written down here so
# the round that meets it recognises it.
#
# **The spread is the runner, not the interpreter.** The first draft of
# this note read the table above as a per-interpreter ranking - 3.12
# fast, 3.9 slow - and proposed stating the budget per interpreter when
# the window closes. The very next run, green under these budgets,
# falsified it:
#
# ```text
#          parallel (31)   1 proc (30)      1 proc, the run before
# 3.9          22.74          24.59          killed at 27.0
# 3.10         21.16          19.60          25.83
# 3.11         21.52          21.43          23.13
# 3.12         23.60          23.50          17.03
# ```
#
# 3.12 was the fastest of the four at 17.03 and is the second slowest
# at 23.50; 3.10 was the slowest at 25.83 and is the fastest at 19.60.
# The ordering did not survive one run, so what these numbers measure
# is which runner a job landed on. Two consequences, both load-bearing
# for whoever re-sizes next: a single run's fastest and slowest are one
# sample of the runner population rather than four samples of four
# interpreters, and a budget stated per interpreter would guard nothing
# it does not already guard. Re-measure across runs, and keep the
# extremes of all of them - which is what the constants below hold.
#
# The one claim the second run did strengthen is the other one: the two
# steps cost the same. Which of the pair is slower flipped between them
# (3.9 and 3.11 have `-n auto` faster, 3.10 and 3.12 slower), and the
# gap is under 1.6s everywhere.
#
# **Round 66 met a third runner, and the single-process step was
# killed at 30.0.** Run 33303144837, head `0ace86b`, `test (3.9)`. Read
# off the **job step timings** rather than pytest's summary line, which
# is the instrument these constants should have been using all along -
# see the note on units below:
#
# ```text
#          parallel (31)   1 proc (30)     runner
# 3.9          29             30, killed   ...2871
# 3.10         27             26           ...2872
# 3.11         23             26           ...2870
# 3.12         19             19           ...2874
# ```
#
# Three interpreters passed the same step on the same commit, so this
# is the runner rather than the tier - the conclusion the previous
# round already reached and this run confirms with a third sample. The
# tier did grow slightly in round 66 (`UX-419` and `UX-420` add about
# fifteen sub-second tests to 2,790), which is nowhere near the 4s
# between 3.9 and its siblings.
#
# **A units defect, found here and worth stating.** Every figure above
# this round came from pytest's own summary line, and the thing the
# budget bounds is the *step*, which also pays for `make`, collection
# and interpreter start - about 0.6s on 3.9, whose step read 30 while
# its summary line read 29.36. So the recorded population and the
# quantity being bounded were never the same measurement, and the gap
# always ran the wrong way: the constants under-stated what the timeout
# actually has to clear. The table above is step seconds; the two
# `_S` constants below are now step seconds too, and the `_FAST_`
# pair is left at its pytest-line value because converting a number
# nobody re-measured would be inventing one - it is the conservative
# direction, since a smaller fastest only tightens the upper bound.
#
# ```text
#             window                    chosen     margin
# parallel    (29.0,  32.34)              32.0     3.0 / 0.34
# 1 proc      (30.0,  32.03)              31.0     1.0 / 1.03
# ```
#
# **The window was about a second wide on both steps**, which is the
# closing this file predicted above ("written down here so the round
# that meets it recognises it") arriving one round later. It never
# quite closed arithmetically - `slowest - fastest` is 11.7s and 13.0s
# against a 15.0s floor - and `UX-421` did not wait for it to. A budget
# with a second of headroom either side is one slow runner from red and
# one re-tier from unsatisfiable, and the deeper problem is that no
# width of window would have helped: the quantity being bounded moves
# for two different reasons and the bound cannot tell them apart.
#
# The table above is kept as the record of what was measured. It is no
# longer what sizes anything - see `SMALL_TIER_BACKSTOP_S` below.
#
# The extremes of all three runs above, which is the whole population
# these constants have. Named by the job that produced each, not
# because the interpreter is the cause - see the note about the runner
# - but so a later reader can find the log.
SMALL_TIER_CI_SLOW_S = 29.0       # parallel, `-n auto`, slowest seen (3.9)
SMALL_TIER_CI_FAST_S = 17.34      # parallel, fastest seen (3.12)
# A floor, not a measurement: `test (3.9)` was killed at this value
# with the run at 100%, so the figure this constant wants is somewhere
# above it. That has now happened twice - at 27.0 and again at 30.0 -
# and a killed run still proves the tier once cost more than the number
# it was killed at, which is what a budget has to clear.
SMALL_TIER_CI_SLOW_1P_S = 30.0    # single process, slowest seen (3.9)
SMALL_TIER_CI_FAST_1P_S = 17.03   # single process, fastest seen (3.12)

# `UX-421`. **These are backstops, not budgets.** The distinction is
# the whole item: a budget claims to bound the tier, and a wall-clock
# step timeout cannot, because two different causes move it the same
# way. Round 66 met the proof - `test (3.9)` was killed at 30s while
# 3.10, 3.11 and 3.12 passed the same step on the same commit at 26,
# 26 and 19s. Nothing about the tier differed between those four jobs.
#
# Sized to catch a hang and nothing finer: about four times the
# slowest step ever seen (30.0s), and far enough below the job's own
# timeout that it fails fast with a legible message instead of burning
# six minutes. A number in this range needs no re-measuring when the
# tier grows by a second, which was the maintenance the old budget
# demanded every re-tier.
#
# **What actually catches a large file in the default tier** is
# `tools/dev_tier_drift.py --against`, run in CI on the 3.11 job. It
# compares each file to CI's own recorded seconds with the run's median
# shift divided out, so a slow runner is not read as a slow file - and
# it names the file, which a timeout never could.
SMALL_TIER_BACKSTOP_S = 120.0     # the `-n auto` step's timeout
SMALL_TIER_BACKSTOP_1P_S = 120.0  # the single-process step's timeout

# The sizing this replaced, kept because it is the argument `UX-421`
# had to answer rather than a number to restore. The old budget was
# falsified with the smallest `LARGE` file (16.4s) moved into the
# default tier, on CI against the *fastest* run:
#
# ```text
#                        local        on CI at its fastest
# parallel   8.5 + 16.4 = 24.9s  <31   17.34 + 16.4 = 33.7s >31   caught
# 1 proc    23.9 + 16.4 = 40.3s  >30   17.03 + 16.4 = 33.4s >30   caught
# ```
#
# That inequality worked, and it is not what failed. What failed is
# that satisfying it also required the budget to sit *below* the
# slowest ordinary run, and by round 66 the two constraints left about
# a second between them - so an unlucky runner and a mis-tiered file
# produced the same red. The per-file rule has no such problem: it
# divides the runner out before it looks at any file.

LARGE = (
    # `UX-435`, then `UX-451`. It was medium at 14.2s - "just under the
    # large floor", which is a note about a file one clause from
    # crossing it. `UX-451` added the refused state: a second served
    # page, a second browser, and eight clauses over two viewports.
    # Measured on the same machine either side, 14.22s -> 28.78s, so it
    # is large now by its own measurement rather than by feel.
    "tests/unit/test_the_handoff_box_is_measured_served.py",         #   28.8s
    # `UX-402`: the documented journey, walked. One cold `bst build`
    # against an isolated artifact cache (so the durations are real),
    # one incremental, then analyze, correlate, export and a browser.
    "tests/unit/test_the_journey_has_an_answer_key.py",              #   50.0s
    # `UX-418`'s first catch, and the reason that item exists. All three
    # were listed medium and had grown past the large floor, and nothing
    # said so: `test_the_tiers_are_a_partition.py` reads the lists
    # against each other, not against a clock. Re-measured
    # single-process, which is what the `measure` skill's recipe uses -
    # the CI report is `-n auto` and reads 5-9% higher on these three.
    "tests/unit/test_the_chain_folds_and_clicks_are_counted.py",     #   24.5s
    "tests/unit/test_any_element_can_be_inspected.py",               #   16.6s
    "tests/unit/test_the_handoff_has_a_fixture.py",                  #   15.5s
    # UX-257's geometry instrument: a real Chrome over CDP, an exported
    # report per class, and every claim measured at three viewports. It
    # was never listed, so it sat in the default tier at 42.6s and then
    # at 61.7s once `UX-285` and `UX-286` added fourteen checks - which
    # is what finally blew the small tier's budget in CI. The file is
    # four times the large floor on its own.
    "tests/unit/test_the_page_has_geometry.py",                      #   61.7s
    "tests/unit/test_process_spine.py",                              #   35.8s
    "tests/unit/test_spine_ground_truth.py",                         #   26.9s
    "tests/unit/test_analysis_memory_shape.py",                      #   24.6s
    "tests/unit/test_trace_stream_and_census_scale.py",              #   19.4s
    "tests/unit/test_snapshot.py",                                   #   18.9s
    "tests/unit/test_cache_logs.py",                                 #   18.2s
    "tests/unit/test_doctor.py",                                     #   15.4s
    # UX-336, re-measured 2026-08-27: the drift the aggregate budget
    # hides, again. `UX-317`'s apparatus checks boot the exported page
    # once per claim and had reached the large floor while sitting in
    # the default tier - the same mechanism round 39 documented, three
    # rounds later.
    "tests/unit/test_apparatus_in_its_place.py",                     #   17.4s
    # UX-334's console net: four boots of a real Chromium - two fixture
    # runs, served and exported - and three positive controls that each
    # start a browser of their own to prove one channel of the
    # instrument can still hear. Measured at 13.8s with two controls and
    # 16.4s with the third, which is what moved it over the floor.
    "tests/unit/test_the_console_stays_clean.py",                    #   16.4s
    # Round 56, re-measured after `UX-355`..`UX-361` landed. Twelve
    # files had drifted over the medium floor, seven of them over the
    # large one, and together they were 213s of the small tier's 214s -
    # every other file in the default tier is under a second. The
    # mechanism is the one round 39 and round 47 both documented, and
    # the cause this time is named: `UX-359` made every page guard boot
    # a real Chromium against an exported page, which is precisely the
    # character of the three files above it. A browser boot per claim
    # is a large test; the tier is where that gets said.
    "tests/unit/test_a_control_acts_on_what_it_names.py",             #   30.0s
    "tests/unit/test_the_two_capabilities_are_offered.py",            #   27.9s
    "tests/unit/test_the_vocabulary_has_the_shape.py",                #   25.0s
    "tests/unit/test_the_provenance_names_its_rule.py",               #   22.7s
    "tests/unit/test_a_sentence_lives_on_its_door.py",                #   20.2s
    "tests/unit/test_the_shape_channel_is_built.py",                  #   19.8s
    "tests/unit/test_the_tools_scale_with_the_table.py",              #   16.8s
    # `UX-367` moved this one across the floor by adding the size it
    # was missing: the volume budget now boots the seeded 1,202-element
    # run beside the two fixtures, which is a `gen-synthetic`, a
    # 1.16 MB export and a third browser page. 11.5s -> 22.3s, and the
    # cost is the whole point of the item - a budget that never met the
    # page is cheaper and worth nothing.
    #
    # `UX-526` added the second size the item is about - the seeded
    # 4,002-element run, a second `gen-synthetic` and a fourth browser
    # page - and the file triples: **22.3s -> 65.0s**, measured alone
    # in one process on this machine. The track that wrote it measured
    # 127s in a worktree under four parallel tracks; both are this
    # file, and the quiet number is the one the floors are made of.
    "tests/unit/test_the_page_has_a_volume_budget.py",                #   65.0s
    # `UX-455`. Listed medium at 13.5s when `UX-394` wrote it - a
    # three-snapshot store, served, four browser boots and one export.
    # Nothing since has been *about* it; it is the browser boots that
    # have grown under it. Re-measured alone in one process, three
    # runs: 18.30 / 18.33 / 18.28s, so it is past the 15.0s large floor
    # by three seconds rather than by a hair.
    "tests/unit/test_the_page_moves_between_runs.py",                #   18.3s
    # `UX-527`, and the round that tripped over it is this one. The
    # note this row carried in `MEDIUM` said "14.7s against a large
    # floor of 15.0 - one more browser clause moves this file"; the
    # item added the 4,002-element clauses that tell a picker offering
    # eight from one offering four thousand, and **54.1s** is where it
    # landed, measured alone in one process. The prediction was right
    # and the row is where it belongs.
    "tests/unit/test_the_query_asks_about_this_run.py",              #   54.1s
    # `UX-529`, large on landing and for one reason: the defect is
    # invisible below a thousand elements, so the population is the two
    # committed fixtures **and** the two seeded runs the volume budget
    # uses. Two `gen-synthetic` calls and four exports, the 4,002 one
    # 17s of them; no browser. Measured alone in one process, twice:
    # 44.74 / 40.87s.
    "tests/unit/test_the_exports_data_half_has_a_budget.py",         #   40.9s
)

MEDIUM = (
    "tests/unit/test_a_broken_pipe_is_not_an_error.py",             # 1.6s
    "tests/unit/test_a_pasted_guide_block_is_fresh_or_dated.py",    # 3.6s
    "tests/unit/test_the_documented_bga_lines_parse.py",            # 2.0s
    # `UX-545`, tiered on landing. A real two-plane render with the
    # ceiling monkeypatched under both rungs, then the exported page
    # booted - so `bga view` and node, twice over. Measured here on a
    # quiet 4-core box, single process: 2.65 / 2.51s, and the track
    # that wrote it read 2.51s.
    "tests/unit/test_a_refused_timeline_says_it_was_refused.py",    #    2.5s
    # `UX-455`, tiered on landing, and it earned the tier the way the
    # item is about: two clauses run the confirmation for real, which
    # is a pytest subprocess each. Three single-process runs:
    # 1.22 / 1.25 / 1.24s.
    "tests/unit/test_the_browser_waits_for_a_condition.py",         #    2.6s
    # `UX-528`, tiered on landing. A store of N golden runs, served,
    # and the window read at three populations - so a browser, and
    # `bga view` in front of it. **13.4s** alone in one process, which
    # is 1.6s under the large floor; the track that wrote it measured
    # 18s under this round's parallel load and called it large. Medium
    # is what the quiet machine says, and the margin is small enough
    # that the next clause moves it.
    "tests/unit/test_the_store_section_takes_a_window.py",          #   13.4s
    # `UX-520`, tiered on landing. Nineteen clauses, each packing and
    # unpacking a real gzipped tar of a small capture, two driving the
    # CLI end to end. Three single-process runs: 1.84 / 2.97 / 2.27s.
    "tests/unit/test_a_run_bundle_you_can_carry.py",                #    2.3s
    # `UX-535`, tiered on landing. Eleven clauses, one of them a
    # subprocess `analyze` over the golden fixture. 4.27s measured.
    # `UX-539` follow-up. An AST walk of every file in `bga/` and
    # `tools/` - 3.50 / 3.66 / 3.83s measured alone in one process.
    "tests/unit/test_the_package_runs_on_the_python_it_claims.py",  #  3.7s
    "tests/unit/test_one_fact_is_published_once.py",                #    4.3s
    "tests/unit/test_a_candidate_is_confirmed_alone.py",            # 1.2s
    # `UX-460`, tiered on landing. It runs `analyze` in-process over
    # every committed capture in the tree - seven of them now - which
    # is the census itself and not overhead. Three single-process runs:
    # 1.09 / 1.22 / 1.14s, over the 1.0s medium floor on every one.
    "tests/unit/test_every_finding_reaches_a_fixture.py",           # 1.2s
    # `UX-455`. Was in the default tier and never listed. Re-measured
    # alone in one process, three runs: 1.35 / 1.34 / 1.37s, over the
    # 1.0s medium floor on every one. It renders every documented
    # command and parses each back, which is a subprocess per command
    # rather than anything a browser does.
    "tests/unit/test_a_command_renders_as_a_command.py",            # 1.4s
    # `UX-443`, tiered on landing. Two real servers on a socket and
    # two full trace renders over a committed capture. 2.8s.
    "tests/unit/test_the_served_handoff_counts_its_edges.py",       # 2.8s
    "tests/unit/test_the_served_scratch_is_not_leaked.py",          # 1.6s
    # `UX-449`, tiered on landing. It parses every test source in the
    # suite - 195 skip call sites over ~380 files - which is why it is
    # seconds rather than milliseconds despite running no build and
    # opening no browser. 3.2s.
    "tests/unit/test_every_skip_reason_is_declared.py",            # 3.2s
    # `UX-436`, tiered on landing. One `gen-synthetic` run, two
    # exports and one browser reading the computed appearance of every
    # button on both - 1,591 of them on the scale page, which is where
    # the fourth grade appears at all. 6.7s.
    "tests/unit/test_every_control_has_a_resting_appearance.py",   #  6.7s
    # `UX-433`, tiered on landing. One `gen-synthetic` run and one
    # render of a 1,202-element two-plane snapshot, then the pivot
    # queries against a SQLite table. 1.6s.
    "tests/unit/test_the_build_pivots_by_program.py",             #  1.6s
    # `UX-430`, tiered on landing. Two `gen-synthetic` runs and six
    # renders of a 1,202-element two-plane snapshot - the size the
    # track bound is measured at, which is the whole point of the
    # file. 4.6s.
    #
    # Re-measured by `UX-530`, which added a clause here: **10.97s**,
    # of which 0.57s is that clause. The recorded 4.6s was 5.8s stale
    # before this round touched it - the renders grew under it, which
    # is `UX-455`'s shape. Still MEDIUM, and now by a measurement.
    "tests/unit/test_the_handoff_counts_what_perfetto_spends.py",  # 11.0s
    # `UX-370`, tiered on landing. One boot of `macro_micro` - the only
    # committed fixture with a Plane 2 report beside its run - plus
    # four payload clauses that need no browser at all. 2.2s.
    "tests/unit/test_plane_two_says_what_it_ran.py",              #    2.2s
    # `UX-366`, tiered on landing. One boot of the seeded 1,202-element
    # run, every population driven twice - at rest and on "All rows" -
    # in a single measure call. 8.2s, most of it the generate and the
    # export.
    "tests/unit/test_all_rows_means_all_rows.py",                #    8.2s
    # `UX-368`, tiered on landing. Four browser clauses over the three
    # committed captures - `with_timeline` for the page that has a
    # handoff, the other two for the dead-control rule. 7.6s.
    "tests/unit/test_a_finding_reaches_the_timeline.py",         #    7.6s
    # `UX-364`, tiered on landing rather than after CI noticed - which
    # it did, at 96% of `timeout 33 make test-small`. Four page exports
    # and eleven clauses over a real Chromium; measured at 10.3s, which
    # is `UX-359`'s rule costing what it costs. The file that measures
    # the page a user gets is a medium test by construction, and this
    # list is where that gets said rather than rediscovered.
    "tests/unit/test_the_lead_names_the_planes_it_has.py",       #   10.3s
    # `UX-372` and `UX-373`, tiered **after** CI noticed - which is the
    # part worth recording. Both landed in the default tier and neither
    # was measured on landing, and the two of them put the small tier
    # at 13.3s parallel and 32.0s single-process against budgets of 33s
    # and 27s. `test (3.9)` and `test (3.10)` hit `timeout 33` at 95%;
    # 3.11 and 3.12 got under it on faster runners, so the tier was
    # already over on the two-core ones before anything reported.
    #
    # `UX-364`'s note four lines up says the same thing about the same
    # mistake one round earlier. Two rounds running, so it is the
    # default that is the trap rather than either author: a file that
    # boots a page belongs here by construction, and the cost of
    # forgetting is a red CI on somebody else's clock.
    "tests/unit/test_the_page_has_a_reader.py",                  #    6.3s
    "tests/unit/test_one_page_behind_the_button.py",             #    4.4s
    # `UX-374`, tiered on landing - which is what the note above says
    # to do. Two exports booted in a real Chromium plus seven node
    # clauses on `format.js`; 4.2s.
    "tests/unit/test_the_page_keeps_the_names_it_was_given.py",  #    4.2s
    # Round 56, the other five of the twelve (see the LARGE block
    # above): over the medium floor, under the large one.
    "tests/unit/test_the_guards_measure_the_page.py",            #   11.5s
    "tests/unit/test_the_merge_carries_every_field.py",          #    8.7s
    "tests/unit/test_the_label_is_for_the_reader.py",            #    6.4s
    # Re-measured 2026-08-25 (round 39). Twenty-four files had drifted
    # over the medium floor while staying in the default tier: the
    # budget is an aggregate, so each one was invisible on its own and
    # together they were 114s of the small tier's 130s. Every line below
    # carries what it measured at.
    # UX-296's big-run fixture: a million process records written to
    # disk, and four subprocess startups measured against it.
    # Round 48, measured on landing rather than after the drift: both
    # of these are subprocess-heavy by construction, and `UX-336`'s
    # lesson is that a file joins `small` by *default* - so the tier is
    # chosen when the file is written, not when the budget notices.
    # The small tier went 23.6s -> 46.2s with these two in it.
    "tests/unit/test_one_bad_row_costs_one_section.py",         #   11.3s
    "tests/unit/test_every_emitted_contract_is_answerable.py",  #    9.0s
    "tests/unit/test_the_view_parses_nothing.py",               #    7.6s
    # Round 50, tiered on landing for the same reason: four `bga analyze`
    # subprocesses, three of them `--format json --explain`.
    "tests/unit/test_the_readme_block_is_the_real_output.py",   #    1.2s
    # `UX-330`'s walk: a seed planted once, then ten `bga` subprocesses
    # run against it - the whole point is that it is not in-process.
    "tests/unit/test_the_stranger_has_a_seed.py",               #    5.6s
    # UX-298's emitter: a 40,000-process trace written twice, once for
    # the ceiling and once for the bytes-before-close clause.
    "tests/unit/test_the_timeline_speaks_perfetto.py",           #    6.0s
    "tests/unit/test_one_table_many_views.py",                  #    8.1s
    # `UX-414` gave it a second fixture: three of its clauses boot the
    # two-plane export as well as the single-plane one, which is where
    # `restructuring` and `binary_cost` exist at all. That took it to
    # 15.9s - over the large floor - and `UX-418`'s new step is what
    # said so. One export and one boot per fixture now, cached.
    "tests/unit/test_the_report_has_chapters.py",               #    4.9s
    "tests/unit/test_a_table_cell_obeys_the_value_rule.py",     #    3.2s
    "tests/unit/test_a_control_says_what_it_does.py",           #    2.7s
    "tests/unit/test_every_table_has_its_own_state_key.py",     #    1.5s
    "tests/unit/test_findings_carry_their_evidence.py",         #    1.5s
    # `UX-343`: five node subprocesses, one per census. Tiered on
    # landing rather than after the drift - `UX-336`'s rule.
    "tests/unit/test_every_number_says_what_it_is.py",          #    1.3s
    "tests/unit/test_the_structural_block_is_reachable.py",     #    1.5s
    "tests/unit/test_dev_run_script.py",                        #    1.4s
    "tests/unit/test_focused_graphs_not_a_dag_viewer.py",       #    1.4s
    "tests/unit/test_a_value_shows_what_it_is.py",              #    1.4s
    "tests/unit/test_element_kind_heuristics.py",               #    1.4s
    "tests/unit/test_logging_and_exceptions.py",                #    1.3s
    "tests/unit/test_capture_diagnostics.py",                   #    1.3s
    "tests/unit/test_correlate.py",                             #    1.2s
    "tests/unit/test_focus_and_the_working_set.py",             #    1.2s
    "tests/unit/test_the_tiers_are_a_partition.py",             #    1.2s
    "tests/unit/test_ci_comment.py",                            #    1.1s
    "tests/unit/test_open_window_flush.py",                     #    1.1s
    "tests/unit/test_focus_is_an_investigation.py",             #    1.1s
    "tests/test_golden.py",                                     #    1.1s
    "tests/unit/test_why_is_this_ranked_first.py",              #    1.0s
    "tests/unit/test_the_jump_box_offers_what_it_knows.py",     #    1.0s
    "tests/unit/test_the_capacity_answer_is_published.py",      #    1.3s
    "tests/unit/test_comparison_refuses_on_contract_movement.py",       #    2.1s
    "tests/unit/test_report_stays_readable_at_scale.py",             #   12.8s
    "tests/unit/test_marginal_efficiency_gate.py",                   #   11.3s
    "tests/unit/test_build_root_override_join.py",                   #    9.9s
    "tests/unit/test_dual_plane_capture.py",                         #    9.8s
    "tests/unit/test_six_seams_round_21_found.py",                   #    7.7s
    "tests/unit/test_stream_merge.py",                               #    7.6s
    "tests/unit/test_the_viewer_renders_the_schema.py",              #    6.6s
    "tests/unit/test_the_perfetto_handoff.py",                       #    6.4s
    "tests/unit/test_docs_links_and_commands.py",                    #    6.2s
    "tests/unit/test_output_schemas.py",                             #    5.7s
    "tests/unit/test_the_handoff_says_whether_perfetto_fetched.py",  #    5.4s
    "tests/unit/test_grace_window_drains.py",                        #    5.3s
    "tests/unit/test_bst_extract_run.py",                            #    5.0s
    "tests/unit/test_blast_ranking_discriminates.py",                #    4.8s
    "tests/unit/test_cli_subcommands.py",                            #    4.6s
    "tests/unit/test_bst_extract_run_strict.py",                     #    4.5s
    "tests/unit/test_why_bga_believes_what_it_believes.py",          #    4.3s
    "tests/unit/test_publish_the_join.py",                           #    4.1s
    "tests/unit/test_a_report_you_can_navigate.py",                  #    3.8s
    "tests/unit/test_native_build_tracer.py",                        #    3.6s
    "tests/unit/test_diagnostics_performance.py",                    #    3.2s
    "tests/unit/test_the_minutes_inside_analyze.py",                 #    2.8s
    "tests/unit/test_bst_run_context.py",                            #    2.7s
    "tests/unit/test_compare_mismatch_refusal.py",                   #    2.6s
    "tests/unit/test_the_views_that_draw.py",                        #    2.5s
    "tests/unit/test_compare.py",                                    #    2.2s
    "tests/unit/test_shared_source_blast.py",                        #    2.2s
    "tests/unit/test_the_report_you_can_attach.py",                  #    2.2s
    "tests/unit/test_the_order_the_page_has.py",                     #    2.1s
    "tests/unit/test_the_numbers_have_a_sentence.py",                #    2.1s
    "tests/unit/test_copy_a_finding.py",                             #    1.8s
    "tests/test_cli.py",                                             #    1.8s
    "tests/unit/test_granularity.py",                                #    1.8s
    "tests/unit/test_efficiency_gate_exit_codes.py",                 #    1.7s
    "tests/unit/test_determinism.py",                                #    1.7s
    "tests/unit/test_bst_show_to_graph.py",                          #    1.7s
    "tests/unit/test_what_if_you_could_choose_the_fixes.py",         #    1.7s
    "tests/unit/test_efficiency_gate_signal.py",                     #    1.7s
    "tests/unit/test_a_clone_without_the_archive.py",                #    1.6s
    "tests/unit/test_bst_checkout_cost.py",                          #    1.6s
    "tests/unit/test_host_manifest_and_cross_host.py",               #    1.6s
    "tests/unit/test_one_timeline_both_planes.py",                   #    1.5s
    "tests/unit/test_a_link_that_shows_what_i_was_looking_at.py",    #    1.5s
    "tests/unit/test_progress_never_touches_the_pipe.py",            #    1.4s
    "tests/unit/test_cli_exit_codes.py",                             #    1.4s
    "tests/unit/test_one_click_from_investigation.py",               #    1.4s
    "tests/unit/test_a_capture_that_slept.py",                       #    1.3s
    "tests/unit/test_tables_you_can_interrogate.py",                 #    1.3s
    "tests/unit/test_the_page_that_answers_why.py",                  #    1.3s
    "tests/unit/test_graph_performance.py",                          #    1.2s
    "tests/unit/test_the_first_screen_is_a_decision.py",             #    1.2s
    "tests/unit/test_every_element_is_one_object.py",                #    1.2s
    "tests/unit/test_the_next_step_is_a_command.py",                 #    1.1s
    "tests/unit/test_blast_query_and_kinds.py",                      #    1.1s
    # UX-336, re-measured 2026-08-27 on the small tier alone. Thirteen
    # more files had crossed the medium floor since round 39 and were
    # invisible for the same reason: each is small, the budget is an
    # aggregate. Together they were 46.2s of the small tier's 81.7s.
    "tests/unit/test_emphasis_is_a_budget.py",                       #   12.4s
    "tests/unit/test_the_documented_invocations_parse.py",           #    5.6s
    "tests/unit/test_the_fold_says_how_deep_it_goes.py",             #    4.4s
    "tests/unit/test_the_shape_before_the_rows.py",                  #    3.6s
    "tests/unit/test_a_drawing_is_graded.py",                        #    3.1s
    "tests/unit/test_the_mapping_is_law.py",                         #    2.2s
    "tests/unit/test_the_page_conforms_to_its_sections.py",          #    2.1s
    "tests/unit/test_a_guard_reads_only_what_a_clone_has.py",        #    6.2s
    # `UX-466`: draws a real timeline per committed capture with
    # `bga timeline` in a subprocess, seven of them.
    "tests/unit/test_the_trace_census_reads_both_ends.py",           #    4.9s
    # `UX-465`: two real `bst build` runs where bst is installed,
    # and the spec/YAML half everywhere.
    "tests/unit/test_a_generated_project_builds.py",                 #    6.5s
    "tests/unit/test_the_printed_sentences_are_contracts.py",        #    1.6s
    "tests/unit/test_a_capture_that_cannot_start.py",                #    1.5s
    "tests/unit/test_the_handoff_does_not_carry_the_trace.py",       #    1.3s
    "tests/unit/test_buttons_that_know_why.py",                      #    1.0s
    # `UX-399`, tiered on landing. Two browser boots over
    # `macro_micro` - one for the rail's scrollspy, one for the
    # layout-cost pair with the optimisation forced off and on in
    # the same page - plus five source clauses that need neither.
    "tests/unit/test_the_browser_is_the_library.py",                 #    4.8s
    # `UX-392`: exports the 1,202-element synthetic run and boots a
    # browser twice. Measured 7.7s total.
    "tests/unit/test_a_filter_is_a_property_of_a_table.py",           #    7.7s
    # `UX-393`: three browser boots on `macro_micro` - the walk, the
    # scroll and the keyboard. 8.6s.
    "tests/unit/test_the_rail_takes_a_step.py",                      #    8.6s
    # `UX-397`: two browser boots - the export scrolled to its end and
    # a served two-plane snapshot where the button is drawn. 4.6s.
    "tests/unit/test_the_handoff_rides_the_rail.py",                 #    4.6s
    # `UX-400`: one `analyze` subprocess and one node sweep that renders
    # ten populations at three sizes each - the subprocess is all of it.
    "tests/unit/test_every_population_at_zero_one_and_many.py",      #    1.3s
    # `UX-401`: one export, one page boot and one `analyze` subprocess -
    # the census reads the keys off the payload and the destinations off
    # the booted document.
    "tests/unit/test_no_key_is_terminal_only_in_silence.py",         #    4.9s
    # `UX-403`'s census found these four booting a real browser from the
    # *small* tier - the escape `test_the_tiers_are_a_partition.py` is
    # for and could not see, because its clauses read the lists against
    # each other and nothing read the lists against the suite.
    "tests/unit/test_a_shapeable_population_is_drawn.py",             #    2.2s
    "tests/unit/test_a_task_uid_is_not_a_label.py",                   #    1.7s
    "tests/unit/test_one_bucket_one_row.py",                          #    1.9s
    "tests/unit/test_the_synthesis_reaches_the_page.py",              #    2.6s
    # `UX-432`, tiered after CI caught it rather than on landing - the
    # note twelve lines up says a file like this belongs here by
    # construction and this round forgot anyway. Seven clauses, each
    # spawning `dev_perfetto_queries.py`, which itself spawns `node` to
    # read the question library: the subprocesses are all of it, and no
    # browser is involved. 4.6s here, 6.1s on CI.
    "tests/unit/test_the_questions_are_asked_of_a_real_trace.py",     #    4.6s
)
