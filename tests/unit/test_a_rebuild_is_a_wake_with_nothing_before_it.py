"""UX-707: a rebuild is a big response with nothing before it.

Round 94 read this session's own transcript: 11 of 336 responses, each
over 30k fresh tokens with no tool call in the response before it, were
73% of the session. This guards the two ways that count is wrong: a big
response counted because a tool ran just before it, and a small one
counted because nothing did.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_track_cost


def _record(message_id, blocks, usage, stamp):
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": message_id, "content": blocks, "usage": usage}}


def _bash(command):
    return {"type": "tool_use", "name": "Bash", "input": {"command": command}}


def _text(words):
    return {"type": "text", "text": words}


def _usage(fresh):
    return {"input_tokens": 0, "cache_creation_input_tokens": fresh,
            "cache_read_input_tokens": 0, "output_tokens": 0}


def _transcript(tmp_path, records, name="t.jsonl"):
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return str(path)


class TestTheFirstResponseHasNothingBeforeItEither:

    def test_a_big_first_response_is_a_rebuild(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_text("thinking")], _usage(500000),
                    "2026-09-05T00:00:00.000Z"),
            _record("msg_b", [_bash("ls docs")], _usage(10),
                    "2026-09-05T00:01:00.000Z"),
        ])
        data = dev_track_cost.rebuilds(path)
        assert data["count"] == 1, data
        assert data["tokens"] == 500000


class TestAToolBeforeItIsNotARebuild:

    def test_a_big_response_after_a_tool_carrying_one_is_not_a_rebuild(
            self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_bash("ls docs")], _usage(5000),
                    "2026-09-05T00:00:00.000Z"),
            _record("msg_b", [_text("done")], _usage(50000),
                    "2026-09-05T00:01:00.000Z"),
        ])
        data = dev_track_cost.rebuilds(path)
        assert data["count"] == 0, data

    def test_a_big_response_after_a_text_only_one_is_a_rebuild(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_text("thinking")], _usage(5000),
                    "2026-09-05T00:00:00.000Z"),
            _record("msg_b", [_bash("ls docs")], _usage(50000),
                    "2026-09-05T00:01:00.000Z"),
        ])
        data = dev_track_cost.rebuilds(path)
        assert data["count"] == 1, data
        assert data["tokens"] == 50000
        assert data["rebuilds"][0]["timestamp"] == "2026-09-05T00:01:00.000Z"


class TestTheFloorIsHonoured:

    def test_a_response_at_the_floor_is_not_over_it(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_text("thinking")], _usage(10), "2026-09-05T00:00:00Z"),
            _record("msg_b", [_bash("ls docs")], _usage(30000),
                    "2026-09-05T00:01:00Z"),
        ])
        data = dev_track_cost.rebuilds(path, floor=30000)
        assert data["count"] == 0, data

    def test_a_lower_floor_catches_a_response_the_default_would_not(
            self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_text("thinking")], _usage(10), "2026-09-05T00:00:00Z"),
            _record("msg_b", [_bash("ls docs")], _usage(30000),
                    "2026-09-05T00:01:00Z"),
        ])
        data = dev_track_cost.rebuilds(path, floor=100)
        assert data["count"] == 1, data


class TestTheRoundSplitSumsToTheTotal:

    def test_two_rounds_partition_the_session(self, tmp_path):
        path = _transcript(tmp_path, [
            _record("msg_a", [_text("thinking")], _usage(1000),
                    "2026-09-05T00:00:00Z"),
            _record("msg_b", [_bash("ls docs")], _usage(50000),
                    "2026-09-05T00:01:00Z"),
            _record("msg_c", [_text("thinking")], _usage(2000),
                    "2026-09-05T01:00:00Z"),
            _record("msg_d", [_bash("ls tools")], _usage(60000),
                    "2026-09-05T01:01:00Z"),
        ])
        totals = dev_track_cost.round_totals(
            path, "one=2026-09-05T00:00:00Z,two=2026-09-05T00:30:00Z")
        assert sum(t["responses"] for t in totals.values()) == 4
        assert sum(t["tokens"] for t in totals.values()) == 113000
        assert sum(t["rebuilds"] for t in totals.values()) == 2
        assert totals["one"]["tokens"] == 51000
        assert totals["two"]["tokens"] == 62000
