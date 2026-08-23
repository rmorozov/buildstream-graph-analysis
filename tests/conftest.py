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
* **no single reason may account for more than a handful.** One file
  going quiet is the signature being guarded - twenty-six tests skipping
  for one reason is a guard file that stopped guarding, whatever the
  reason says.

Making `jsonschema` a hard dependency was the other option and is
declined: it is a dev tool and stays one. The claim gets honest instead.
"""
import collections

# Every skip reason this suite is known to produce, with what each one
# means. A reason not in here fails the session - deliberately, because
# the point is that nobody adds a silent skip without saying so.
KNOWN_SKIP_REASONS = {
    "not a dev environment by its own account (BGA_EXPECT_DEV is unset)":
        "the dev-extras canary, which only asserts where the environment "
        "claims to be a dev environment (CI sets BGA_EXPECT_DEV)",
    "trace_processor_shell is not installed":
        "Perfetto's shell is an optional local tool, not a dependency",
    "node is not installed":
        "the viewer guards need node; CI has it",
    "jsonschema is not installed - `pip install -e '.[dev]'`":
        "schema validation is a dev extra",
    "buildstream is not installed":
        "the bst-dependent guards run in the bst-* CI jobs",
    # UX-213's real-capture arm. These three were undeclared until the
    # census asked: they are legitimate - a guard that also runs against
    # a real capture skips that arm where the capture is absent, and its
    # committed-fixture arm still runs - but nothing had ever named
    # them, which is precisely what the census is for.
    "no real capture here":
        "UX-213's second arm, where examples/06's capture is absent",
    "no real capture in this tree":
        "UX-213's second arm, where examples/06's capture is absent",
    "the examples/06 capture is not here":
        "UX-213's second arm, where examples/06's capture is absent",
}

# One file going quiet is what this exists to catch. The suite's own
# baseline is one skip per reason; a reason that suddenly accounts for
# dozens is a module-level marker that silenced a whole file.
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
                f"tests/conftest.py with what it means, or stop skipping.")
        elif count > cap:
            complaints.append(
                f"{count} tests skipped for one reason ({reason!r}) - more "
                f"than {cap}. That is a whole guard file going quiet, which "
                f"is exactly what a green run must not be able to hide.")
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
