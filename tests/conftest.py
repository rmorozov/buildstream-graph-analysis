"""UX-235: a skip that stays quiet is a guard that stopped guarding.

Several verification logs claim a suite that "runs on a fresh clone".
Measured, that is one extras-flag wider than it sounds: with
`jsonschema` absent - exactly what a plain `pip install -e .` gives you
- `tests/unit/test_output_schemas.py` collapses to **26 skipped** and
the run stays green.

Round 21's seam 6 banned a module-*scope* `pytest.importorskip`, which
turned whole files into "1 skipped". The shape that remains is a
module-level `skipif` marker applied to every class: the tests are
collected, so seam 6 is satisfied, and every one of them skips, so the
file still says nothing. `BGA_EXPECT_DEV` (set in CI) turns that into a
red for the jsonschema case specifically - but it is opt-in, so a local
fresh clone is silent, and it knows about jsonschema only.

This is the general form, and it needs no opt-in. Every skip is tallied
by reason; at the end of the session two things are checked:

* **no reason may be new.** A skip this repository has not thought about
  is a skip nobody has decided is acceptable.
* **no reason may account for more than it was measured at, plus one
  file's worth.** One file going quiet is the signature being guarded -
  twenty-six tests skipping for one reason is a guard file that stopped
  guarding, whatever the reason says. The measured baseline is per
  reason because it is per *environment*: a runner without `bst` skips
  a dozen tests for one reason legitimately, and a single global cap
  cannot tell that from a silenced file.

Making `jsonschema` a hard dependency was the other option and is
declined: it is a dev tool and stays one. The claim gets honest instead.
"""
import collections
import os
import pathlib

import pytest

from tiers import LARGE, MEDIUM

# UX-264: where the one DOM shim lives, as an absolute file URL.
#
# The viewer harnesses run `node -e` in a subprocess, and several of
# them do it from a `tmp_path` rather than the repository root - so a
# relative `import "./tests/dom_shim.mjs"` resolves against whatever
# directory that test happened to choose. Published here, inherited by
# every subprocess, and independent of cwd.
os.environ["BGA_DOM_SHIM"] = (
    pathlib.Path(__file__).resolve().parent / "dom_shim.mjs").as_uri()

# UX-238: which tier each collected test is in.
#
# Applied here rather than as a marker in 220 files: the tier is a
# property of what a file *does*, the lists in `tiers.py` are the
# exceptions, and a new file inherits `small` without anyone editing
# anything. `bst` is left alone - it is the enormous tier under its own
# name and the files that need it already carry it.
_LARGE = frozenset(LARGE)
_MEDIUM = frozenset(MEDIUM)


def pytest_collection_modifyitems(config, items):
    root = pathlib.Path(config.rootpath)
    for item in items:
        try:
            relative = pathlib.Path(item.fspath).relative_to(root).as_posix()
        except ValueError:                              # pragma: no cover
            continue
        if relative in _LARGE:
            item.add_marker(pytest.mark.large)
        elif relative in _MEDIUM:
            item.add_marker(pytest.mark.medium)
        else:
            item.add_marker(pytest.mark.small)

# Every skip reason this suite is known to produce: what each one means,
# and **the largest count it has been measured at**. A reason not in
# here fails the session - deliberately, because the point is that
# nobody adds a silent skip without saying so.
#
# The measured count is the repair `UX-233`'s CI run forced. The first
# version of this table was written from one machine's skip set - a dev
# container with `bst`, `bwrap` and a real capture in it - and CI's
# `test` job has none of those. It skipped **82 tests across nine
# reasons**, seven of them undeclared, and the census failed a run in
# which nothing was wrong. A census calibrated on one environment is
# exactly the hollow instrument this item was filed about, one level up.
#
# So the bound is per reason and comes from a measurement rather than
# from a single global guess: a reason may account for what it was
# measured at, plus `MAX_PER_REASON` of headroom. Ordinary growth in a
# family passes; a whole file adopting the reason does not. `0` means
# "never seen more than a handful", which is the original behaviour.
KNOWN_SKIP_REASONS = {
    "not a dev environment by its own account (BGA_EXPECT_DEV is unset)": (
        "the dev-extras canary, which only asserts where the environment "
        "claims to be a dev environment (CI sets BGA_EXPECT_DEV)", 0),
    # Round 43 gave this reason a second file and twelve more skips.
    # `UX-312`'s first clause loads the emitted trace with Perfetto's
    # own reader instead of this repository's decoder, which is the
    # only way to check that `bga` and Perfetto agree about the wire
    # format - and the binary is deliberately neither vendored (11 MB,
    # in a repository that declines a protobuf dependency) nor fetched
    # by the suite (a guard that reaches the network fails for reasons
    # unrelated to the code). Measured on this container: 12 from
    # `test_the_real_reader_agrees.py`, 1 from the handoff guard.
    # Re-measured 2026-08-29: 14. 13 -> 14.
    # Round 70 added `UX-434`'s two real-reader clauses, which first
    # coined a second wording for this same absence and so skipped
    # undeclared - failing the census on all four interpreters in CI
    # while every test passed. They ask `tests/trace_processor.py` now.
    # Re-measured 2026-08-31 (the three files that use the gate,
    # `-rs`): 16. 14 -> 16.
    "trace_processor_shell is not installed": (
        "Perfetto's shell is an optional local tool, not a dependency", 16),
    # UX-313 reads the committed dual-plane capture of `examples/06` to
    # show that every element leaves a record whose exit was never
    # observed - the fact that makes the reorder window the whole record
    # list. `UX-189` keeps that capture out of a clone, and CI runs
    # without it, so the three clauses that need it declare their
    # absence here rather than passing vacuously.
    # Round 50 (`UX-330`) added two, and the census is what found the
    # mistake behind them: the gzipped-raw-log clauses first called
    # that capture "committed" and invented their own skip reason, so
    # they skipped silently in CI and passed vacuously here, where the
    # capture happens to exist. 3 -> 5.
    "the example capture is not in this clone (UX-189)": (
        "the capture archive is deliberately not shipped; the clauses "
        "that read it say so rather than passing on an empty tree", 5),
    "node is not installed": (
        "the viewer guards need node; CI has it", 0),
    # UX-257's geometry guards. Declared so that "no browser here" is
    # a fact the census reports rather than a silence.
    "no chrome/chromium for the geometry guards (set BGA_CHROME)": (
        "UX-257 drives a real Chrome over CDP; where there is none, the "
        "geometric claims are unguarded and this says so", 12),
    # UX-247's freshness guard reads `git log` for one document. A
    # shallow checkout has no commit that touched it, and "we could not
    # check" must not read as "checked and found nothing".
    "the clone has no history for this file (a shallow checkout)": (
        "UX-247 compares a document's own Verification Log date against "
        "when git last changed it; a depth-1 clone cannot answer that", 0),
    # `UX-314` asks for port 8080 by name, because it is one of exactly
    # two plain-http origins ui.perfetto.dev's CSP will fetch from. A
    # developer machine often has something there already, and the
    # guard binds the port to find out rather than trusting an
    # exception `bga view` handles for itself.
    "port 8080 is in use on this machine": (
        "UX-314's friendly-port arm, where the port is already taken", 0),
    "jsonschema is not installed - `pip install -e '.[dev]'`": (
        "schema validation is a dev extra", 0),
    "buildstream is not installed": (
        "the bst-dependent guards run in the bst-* CI jobs", 0),
    # UX-213's real-capture arm. These three were undeclared until the
    # census asked: they are legitimate - a guard that also runs against
    # a real capture skips that arm where the capture is absent, and its
    # committed-fixture arm still runs - but nothing had ever named
    # them, which is precisely what the census is for.
    "no real capture here": (
        "UX-213's second arm, where examples/06's capture is absent", 19),
    # Round 43's four trace guards adopted this string. Their
    # *properties* are checked on committed fixtures that a clone has;
    # what skips here is the arithmetic only `examples/06`'s gitignored
    # capture can produce. Measured with that directory moved aside:
    # 3 from the annotations guard, 3 from the counter guard, 1 each
    # from the flows and identity guards - plus `UX-213`'s own arm.
    #
    # **8 -> 15**, re-measured 2026-08-29. Seven files carry the string
    # as a `skipif` now rather than round 43's four - the pairing-pass,
    # arrows, why-page, counter, capture-layout, slice and
    # trace-identity guards - and the declaration stayed at what round
    # 43 measured. It was inside its bound the whole time on
    # `MAX_PER_REASON` of headroom rather than on its own count, which
    # is the census going quiet by degrees instead of at once. Round 61
    # found it the hard way: `UX-381`'s guard took the reason to 17
    # against a bound of 16 and reddened CI, and the number that was
    # actually stale was this one.
    #
    # Measured by running the suite in a worktree that has no `.bga`
    # (`git worktree add --detach`) rather than by moving the real
    # capture aside - a timeout during that move once left the
    # directory renamed. **The count is the hook's own tally, not a
    # `-rs` replay**: `pytest_runtest_logreport` counts `setup`-phase
    # skips only, so a `pytest.skip()` in a test body is invisible to
    # the census while `-rs` lists it, and two of these seven files
    # have one. Reading a census off `-rs` gives a different number in
    # both directions.
    "no real capture in this tree": (
        "UX-213's second arm, where examples/06's capture is absent", 15),
    "the examples/06 capture is not here": (
        "UX-213's second arm, where examples/06's capture is absent", 10),
    # `UX-572`: the same absence, with the path in it. "in this tree"
    # named no tree, and the tree it meant was a linked worktree, which
    # never has an ignored capture. Measured at 3 in a tree without it
    # (`-rs`, the file's three real-capture clauses).
    "no real capture at examples/06-macro-micro-optimization/"
    ".bga/runs/20260821T170127Z, in this tree or the checkout "
    "it was linked from": (
        "UX-213's second arm, saying which path was missing", 3),
    # The seven CI's `test` job produces and a dev container does not.
    # Every one of them is "the tool is not installed on this runner",
    # and every one of them has a job that *does* install it: the
    # `bst-smoke`, `bst-tests`, `bst-examples` and `installed-capture`
    # jobs exist so these arms run somewhere. Counts measured on the
    # `test (3.11)` job of PR #137.
    "bst not found on PATH": (
        "the bst-dependent arm; the bst-* CI jobs install it and run it", 2),
    "bst not found on PATH - see docs/spec/ingestion-pipeline.md": (
        "the bst-dependent arm; the bst-* CI jobs install it and run it", 12),
    "bst and/or buildstream-plugins not available - "
    "see docs/spec/ingestion-pipeline.md": (
        "the bst-dependent arm; the bst-* CI jobs install it and run it", 1),
    "bst/bwrap/bga not all found on PATH - "
    "see docs/spec/ingestion-pipeline.md": (
        "the full-capture arm; `installed-capture` is where it runs", 2),
    "bst/bwrap/busybox not all found on PATH - "
    "see docs/spec/ingestion-pipeline.md": (
        "`UX-465`'s generated-project arm; busybox is the static shell the "
        "generated project stages, as examples/stage_runtimes.sh does", 2),
    "bst/bwrap/cc not all found on PATH - "
    "see docs/spec/ingestion-pipeline.md": (
        "the full-capture arm; `installed-capture` is where it runs", 6),
    "bwrap not on PATH": (
        "the sandbox arm; the bst-* CI jobs provide bwrap and run it", 5),
    "bwrap/cc not both on PATH": (
        "the sandbox arm; the bst-* CI jobs provide bwrap and run it", 8),
    # `UX-405`'s shim guard reaches `install_bwrap_shim`, which writes a
    # shim that *falls back* to the real `bwrap` and refuses when there
    # is none, before it reaches anything it is about. It declared a C
    # compiler and not a sandbox, so it passed on a dev container and
    # failed on every `test (3.x)` runner - `UX-213`'s class, found by
    # CI rather than by this census, because the census only sees a
    # skip that happens. Measured on `test (3.11)` of PR #181: 1.
    "no bwrap for the capture's shim to fall back to": (
        "the sandbox arm; the bst-* CI jobs provide bwrap and run it", 1),
    # `UX-402`'s journey walks the documented commands over a copy of
    # `examples/06`, so it needs all three: a `bst` to build with, a
    # `bwrap` to build in, and the staged toolchain
    # `generate_sources.py` writes and `UX-189` keeps out of a clone.
    # The `test` job has none of them and the whole file skips, so this
    # number is the file's clause count and moves when the file grows.
    # PR #181's `test (3.11)`: 14. Round 80: **23** - `UX-536` and
    # `UX-538` each added a clause and the 8 of headroom absorbed the
    # first fourteen, so the number that finally reddened CI was one
    # over the cap rather than one over the count.
    #
    # Invisible to any developer machine that has `bst` (this one does:
    # the file runs, 23 passed in 103s, and skips nothing), which is
    # fixing guide 7's class - a claim only CI can falsify.
    # `UX-524` put one CI job's `make test` under `--cov-context=test`,
    # and the workflow states its price: +20% wall clock. The 1500-
    # element bound then reads the tracer - 10.30s against 10.0 on CI
    # 3.12, ~8.6s uninstrumented. One clause, and only where a tracer
    # is attached, so it fires on no developer machine and on exactly
    # one of CI's five jobs.
    "the duration is a tracer's and not this pipeline's; UX-524's "
    "coverage job runs +20% and a bare bound would read the instrument": (
        "the 1500-element timing bound; it runs wherever no tracer is "
        "attached, which is every job but the coverage one", 1),

    "the journey needs bst, bwrap and example 06's staged toolchain "
    "(files/toolchain, written by generate_sources.py)": (
        "UX-402's whole-journey arm; it runs where bst, bwrap and the "
        "staged toolchain are all present", 24),

    # `UX-449`. Everything below was **found by the static scan in
    # `tests/skip_reasons.py`**, not by a run: eighteen reasons written
    # into the suite that this dictionary had never heard of, on a tree
    # where every session was green.
    #
    # They were invisible for two independent reasons, and the counts
    # here say which. Sixteen of the eighteen are raised by
    # `pytest.skip()` in a **test body**, and the hook above counts
    # `report.when == "setup"` - so the runtime census cannot see them
    # at all, on any machine, ever. Measured directly, on a two-test
    # probe where both tests skipped:
    #
    #     CENSUS SAW: {'a setup-phase reason': 1}
    #
    # The other two ride a `skipif` marker over a tool this machine
    # happens to have, which is the blind spot `UX-449` was filed for.
    #
    # All of them are 0 because none fired in `make test` here or in
    # round 70's CI (144 skips, every one declared). A count that turns
    # out to be wrong is the census doing its job, and is a measurement
    # to correct rather than a reason not to declare.
    "bst or a staged runtime is missing": (
        "the capture chain needs both, and reports which is absent", 0),
    "examples/01 is not staged - run examples/stage_runtimes.sh": (
        "example 01's runtime is generated, not committed (`UX-189`)", 0),
    "examples/05-cmake-cpp-toolchain's toolchain isn't staged - run "
    "stage_cpp_toolchain.sh first": (
        "example 05's toolchain is generated, not committed", 0),
    "examples/06 is not staged - run examples/stage_cpp_toolchain.sh": (
        "example 06's toolchain is generated, not committed", 0),
    "golden has no Plane 2 sibling to lose": (
        "a fixture-shape gate: the clause needs a run with both planes", 0),
    "jq not found on PATH": (
        "the docs' own examples pipe through jq; it is not a dependency", 0),
    "no C compiler on PATH": (
        "the LD_PRELOAD hook and the spine's fixtures are compiled here", 0),
    "no PATH": (
        "the doctor's remedy text is about resolving a command, so an "
        "environment with no PATH at all has nothing to assert", 0),
    "no block declares a join destination": (
        "a payload-shape gate over the committed fixtures", 0),
    "no bulk tree in this checkout - examples/README.md says how to make one": (
        "`UX-462`'s clause needs the generated tree the guide tells a "
        "reader to make; the root `.gitignore` keeps it out of a clone", 0),
    "no busybox on PATH to exercise a static binary with": (
        "the static-binary blind spot needs a real static binary", 0),
    "no snapshot store in this checkout": (
        "a store is written by a capture and `UX-189` keeps it out of "
        "a clone", 0),
    # `UX-514`'s two arms. Exactly one fires: the pair reads
    # `capture-ref-policy:` out of the workflow and each clause skips
    # when the *other* policy is declared. Both are `pytest.skip()` in
    # a test body, which the census hook cannot see (it counts
    # `setup`-phase skips), so both are measured at 0 - `-rs` shows one.
    "the workflow declares `advanced`": (
        "the pinned-policy arm, skipped where the workflow says "
        "`advanced`", 0),
    "the workflow declares `pinned`": (
        "the advanced-policy arm, skipped where the workflow says "
        "`pinned`", 0),
    "this fixture's evidence carries no structured value": (
        "a payload-shape gate over the committed fixtures", 0),
    "this fixture's findings name no elements": (
        "a payload-shape gate over the committed fixtures", 0),
    "this host exposes no /proc/meminfo": (
        "the host sampler reads Linux's own files", 0),
    "this run published no joint-saving signal": (
        "a payload-shape gate over the committed fixtures", 0),
    "this run rendered no anchored section": (
        "a geometry gate: the page has to have drawn one first", 0),
    "this run rendered no rail": (
        "a geometry gate: the page has to have drawn one first", 0),
    "tomllib is 3.11+; CI's packaging job covers this everywhere": (
        "the one reason here that names its own coverage elsewhere", 0),
    # `UX-588`: never taken while the floor is 3.9. It exists so the
    # PEP 604 clause retires itself the day the floor moves, rather
    # than passing on a check that no longer applies.
    "the floor has moved to 3.10; PEP 604 is allowed": (
        "the floor guard's own retirement, unreachable at >=3.9", 0),
}

# One file going quiet is what this exists to catch, and it is also the
# headroom each measured reason gets. The suite's own baseline is a
# handful per reason; a reason that suddenly accounts for a file more
# than it was measured at is a module-level marker that silenced one.
MAX_PER_REASON = 8

_SKIPS = collections.Counter()


def pytest_runtest_logreport(report):
    if report.when != "setup" or not report.skipped:
        return
    reason = ""
    if isinstance(report.longrepr, tuple) and len(report.longrepr) == 3:
        reason = report.longrepr[2]
    _SKIPS[reason.replace("Skipped: ", "").strip()] += 1


def skip_census():
    """What this run skipped, by reason."""
    return dict(_SKIPS)


def census_complaints(census, known=None, cap=MAX_PER_REASON):
    """What is wrong with a skip census, as a list of sentences.

    Split out from the hook so it can be tested directly - a session
    hook that is only exercised by the session it guards is the same
    kind of untested instrument this item is repairing.
    """
    known = KNOWN_SKIP_REASONS if known is None else known
    complaints = []
    for reason, count in sorted(census.items()):
        if reason not in known:
            complaints.append(
                f"{count} test(s) skipped for a reason this suite has never "
                f"declared: {reason!r}. Add it to KNOWN_SKIP_REASONS in "
                f"tests/conftest.py with what it means and what it was "
                f"measured at, or stop skipping.")
            continue
        # A declared reason carries the count it was measured at; the
        # bound is that plus one file's worth of headroom, so growth in
        # a family passes and a file adopting the reason does not.
        declared = known[reason]
        measured = declared[1] if isinstance(declared, tuple) else 0
        allowed = measured + cap
        if count > allowed:
            complaints.append(
                f"{count} tests skipped for one reason ({reason!r}) - more "
                f"than the {allowed} this suite allows it "
                f"({measured} measured + {cap} headroom). That is a whole "
                f"guard file going quiet, which is exactly what a green run "
                f"must not be able to hide.")
    return complaints


def pytest_sessionfinish(session, exitstatus):
    """Fail the session on a bad census, whatever the test order was.

    In `pytest_sessionfinish` rather than in a test, because a test
    would have to run last to see the whole tally and nothing
    guarantees that.
    """
    # A filtered run (`-k`, a single file) has no business asserting a
    # whole-suite census; only a full run does.
    #
    # `config.args`, not `config.option.file_or_dir` - the latter does
    # not exist on pytest 9, so the first draft of this gate raised
    # inside the hook and the census never ran at all. It was written,
    # it looked right, and it measured nothing: the same hollow-guard
    # shape this whole item is repairing, found the only way such
    # things are found - by running it against a real absence and
    # checking the complaint actually appeared.
    if getattr(session.config.option, "keyword", None):
        return
    # UX-238: and neither does a *tier* run. `make test-small` filters
    # with `-m`, which `config.args` cannot see - so without this the
    # census would report on a third of the suite while claiming to
    # have looked at all of it, which is the shape UX-235 exists to
    # prevent rather than to reproduce.
    if getattr(session.config.option, "markexpr", ""):
        return
    args = [str(a) for a in getattr(session.config, "args", [])]
    if [a.rstrip("/") for a in args] != ["tests"]:
        return
    complaints = census_complaints(skip_census())
    if not complaints:
        return
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_sep("=", "skip census", red=True)
        for complaint in complaints:
            reporter.write_line(complaint)
    session.exitstatus = 1
