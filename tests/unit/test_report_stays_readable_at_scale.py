"""UX-187: a report you can read at four thousand elements.

Field feedback: *"let's check that our reports in different formats are
readable enough on long output."*

Measured before the fix, on a synthetic run whose critical path is 402
elements long: the path section rendered **405 of the report's 498
lines** - 81% of everything - and the four sections a reader actually
acts on (Key Findings, the floors, the occupancy verdict, the
diagnostics) all sat below it. `UX-33` made the path always-print when
paths were ten elements; at four hundred the rule that helped now
buries the finding.

The rule the caps follow: **nothing is truncated silently**. Every
elision names its own count and the flag that undoes it, because a
reader cannot act on a number they do not know is missing - which is
`UX-160`'s standing lesson, and the specific defect fixed here in the
serialized-pairs line, which had sliced to five and said nothing.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

# A total the whole text report must fit inside on the deep fixture.
# Chosen from the measurement, not guessed: capped rendering of the
# 402-element chain is 117 lines, and the headroom is for the sections
# that grow with findings rather than with elements.
_REPORT_LINE_BUDGET = 200


def _bga(args):
    return subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=os.getcwd())


@pytest.fixture(scope="module")
def deep_run(tmp_path_factory):
    """A 400-layer chain: the shape that makes a critical path long.

    The default synthetic project is wide rather than deep - its path is
    14 elements - so it does not exercise the section this item is
    about. **Narrow** on purpose: the path length comes from the layer
    count, and width 2 gives the same 402-element chain as width 10 for
    a fifth of the analysis (1.7s against 30s, measured), which matters
    because this fixture is analyzed eight times below.
    """
    out = tmp_path_factory.mktemp("deep") / "run"
    result = _bga(["gen-synthetic", str(out), "--layers", "400",
                   "--width", "2", "--seed", "1"])
    assert result.returncode == 0, result.stderr
    return str(out)


class TestTheCriticalPathIsFolded:
    def test_the_report_fits_a_stated_budget(self, deep_run):
        rendered = _bga(["analyze", deep_run, "--diagnostics"]).stdout.splitlines()
        assert len(rendered) <= _REPORT_LINE_BUDGET, (
            f"{len(rendered)} lines - the report grew past the budget this "
            f"item set. If that is deliberate, move the number and say why.")

    def test_the_path_section_is_no_longer_most_of_the_report(self, deep_run):
        rendered = _bga(["analyze", deep_run, "--diagnostics"]).stdout
        section = rendered.split("Path (chain order", 1)[1].split("\n\n", 1)[0]
        rows = [line for line in section.splitlines()
                if re.match(r"^    \S+\.bst\s", line)]
        assert len(rows) <= 24, f"{len(rows)} path rows still render by default"
        assert len(rows) >= 10, (
            f"only {len(rows)} rows - the fold took the finding with it")

    def test_both_ends_of_the_chain_survive(self, deep_run):
        """A chain's two ends are where an optimizer starts: the root
        everything waits on, and the last link before the build ends.
        Folding the middle keeps both; folding the tail keeps neither."""
        rendered = _bga(["analyze", deep_run, "--diagnostics"]).stdout
        assert "toolchain.bst" in rendered, "the root of the chain is gone"
        assert re.search(r"layer39\d/", rendered), "the end of the chain is gone"

    def test_the_elision_names_its_count_and_its_flag(self, deep_run):
        rendered = _bga(["analyze", deep_run, "--diagnostics"]).stdout
        match = re.search(r"\.\.\. (\d+) more element\(s\) \(--full-path to print all\)",
                          rendered)
        assert match, "the fold is silent"
        assert int(match.group(1)) > 300, (
            "the count must be the real number of hidden elements")

    def test_the_flag_restores_the_section(self, deep_run):
        capped = _bga(["analyze", deep_run, "--diagnostics"]).stdout.splitlines()
        full = _bga(["analyze", deep_run, "--diagnostics",
                     "--full-path"]).stdout.splitlines()
        assert len(full) > len(capped) * 3
        assert "--full-path to print all" not in "\n".join(full), (
            "the elision line must not survive its own flag")

    def test_a_short_path_is_untouched(self):
        """The golden fixture's three-element path renders exactly as it
        did - the caps must not change the common case."""
        rendered = _bga(["analyze", GOLDEN]).stdout
        assert "base.bst → lib.bst → app.bst" in rendered
        assert "to print all" not in rendered


class TestTheSharedSourcesTableIsCapped:
    def test_a_wide_table_folds_and_says_so(self, tmp_path):
        from bga import sources

        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        # Twenty repositories, each fed to both elements, so every one
        # earns a row.
        elements = {}
        for uid in ("base.bst", "lib.bst"):
            elements[uid] = [
                {"kind": "git", "identity": f"host/org/repo-{n:02d}",
                 "declared": f"https://host/org/repo-{n:02d}.git",
                 "keying": "ref", "staged_at": None}
                for n in range(20)
            ]
        (run / "sources.json").write_text(json.dumps(sources.build_inventory(elements)))

        capped = _bga(["analyze", str(run)]).stdout
        assert "--full-sources to print all" in capped
        assert capped.count("host/org/repo-") <= 12, "every row still renders"

        full = _bga(["analyze", str(run), "--full-sources"]).stdout
        assert full.count("host/org/repo-") >= 20
        assert "to print all" not in full


class TestJsonNeverTruncates:
    """The caps are a text-rendering concern. A consumer that asked for
    JSON asked for all of it."""

    def test_the_whole_path_is_in_the_json(self, deep_run):
        payload = json.loads(
            _bga(["analyze", deep_run, "--format", "json"]).stdout)
        # `UX-288`: the path lives in `critical_path_detail` now,
        # which is the one place it is published.
        path = payload["critical_path_detail"]
        assert len(path) > 300, f"the JSON path is {len(path)} elements"

    def test_the_flag_does_not_change_the_json(self, deep_run):
        """A `--full-*` flag is about the page, so it must be inert
        here - otherwise the caps have leaked into the contract."""
        without = _bga(["analyze", deep_run, "--format", "json"]).stdout
        with_flag = _bga(["analyze", deep_run, "--format", "json",
                          "--full-path", "--full-sources"]).stdout
        assert without == with_flag


class _StubResult:
    """The smallest result that reaches the batch-opportunities block.

    `result.structural` is the attribute the renderer reads - written
    down here because getting it wrong produces a report with no
    Serialized line at all, which a naive assertion reads as a pass.
    """

    def __init__(self, serialized_pairs):
        self.run_id = "stub"
        self.total_duration_us = 1000
        self.signals = {}
        self.floors = {}
        self.attribution = {}
        self.occupancy = {}
        self.confidence = {}
        self.violations = []
        self.utilisation = {}
        self.structural = {
            # `parallelism` is what opens the Structural Analysis block
            # the batch opportunities render inside; without it the
            # section is skipped entirely.
            "parallelism": {"max_parallelism": 1},
            "batch_opportunities": {"serialized_pairs": serialized_pairs},
        }


class TestNothingIsCutSilently:
    def _serialized_line(self, pairs):
        from bga.report.text import format_text

        rendered = format_text(_StubResult(serialized_pairs=pairs))
        matched = [line for line in rendered.splitlines() if "Serialized" in line]
        assert matched, (
            "the Serialized line did not render at all - the stub no longer "
            "reaches the block, so this test would pass while asserting nothing")
        return matched[0]

    def test_the_line_names_what_it_dropped(self):
        line = self._serialized_line([(f"a{n}.bst", f"b{n}.bst") for n in range(9)])
        assert "+4 more" in line, (
            "the line sliced to five and said nothing about the rest")

    def test_it_stays_quiet_when_nothing_was_dropped(self):
        line = self._serialized_line([("a.bst", "b.bst")])
        assert "more" not in line


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
