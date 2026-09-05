"""UX-710: an `agent-runs.md` row derived from the transcript, not typed.

Round 93's researcher row said 62k where the transcript's own sum said
58.5k. This guards that `--ledger`'s model comes from the records'
`message.model`, never a frontmatter claim, and that the cell order
matches the ledger header's.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_track_cost

HEADER = ("| round | agent | model | task | tokens | tool calls | wall | "
          "outcome | what cost the most / what went wrong |")


def _record(message_id, blocks, usage, stamp, agent="researcher",
            model="claude-sonnet-5"):
    return {"type": "assistant", "timestamp": stamp, "attributionAgent": agent,
            "message": {"id": message_id, "content": blocks, "usage": usage,
                        "model": model}}


def _bash(command):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def _usage(fresh):
    return {"input_tokens": 0, "cache_creation_input_tokens": fresh,
            "cache_read_input_tokens": 0, "output_tokens": 0}


def _transcript(tmp_path, records):
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return str(path)


class TestTheCellOrderIsTheHeaders:

    def test_the_row_has_nine_cells_in_header_order(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs"), _bash("ls tools")], _usage(50000),
                    "2026-09-05T00:00:00Z"),
            _record("msg_b", [_bash("ls tests")], _usage(20000),
                    "2026-09-05T00:05:00Z"),
        ])
        row = dev_track_cost.ledger_row(
            path, 94, "a task", "complete", "no friction")
        header_cells = [c.strip() for c in HEADER.strip("|").split("|")]
        row_cells = [c.strip() for c in row.strip("|").split("|")]
        assert len(row_cells) == len(header_cells) == 9, row
        assert row_cells[0] == "94"
        assert row_cells[1] == "researcher"
        assert row_cells[3] == "a task"
        assert row_cells[7] == "complete"
        assert row_cells[8] == "no friction"


class TestTheModelComesFromTheRecords:

    def test_the_model_column_is_the_records_model(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs")], _usage(1000),
                    "2026-09-05T00:00:00Z", model="claude-opus-5"),
        ])
        row = dev_track_cost.ledger_row(path, 1, "t", "complete", "-")
        assert "| opus |" in row, row

    def test_a_different_model_prints_a_different_word(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs")], _usage(1000),
                    "2026-09-05T00:00:00Z", model="claude-fable-5-1"),
        ])
        row = dev_track_cost.ledger_row(path, 1, "t", "complete", "-")
        assert "| fable |" in row, row


class TestTheToolCallCount:

    def test_tool_calls_is_the_count_of_tool_use_blocks(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs"), _bash("ls tools")], _usage(1000),
                    "2026-09-05T00:00:00Z"),
            _record("msg_b", [_bash("ls tests")], _usage(1000),
                    "2026-09-05T00:01:00Z"),
        ])
        row = dev_track_cost.ledger_row(path, 1, "t", "complete", "-")
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert cells[5] == "3", row


class TestListSkipsWhatIsNotATranscript:
    """`tasks/*.output` also holds a Bash run's own stdout, plain text
    that is not a JSONL record at all - `--list` must step over it."""

    def test_the_transcript_is_named_and_the_plain_text_is_not(
            self, tmp_path, capsys):
        tasks = tmp_path / "tasks"
        tasks.mkdir()
        (tasks / "x1.output").write_text(
            json.dumps({"type": "assistant",
                        "message": {"content": "Implement **UX-999** only."}})
            + "\n", encoding="utf-8")
        (tasks / "x2.output").write_text(
            "5 passed in 1.2s\n", encoding="utf-8")
        code = dev_track_cost.main(["--list", "--root", str(tmp_path)])
        said = capsys.readouterr().out
        assert code == 0
        assert "x1.output" in said, said
        assert "x2.output" not in said, said
