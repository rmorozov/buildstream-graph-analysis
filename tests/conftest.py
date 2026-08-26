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
    "trace_processor_shell is not installed": (
        "Perfetto's shell is an optional local tool, not a dependency", 13),
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
    "no real capture in this tree": (
        "UX-213's second arm, where examples/06's capture is absent", 8),
    "the examples/06 capture is not here": (
        "UX-213's second arm, where examples/06's capture is absent", 10),
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
    "bst/bwrap/cc not all found on PATH - "
    "see docs/spec/ingestion-pipeline.md": (
        "the full-capture arm; `installed-capture` is where it runs", 6),
    "bwrap not on PATH": (
        "the sandbox arm; the bst-* CI jobs provide bwrap and run it", 5),
    "bwrap/cc not both on PATH": (
        "the sandbox arm; the bst-* CI jobs provide bwrap and run it", 8),
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
