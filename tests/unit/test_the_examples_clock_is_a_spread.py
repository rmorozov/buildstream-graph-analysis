"""UX-941: `bst-examples`' wall clock is stated as a spread, never priced alone.

The job's clock is one run of each sha. `tools/dev_bst_examples_spread.py`
keeps the jobs API's readings and derives the spread; `ci.yml` carries it
beside the job, and a sentence in the documents that prices the job in
seconds carries its range. Its exact figures leave as `::notice::` lines
from a last step that runs under `always()`.
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_bst_examples_spread as spread_tool
import dev_tier_drift

CI = REPO / ".github" / "workflows" / "ci.yml"
JOB = "bst-examples"

#: Where a sentence pricing the job would be read.
DOCUMENTS = ("docs/**/*.md", "examples/README.md", "README.md", "CLAUDE.md")

#: `test_the_cost_row_is_derived_from_the_selector.DURATION`, plus minutes.
DURATION = re.compile(r"(?<![\w.-])~?\d+(?:\.\d+)?\s*(?:s|min|minutes?)(?![\w])")
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*(\[])")

#: A sentence naming an element prices that element inside one capture,
#: a paired reading, not the job's clock (`round-124.md`'s `giant.bst`).
ELEMENT = re.compile(r"[\w-]+\.bst\b")


def job_header():
    """The comment block between the job's key and its `runs-on`."""
    text = CI.read_text(encoding="utf-8")
    start = text.index(f"\n  {JOB}:\n")
    return text[start:text.index("runs-on:", start)]


def job_text():
    text = CI.read_text(encoding="utf-8")
    start = text.index(f"\n  {JOB}:\n")
    following = re.search(r"\n  [\w-]+:\n", text[start + 1:])
    return text[start:start + 1 + following.start()] if following else text[start:]


def steps():
    return yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"][JOB]["steps"]


def unpriced(text, token):
    """Sentences and table rows naming the job with a duration, no
    element, and not the range."""
    found = []
    for paragraph in re.split(r"\n\s*\n", text):
        rows = [line for line in paragraph.splitlines() if line.lstrip().startswith("|")]
        prose = " ".join(line for line in paragraph.splitlines() if line not in rows)
        for sentence in [*rows, *SENTENCE.split(" ".join(prose.split()))]:
            if (JOB in sentence and DURATION.search(sentence)
                    and not ELEMENT.search(sentence) and token not in sentence):
                found.append(sentence)
    return found


class TestTheParagraphCarriesTheMeasuredSpread:

    def test_the_readings_are_a_population_of_jobs_api_spans(self):
        data = spread_tool.load()
        assert len(data["runs"]) >= spread_tool.MIN_RUNS, len(data["runs"])
        assert len({r["run_id"] for r in data["runs"]}) == len(data["runs"])
        for row in data["runs"]:
            assert row["seconds"] == spread_tool._seconds(
                row["started_at"], row["completed_at"]), row
            assert row["started_at"][:10] >= data["since"], row
        datetime.date.fromisoformat(data["measured"])
        assert data["command"].startswith("python3 tools/dev_bst_examples_spread.py --fetch")

    def test_the_paragraph_is_what_the_tool_would_write(self):
        """A narrower figure typed over the derived one reds here."""
        got, measured = spread_tool.current()
        header = job_header()
        assert spread_tool.FIGURE_LINE.search(header), (
            f"no `# clock:` line beside `{JOB}`")
        line = spread_tool.figure(got, measured)
        assert f"clock: {line}\n" in header, (
            f"`{JOB}`'s clock line is not {line!r}. "
            "Run `python3 tools/dev_bst_examples_spread.py --write`.")
        text = CI.read_text(encoding="utf-8")
        assert spread_tool.write_figure(text, line) == text

    def test_the_paragraph_names_its_command_and_says_it_is_no_measurement(self):
        header = job_header()
        assert "not a measurement" in header
        assert "tools/dev_bst_examples_spread.py --fetch" in header

    def test_the_spread_exceeds_the_drift_factor_the_paragraph_names(self):
        got, _ = spread_tool.current()
        assert spread_tool.drift_factor() == dev_tier_drift.CI_DRIFT_FACTOR
        assert got["max"] > got["min"] * dev_tier_drift.CI_DRIFT_FACTOR, (
            f"{got['min']}-{got['max']}s is inside CI_DRIFT_FACTOR "
            f"{dev_tier_drift.CI_DRIFT_FACTOR}; the paragraph says it is not")


class TestNoSentencePricesTheJobWithoutItsSpread:

    def test_the_scanner_catches_a_bare_price_and_passes_a_banded_one(self):
        token = "620-964s"
        assert unpriced("Staging it costs `bst-examples` 120s.", token)
        assert not unpriced(f"It read 807s on `bst-examples`, inside {token}.", token)
        assert not unpriced("`bst-examples` caught it. Two runs read 40.1s.", token)
        assert not unpriced("`bst-examples` ran `giant.bst` 40.1s slower.", token)
        assert unpriced("| row | `bst-examples` took 900s |", token)

    def test_no_document_prices_the_job_without_its_range(self):
        got, _ = spread_tool.current()
        token = spread_tool.range_token(got)
        names = sorted({p for pattern in DOCUMENTS for p in REPO.glob(pattern)})
        naming = [p for p in names if JOB in p.read_text(encoding="utf-8")]
        assert len(naming) >= 20, f"only {len(naming)} documents name `{JOB}`"
        bare = {str(p.relative_to(REPO)): found for p in naming
                if (found := unpriced(p.read_text(encoding="utf-8"), token))}
        assert bare == {}, (
            f"sentence(s) price `{JOB}` in seconds without {token}: {bare}")


class TestAPopulationOfOneHasNoMedian:

    def test_one_reading_is_refused(self):
        with pytest.raises(spread_tool.TooFewRuns):
            spread_tool.spread([807])

    def test_the_tool_prints_no_median_for_one_run(self, tmp_path, monkeypatch, capsys):
        data = spread_tool.load()
        data["runs"] = data["runs"][:1]
        path = tmp_path / "clock.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(spread_tool, "DATA", path)
        assert spread_tool.main([]) == 1
        out = capsys.readouterr()
        assert "median" not in out.out, out.out
        assert "fewer than" in out.err, out.err

    def test_the_median_is_exact(self):
        assert spread_tool.spread([3, 1, 2])["twice_median"] == 4
        got = spread_tool.spread([620, 700, 815, 964])
        assert spread_tool.figure(got, "d").startswith("4 runs of main, median 757.5s, 620-964s")


class TestTheNoticeStep:

    def step(self):
        named = [s for s in steps() if s.get("name", "").startswith("UX-941")]
        assert len(named) == 1, [s.get("name") for s in steps()]
        return named[0]

    def test_it_follows_every_build_step_and_runs_always(self):
        """After every step that can write a figure; only `always()`
        steps, such as the upload or another row's notice, may follow."""
        step = self.step()
        assert step.get("if") == "always()", step.get("if")
        after = steps()[steps().index(step) + 1:]
        assert all(s.get("if") == "always()" for s in after), (
            [s.get("name") for s in after if s.get("if") != "always()"])
        assert steps().index(step) > max(
            n for n, s in enumerate(steps()) if "bga analyze -f json" in str(s.get("run", "")))

    def test_it_reads_the_toolchain_the_job_stages(self):
        run = self.step()["run"]
        assert "tools/dev_bst_examples_spread.py --notices artifacts " in run, run
        assert run.split()[-1] == spread_tool.TOOLCHAIN, run
        staging = (REPO / "examples" / "stage_cpp_toolchain.sh").read_text(encoding="utf-8")
        assert 'DEST="$HERE/' + spread_tool.TOOLCHAIN.removeprefix("examples/") + '"' in staging

    @pytest.mark.parametrize("name", spread_tool.REPORTS)
    def test_each_report_it_reads_is_one_the_job_writes(self, name):
        folder, base = name.split("/")
        text = job_text()
        assert f"OUT=artifacts/{folder}\n" in text, folder
        assert f'-f json -o "$OUT/{base}"' in text, base

    def test_the_command_prints_one_figure_per_line(self, tmp_path):
        """A step printing nothing, or an empty figure, reds here."""
        artifacts, toolchain = tmp_path / "artifacts", tmp_path / "toolchain"
        for name in spread_tool.REPORTS:
            (artifacts / name).parent.mkdir(parents=True, exist_ok=True)
            (artifacts / name).write_text(
                json.dumps({"graph_metrics": {"num_elements": 11}}), encoding="utf-8")
        for n in range(3):
            (toolchain / "nix" / "store" / f"{n:032d}-p{n}").mkdir(parents=True)
        run = self.step()["run"].split()
        out = subprocess.run(
            [sys.executable, *run[1:-2], str(artifacts), str(toolchain)],
            cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
        assert len(out) == 1 + len(spread_tool.REPORTS), out
        assert all(line.startswith("::notice title=UX-941 structural::") for line in out)
        assert "examples/05 toolchain: 3 store paths staged" in out[0], out[0]
        assert all(": 11 elements" in line for line in out[1:]), out

    def test_a_missing_input_is_reported_absent_never_silent(self, tmp_path):
        out = spread_tool.notices(str(tmp_path / "none"), str(tmp_path / "none"))
        assert len(out) == 1 + len(spread_tool.REPORTS)
        assert all(": absent " in line for line in out), out

    def test_it_stays_under_the_per_step_notice_cap(self):
        """GitHub's documented cap is 10 notices per step; not measured here."""
        assert 1 + len(spread_tool.REPORTS) <= 10


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
