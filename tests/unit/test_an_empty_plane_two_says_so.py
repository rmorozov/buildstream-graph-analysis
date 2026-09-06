"""UX-726: a Plane 2 report that recorded nothing says which absence it is.

`plane2.absence` modelled three states. A fourth exists and returned
`None` - "no absence at all" - which is the one state a reader cannot
act on. Measured on a copy of `examples/08-process-storm`, isolated
`XDG_CACHE_HOME`, one cold build per flag set:

```text
flags                                  plane2.json  process_count  absence()
--no-trace-opens --trace-spine=off     written                  0  None
--no-inject                            written                  0  None
```

Every `bga snapshot` flag that reads like "off" produces this, and so
does a hook that failed to attach - a fine measurement and a broken
machine, told apart by nothing. `cli.md:129` promises the report says
which absence it is; this was the absence it could not name.

The state is `CAPTURED_EMPTY` now. The flags are unchanged: they are
orthogonal - opened paths, the ptrace spine, the argv rewrite - and
none claims to be "capture Plane 1 alone". `bga wrap` + `bga extract`
is that, and the sentence says so.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2


def _run(tmp_path, *, process_count, raw_log=True):
    """A snapshot-shaped directory: a `run/` with its Plane 2 siblings.

    Built rather than captured: this file's claim is about which
    sentence `absence` returns for a given tree, and a real `bst build`
    would spend a minute arriving at the same four files.
    """
    snapshot = tmp_path / "20260906T000000Z"
    run = snapshot / "run"
    run.mkdir(parents=True)
    (snapshot / "plane2.json").write_text(json.dumps({
        "schema": "plane2/v3", "process_count": process_count,
        "matched_count": 0, "open_count": 0, "by_binary": []}))
    if raw_log:
        (snapshot / "plane2.log.gz").write_bytes(b"")
    return str(run)


class TestTheFourthStateHasASentence:
    def test_a_report_that_counted_nothing_is_named(self, tmp_path):
        assert plane2.absence(_run(tmp_path, process_count=0)) \
            == plane2.CAPTURED_EMPTY

    def test_a_report_with_processes_has_no_absence(self, tmp_path):
        """The discriminating half. Without it the clause above passes
        for a version returning `CAPTURED_EMPTY` unconditionally."""
        assert plane2.absence(_run(tmp_path, process_count=7)) is None

    def test_a_missing_raw_log_still_wins(self, tmp_path):
        """Order matters: the three older states are about what is
        beside the run, this one about what is inside the report. A run
        with neither reports the older, more actionable one."""
        assert plane2.absence(_run(tmp_path, process_count=0, raw_log=False)) \
            == plane2.CAPTURED_NO_RAW_LOG

    def test_no_plane_two_at_all_still_wins(self, tmp_path):
        run = tmp_path / "20260906T000000Z" / "run"
        run.mkdir(parents=True)
        assert plane2.absence(str(run)) == plane2.NOT_CAPTURED

    def test_a_corrupt_report_is_not_called_empty(self, tmp_path):
        """`absence` has already ruled the file present, so a read that
        fails is a corrupt report and not an empty one. Saying
        "recorded nothing" about it would be a guess."""
        run = _run(tmp_path, process_count=0)
        (pathlib.Path(run).parent / "plane2.json").write_text("{not json")
        assert plane2.absence(run) is None


class TestTheSentenceIsUsable:
    def test_it_names_the_flags_that_produce_it(self):
        """The reader arriving here typed one of them. A sentence that
        said only "empty" would leave them to guess which."""
        for flag in ("--no-inject", "--no-trace-opens", "--trace-spine=off"):
            assert flag in plane2.CAPTURED_EMPTY, flag

    def test_it_names_the_path_that_captures_plane_one_alone(self):
        assert "bga wrap" in plane2.CAPTURED_EMPTY
        assert "bga extract" in plane2.CAPTURED_EMPTY

    def test_it_says_a_failed_hook_looks_the_same(self):
        """The half that makes it honest rather than reassuring: this
        sentence cannot tell a deliberate Plane-1 capture from a hook
        that did not attach, and says so."""
        assert "failed to attach" in plane2.CAPTURED_EMPTY

    def test_the_four_sentences_are_four(self):
        said = {plane2.NOT_CAPTURED, plane2.CAPTURED_NO_RAW_LOG,
                plane2.DECLINED, plane2.CAPTURED_EMPTY}
        assert len(said) == 4
