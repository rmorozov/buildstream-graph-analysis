"""UX-312: a canned question may only name vocabulary the trace emits.

The library is a promise: these are the questions worth asking, and
here is the SQL that asks them. A query that names a key the emitter
never writes does not fail loudly - `extract_arg` returns null and the
question returns **zero rows in silence**, which is the worst way for a
canned answer to be wrong.

**That is not hypothetical; it is what this file was written after.**
`UX-204` wrote the library against the legacy Chrome JSON trace, where
an `args` object becomes `args.<key>` in `trace_processor` and the
converter wrote a `cat` field. `UX-298` made Perfetto's own TrackEvent
the default format, where the same facts are *debug annotations* under
`debug.<key>` - and `EVENT_CATEGORY_IIDS` was "reserved rather than
used" until `UX-308` spent it on `failed`. Nobody re-pointed the
library. Measured on a trace rendered by this tree at the commit before
the fix: **all six questions dead**, every one of them on both
channels at once.

So the rule this file holds is the one nothing held then: every
`debug.` key a question names is in `ANNOTATION_CONTRACT`, every
category it scopes by is one the emitter emits, every counter track it
selects is one the emitter creates - and the contract is documented
where a reader can find it, in both directions.
"""
import gzip
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bga_timeline  # noqa: E402
from tools.native_trace import trackevent  # noqa: E402

QUESTIONS_JS = REPO / "bga/viewer/questions.js"
DICTIONARY = REPO / "docs/spec/trace-dictionary.md"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _questions():
    """The library, as data, read by running the module it lives in."""
    script = ('const { QUESTIONS } = await import("./bga/viewer/questions.js");'
              'console.log(JSON.stringify(QUESTIONS));')
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _arg_keys(sql):
    return set(re.findall(r"'debug\.([a-z_0-9]+)'", sql))


def _categories(sql):
    return set(re.findall(r"category\s+glob\s+'\*([a-z0-9-]+)\*'", sql)) | set(
        re.findall(r"category\s*=\s*'([a-z0-9-]+)'", sql))


CONTRACT = {key for key, _why in bga_timeline.ANNOTATION_CONTRACT}
EMITTED_CATEGORIES = {bga_timeline.CATEGORY_PLANE1,
                      bga_timeline.CATEGORY_PLANE2,
                      bga_timeline.CATEGORY_RUN,
                      bga_timeline.CATEGORY_FAILED}


@needs_node
class TestEveryQuestionNamesEmittedVocabulary:

    def test_every_debug_key_is_in_the_contract(self):
        unknown = {}
        for question in _questions():
            missing = _arg_keys(question["sql"]) - CONTRACT
            if missing:
                unknown[question["id"]] = sorted(missing)
        assert unknown == {}, (
            f"question(s) selecting an annotation key the emitter never "
            f"writes - `extract_arg` returns null and the question returns "
            f"nothing, silently: {unknown}")

    def test_no_question_still_uses_the_chrome_arg_namespace(self):
        """The exact defect, named so it cannot come back quietly.

        `args.<key>` was right for the Chrome JSON trace and is wrong
        for every trace `bga timeline` writes by default.
        """
        offenders = [q["id"] for q in _questions() if "'args." in q["sql"]]
        assert offenders == [], (
            f"{offenders} select `args.<key>`, which is the legacy Chrome "
            f"converter's namespace; a TrackEvent debug annotation is "
            f"`debug.<key>`")

    def test_every_category_is_one_the_emitter_emits(self):
        unknown = {}
        for question in _questions():
            missing = _categories(question["sql"]) - EMITTED_CATEGORIES
            if missing:
                unknown[question["id"]] = sorted(missing)
        assert unknown == {}, (
            f"question(s) scoping by a category no slice carries: {unknown}")

    def test_a_question_that_scopes_by_plane_uses_glob(self):
        """A slice may carry two categories.

        `trace_processor` joins them into one string, so a failed Plane
        2 process reads `native-process,failed` and `= 'native-process'`
        misses it - which would make the failures invisible to exactly
        the questions about resources and time.
        """
        for question in _questions():
            for bad in re.findall(r"category\s*=\s*'([a-z0-9-]+)'",
                                  question["sql"]):
                pytest.fail(
                    f"{question['id']} matches category with `= '{bad}'`; a "
                    f"slice may carry more than one, so this must be `glob`")

    def test_every_counter_track_named_is_one_the_emitter_creates(self):
        emitted = {bga_timeline.CONCURRENCY_COUNTER}
        for question in _questions():
            for name in re.findall(r"t\.name\s*=\s*'([^']+)'", question["sql"]):
                assert name in emitted, (
                    f"{question['id']} selects counter track {name!r}; the "
                    f"emitter creates {sorted(emitted)}")

    def test_the_flow_questions_join_the_flow_table(self):
        """`UX-309`'s edges are `flow` rows, not timestamp proximity."""
        flow = next(q for q in _questions() if q["id"] == "waited-on-flow")
        assert "from flow" in flow["sql"]
        assert "slice_out" in flow["sql"] and "slice_in" in flow["sql"]


class TestTheTraceDictionaryIsTheOneDocumentedPlace:
    """`UX-190`'s discipline, applied to annotation keys.

    Two copies of one fact drift; the guard is what keeps them from
    drifting silently. A rename is a break, and the dictionary is where
    a reader finds out what a key means without reading the emitter.
    """

    def _documented(self):
        """The keys table only.

        The scope and category tables below it have the same row shape,
        so a regex over the whole document reads `failed` - a category -
        as an annotation key and reports it undocumented-in-reverse.
        The section heading is the boundary, and reading it that way is
        what keeps the two tables from having to look different for the
        guard's benefit.
        """
        text = DICTIONARY.read_text(encoding="utf-8")
        assert "## The keys" in text, "the dictionary has no keys section"
        section = text.split("## The keys", 1)[1].split("\n## ", 1)[0]
        return set(re.findall(r"^\| `([a-z_0-9]+)` \|", section, re.M)), text

    def _key_rows(self):
        text = DICTIONARY.read_text(encoding="utf-8")
        section = text.split("## The keys", 1)[1].split("\n## ", 1)[0]
        return re.findall(r"^\| `([a-z_0-9]+)` \| ([^|]+) \|", section, re.M)

    def test_the_dictionary_exists_and_documents_every_emitted_key(self):
        documented, _text = self._documented()
        missing = CONTRACT - documented
        assert missing == set(), (
            f"emitted annotation key(s) documented nowhere: "
            f"{sorted(missing)}. A key nobody wrote down is a key a query "
            f"cannot be written against on purpose")

    def test_it_documents_nothing_the_emitter_does_not_write(self):
        documented, _text = self._documented()
        extra = documented - CONTRACT
        assert extra == set(), (
            f"documented key(s) the emitter never writes: {sorted(extra)}. A "
            f"reader would build a query on them and get nothing back")

    def test_every_key_says_which_plane_it_rides(self):
        rows = self._key_rows()
        assert len(rows) == len(CONTRACT), (len(rows), len(CONTRACT))
        planes = {"Plane 1", "Plane 2", "run"}
        for key, plane in rows:
            assert plane.strip() in planes, (
                f"`{key}` rides {plane.strip()!r}; a key belongs to one of "
                f"{sorted(planes)} and a reader scopes their query by it")

    def test_the_stability_rule_is_written_down(self):
        _documented, text = self._documented()
        assert "rename is a break" in text, (
            "the dictionary does not say that renaming a key breaks saved "
            "queries, which is the whole reason it is a contract")

    def test_the_categories_and_the_counter_are_documented_too(self):
        _documented, text = self._documented()
        for name in sorted(EMITTED_CATEGORIES):
            assert f"`{name}`" in text, f"category {name} is undocumented"
        assert f"`{bga_timeline.CONCURRENCY_COUNTER}`" in text


class TestTheEmittedTraceCarriesWhatTheQuestionsScopeBy:
    """Read off the wire, not asserted about the source.

    The plane categories are the channel every scoped question depends
    on, and they were absent from the emitted trace for two rounds while
    the source still named them. Only the bytes settle it.
    """

    @pytest.fixture(scope="class")
    def decoded(self):
        sys.path.insert(0, str(REPO / "tests/unit"))
        from test_the_timeline_speaks_perfetto import _snapshot, _fields

        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            snapshot = _snapshot(tmp)
            out = tmp / "trace.gz"
            bga_timeline.render(str(snapshot), str(out))
            raw = gzip.open(out, "rb").read()
            packets = [v for f, w, v in _fields(raw)
                       if f == trackevent.TRACE_PACKET and w == 2]
            names, used = {}, {}
            for packet in packets:
                for field, _w, value in _fields(packet):
                    if field == trackevent.PACKET_INTERNED_DATA:
                        for inner, _ww, entry in _fields(value):
                            if inner != trackevent.INTERNED_EVENT_CATEGORIES:
                                continue
                            iid = name = None
                            for i, _x, payload in _fields(entry):
                                if i == 1:
                                    iid = payload
                                elif i == 2:
                                    name = payload.decode("utf-8")
                            names[iid] = name
                    elif field == trackevent.PACKET_TRACK_EVENT:
                        for inner, _ww, payload in _fields(value):
                            if inner == trackevent.EVENT_CATEGORY_IIDS:
                                used[payload] = used.get(payload, 0) + 1
            return {names[iid]: count for iid, count in used.items()}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_both_planes_tag_their_slices(self, decoded):
        assert decoded.get(bga_timeline.CATEGORY_PLANE1, 0) > 0, decoded
        assert decoded.get(bga_timeline.CATEGORY_PLANE2, 0) > 0, decoded

    def test_every_slice_carries_a_scope(self, decoded):
        """Not a sample of them. A question scoped by plane that misses
        slices is a wrong answer rather than a missing one, so the three
        scopes have to partition the trace rather than cover most of
        it. The run-identity instant is the third: it belongs to
        neither plane, and leaving it uncategorised is how a partition
        stops being one."""
        planes = (decoded.get(bga_timeline.CATEGORY_PLANE1, 0)
                  + decoded.get(bga_timeline.CATEGORY_PLANE2, 0)
                  + decoded.get(bga_timeline.CATEGORY_RUN, 0))
        sys.path.insert(0, str(REPO / "tests/unit"))
        from test_the_timeline_speaks_perfetto import _snapshot

        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            result = bga_timeline.render(str(_snapshot(tmp)),
                                         str(tmp / "t.gz"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        assert planes == result["slices"], (planes, result["slices"])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
