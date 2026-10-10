"""UX-1351: a ledger row carries the run's dollars and its model's version.

The figures below are the 2026-10-10 probe's own transcripts, priced by
hand from the billing table: Claude Code reported $0.1636 and $0.0168.
"""

import datetime
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_retro as retro

from tools import dev_process_bands, dev_track_cost


def _usage(fresh=0, out=0, read=0, hour=0, five=0, iterations=None):
    usage = {
        "input_tokens": fresh,
        "output_tokens": out,
        "cache_read_input_tokens": read,
        "cache_creation_input_tokens": hour + five,
        "cache_creation": {"ephemeral_1h_input_tokens": hour, "ephemeral_5m_input_tokens": five},
    }
    if iterations:
        usage["iterations"] = iterations
    return usage


class TestAResponseIsPricedAtItsModel:
    def test_sonnet_5_5_reads_at_ten_cents(self):
        # 1M cache reads, 1M one-hour writes, 1M output: 0.10 + 4 + 10.
        assert round(dev_track_cost.price(_usage(read=10**6, hour=10**6, out=10**6), "claude-sonnet-5-5"), 6) == 14.1

    def test_a_five_minute_write_is_cheaper_than_an_hour(self):
        five = dev_track_cost.price(_usage(five=10**6), "claude-opus-5-5")
        hour = dev_track_cost.price(_usage(hour=10**6), "claude-opus-5-5")
        assert (round(five, 6), round(hour, 6)) == (5.0, 8.0)

    def test_the_1m_suffix_and_a_date_name_the_same_rates(self):
        usage = _usage(fresh=1000, out=1000)
        assert dev_track_cost.price(usage, "claude-opus-5-5[1m]") == dev_track_cost.price(usage, "claude-opus-5-5")

    def test_an_unpriced_model_is_unknown_not_zero(self):
        assert dev_track_cost.price(_usage(fresh=1000), "claude-unknown-9") is None


class TestHaikusLongPromptCard:
    def test_a_prompt_at_100k_is_the_short_card(self):
        dollars = dev_track_cost.price(_usage(read=100_000, out=10**6), "claude-haiku-5-5")
        assert round(dollars, 6) == round(100_000 * 0.01 / 1e6 + 0.50, 6)

    def test_a_prompt_over_100k_is_five_times(self):
        dollars = dev_track_cost.price(_usage(read=100_001, out=10**6), "claude-haiku-5-5")
        assert round(dollars, 6) == round(100_001 * 0.05 / 1e6 + 2.50, 6)

    def test_sonnet_has_no_second_card(self):
        short = dev_track_cost.price(_usage(read=50_000), "claude-sonnet-5-5") / 50_000
        long = dev_track_cost.price(_usage(read=500_000), "claude-sonnet-5-5") / 500_000
        assert round(short, 12) == round(long, 12)


class TestAnAdvisorConsultIsBilledInside:
    def test_the_consult_is_priced_at_the_advisors_model(self):
        consult = {"type": "advisor_message", "model": "claude-fable-5-1", "input_tokens": 50_383, "output_tokens": 427}
        alone = dev_track_cost.price(_usage(fresh=4, out=108), "claude-sonnet-5-5")
        both = dev_track_cost.price(_usage(fresh=4, out=108, iterations=[consult]), "claude-sonnet-5-5")
        assert round(both - alone, 5) == 0.52518


def _transcript(tmp_path, model, usages):
    import json

    path = tmp_path / "t.jsonl"
    records = [
        {
            "type": "assistant",
            "timestamp": f"2026-10-10T00:0{i}:00Z",
            "attributionAgent": "verifier",
            "message": {"id": f"m{i}", "model": model, "content": [], "usage": usage},
        }
        for i, usage in enumerate(usages)
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return str(path)


class TestTheRowCarriesCostAndVersion:
    def test_the_row_prices_the_run_and_names_the_version(self, tmp_path):
        path = _transcript(tmp_path, "claude-sonnet-5-5", [_usage(read=10**6, out=10**5)] * 2)
        row = dev_track_cost.ledger_row(path, 172, "UX-1 verifier", "PASS", "-")
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert cells[2] == "sonnet-5-5", row
        assert cells[7] == "$2.20", row

    def test_a_run_with_an_unpriced_response_reads_unknown(self, tmp_path):
        path = _transcript(tmp_path, "claude-unknown-9", [_usage(fresh=1000)])
        cells = [c.strip() for c in dev_track_cost.ledger_row(path, 1, "t", "o", "-").strip("|").split("|")]
        assert cells[7] == "—"


class TestTheReadersTakeBothWidths:
    def test_a_ten_cell_row_is_costed_and_a_nine_cell_row_is_not(self, tmp_path):
        ledger = tmp_path / "agent-runs.md"
        ledger.write_text(
            "| 171 | verifier | sonnet | a | 50k | 3 | 2 m | PASS | - |\n"
            "| 172 | verifier | haiku-5-5 | b | 40k | 3 | 2 m | $0.02 | PASS | - |\n",
            encoding="utf-8",
        )
        old, new = dev_process_bands.ledger_runs(ledger)
        assert (old["cost"], old["outcome"]) == (None, "PASS")
        assert (new["cost"], new["outcome"]) == (0.02, "PASS")

    def test_the_live_ledger_is_ten_cells_wide(self):
        lines = (REPO / "docs/audits/agent-runs.md").read_text(encoding="utf-8").splitlines()
        rows = [r for r in lines if r.startswith("| ") and r.split("|")[1].strip().isdigit()]
        assert rows and {len(r.split("|")) - 2 for r in rows} == {10}


def _git(repo, *argv, date=None):
    env = (
        {**os.environ, "GIT_AUTHOR_DATE": f"{date}T12:00:00", "GIT_COMMITTER_DATE": f"{date}T12:00:00"}
        if date
        else None
    )
    return subprocess.run(["git", *argv], cwd=repo, check=True, env=env, capture_output=True, text=True)


class TestARewrittenRowIsNotANewRun:
    def test_widening_every_row_adds_no_retro_finding(self, tmp_path):
        today = datetime.date.today()
        repo = tmp_path / "repo"
        (repo / "docs/audits").mkdir(parents=True)
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "a@b")
        _git(repo, "config", "user.name", "a")
        ledger = repo / "docs/audits/agent-runs.md"
        ledger.write_text("| 1 | implementer | sonnet | UX-1 | 10k | 5 | 1 m | merged | tools/dev_probe.py drifted |\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-qm", "row", date=(today - datetime.timedelta(days=30)).isoformat())
        ledger.write_text(
            "| 1 | implementer | sonnet | UX-1 | 10k | 5 | 1 m | — | merged | tools/dev_probe.py drifted |\n"
        )
        _git(repo, "commit", "-qam", "widen", date=(today - datetime.timedelta(days=3)).isoformat())
        since = (today - datetime.timedelta(days=10)).isoformat()
        findings, no_command = retro.ledger_findings(repo, since)
        assert (findings, no_command) == ([], 0)
