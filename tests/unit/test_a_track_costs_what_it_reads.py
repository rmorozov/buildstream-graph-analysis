"""UX-525: the phase split of a track's tokens, and the one lever landed.

Round 75 recorded three tracks as three totals. `tools/dev_track_cost.py`
splits them, and two things it has to get right are guarded here: one API
response is one response however many JSONL records carry it (counting
records read 107 turns and 140,700 tokens where the truth is 65 and
78,583), and a response's cost belongs to the turn whose tool results it
is, not to the turn that received them.

The lever is `dev_touching`'s: a green run prints one line.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_touching, dev_track_cost


def _record(message_id, blocks, usage, stamp="2026-09-02T00:00:00.000Z"):
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": message_id, "content": blocks, "usage": usage}}


def _bash(command):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def _usage(fresh, read=0):
    return {"input_tokens": 0, "cache_creation_input_tokens": fresh,
            "cache_read_input_tokens": read, "output_tokens": 0}


def _transcript(tmp_path, records):
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return str(path)


class TestOneResponseIsCountedOnce:
    """The defect this tool shipped with in its first hour: the harness
    writes one record per content block, each repeating the same
    `usage`, so a per-record sum multiplied the track by 1.8x."""

    def test_three_records_of_one_response_are_one_response(self, tmp_path):
        blocks = [{"type": "thinking", "thinking": "x"},
                  _bash("sed -n '1,20p' bga/cli.py"), _bash("ls docs")]
        path = _transcript(tmp_path, [
            _record("msg_a", blocks[:1], _usage(500)),
            _record("msg_a", blocks[1:2], _usage(500)),
            _record("msg_a", blocks[2:], _usage(500)),
        ])
        assert len(dev_track_cost.responses(path)) == 1
        assert dev_track_cost.split(path)["responses"] == 1

    def test_the_tool_calls_of_all_its_records_are_kept(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [{"type": "text", "text": "hi"}], _usage(10)),
            _record("msg_a", [_bash("python3 -m pytest tests/unit -q")], _usage(10)),
        ])
        tools, _ = dev_track_cost.responses(path)[0]
        assert len(tools) == 1
        assert dev_track_cost.phases_of(tools) == {"test"}

    def test_the_total_is_the_sum_of_distinct_responses(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs")], _usage(100)),
            _record("msg_a", [_bash("ls tools")], _usage(100)),
            _record("msg_b", [_bash("ls tests")], _usage(400)),
        ])
        data = dev_track_cost.split(path)
        assert sum(tokens for _, tokens in data["phases"].values()) == 500


class TestTheCostGoesToTheTurnThatProducedIt:

    def test_a_pytest_run_is_charged_for_what_pytest_printed(self, tmp_path):
        """Response 1's `cache_creation` *is* response 0's pytest output.
        Charging it to response 1 would credit the phase that read it."""
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("python3 -m pytest tests/unit -q")], _usage(50)),
            _record("msg_b", [_bash("sed -n '1,5p' README.md")], _usage(9000)),
        ])
        phases = dev_track_cost.split(path)["phases"]
        assert phases["test"][1] == 9000, dict(phases)
        assert phases["read"][1] == 0, dict(phases)

    def test_the_first_response_is_the_brief_and_no_phase_of_the_track(
            self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs")], _usage(7000)),
        ])
        phases = dev_track_cost.split(path)["phases"]
        assert phases["brief"][1] == 7000, dict(phases)

    def test_cache_reads_are_not_in_the_total(self, tmp_path):
        """`cache_read_input_tokens` is the prefix re-read every turn -
        5.2M of it on a 78k track. Counting it would measure turns."""
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs")], _usage(100, read=50000)),
            _record("msg_b", [_bash("ls tools")], _usage(200, read=60000)),
        ])
        data = dev_track_cost.split(path)
        assert sum(t for _, t in data["phases"].values()) == 300
        assert data["cache_read"] == 110000


class TestThePhaseComesFromTheArgv:

    @pytest.mark.parametrize("command,phase", [
        ("python3 -m pytest tests/unit/test_x.py -q", "test"),
        ("make test-small", "test"),
        ("cp tools/x.py /tmp/x.bak && python3 -m pytest tests/unit -q", "falsify"),
        ("git commit -F - <<'EOF'", "close"),
        ("python3 tools/dev_close_task.py UX-1 --check", "close"),
        ("make lint", "close"),
        ("sed -n '1,40p' docs/spec/specification.md", "read"),
        ("git grep -n unclassified -- docs", "read"),
        ("sed -i 's/a/b/' bga/cli.py", "edit"),
    ])
    def test_a_command_lands_in_its_phase(self, command, phase):
        assert dev_track_cost.phases_of([_bash(command)]) == {phase}

    def test_a_write_to_a_task_file_is_the_outcome_not_an_edit(self):
        found = dev_track_cost.phases_of([{
            "type": "tool_use", "name": "Write",
            "input": {"file_path": "docs/backlog/scenarios/UX-0525-a-track.md"}}])
        assert found == {"outcome"}

    def test_a_turn_in_two_phases_is_charged_to_the_higher(self):
        found = dev_track_cost.phases_of(
            [_bash("ls docs"), _bash("python3 -m pytest tests -q")])
        assert found == {"read", "test"}
        assert dev_track_cost.rank(found) == "test"


class TestAGreenSelectorRunPrintsOneLine:
    """`UX-525`'s lever. Pytest output is 10.0-15.7% of a track's tokens
    and a passing run says nothing its summary does not."""

    def _run(self, monkeypatch, capsys, returncode, stdout):
        # `**_` on both: `UX-522` gave `changed_files` a `staged=` and
        # `select` a `census=`, and a stub that names its parameters is
        # a stub that breaks on the next one. What this clause is about
        # is the *printing*, not the selection.
        monkeypatch.setattr(dev_touching, "changed_files",
                            lambda *a, **_: ["bga/cli.py"])
        monkeypatch.setattr(dev_touching, "select",
                            lambda *a, **_: (["tests/unit/test_cli.py"], {}))

        class Done:
            pass

        done = Done()
        done.returncode, done.stdout, done.stderr = returncode, stdout, ""
        monkeypatch.setattr(dev_touching.subprocess, "run",
                            lambda *a, **k: done)
        code = dev_touching.main([])
        captured = capsys.readouterr()
        return code, captured.out + captured.err

    GREEN = ("=== test session starts ===\nplatform linux\nrootdir: /x\n"
             "plugins: xdist\n4 workers [99 items]\n\n....\n"
             "=========== 99 passed in 20.54s ===========\n")
    RED = GREEN.replace("99 passed", "1 failed, 98 passed") + "FAILED tests/x\n"

    def test_green_is_one_line(self, monkeypatch, capsys):
        code, said = self._run(monkeypatch, capsys, 0, self.GREEN)
        assert code == 0
        assert len([line for line in said.splitlines() if line.strip()]) == 1, said
        assert "99 passed in 20.54s" in said, said

    def test_red_is_the_whole_run(self, monkeypatch, capsys):
        code, said = self._run(monkeypatch, capsys, 1, self.RED)
        assert code == 1
        assert "FAILED tests/x" in said, said
        assert "rootdir: /x" in said, said

    def test_the_summary_line_is_read_from_pytest_not_composed(self):
        assert dev_touching.last_line("a\n\n==== 3 passed in 1.0s ====\n") \
            == "3 passed in 1.0s"
        assert dev_touching.last_line("") == "no output"
