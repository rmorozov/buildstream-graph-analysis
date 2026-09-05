"""The boundary between the page and the trace, held as a property.

`docs/guides/what-the-viewer-answers.md` states one rule:

> The report has no time axis. Every number in it is a total, a
> per-element aggregate, or a ranking. The moment a question needs
> *when*, or needs an individual **process**, its answer is not in the
> report — and Perfetto is the instrument.

A guide that states a rule the code does not keep is worse than no
guide, so this file holds the rule rather than the prose. Two halves:

* the report really has no time axis, and really does carry the
  per-element side of each of the three crossings the guide names;
* every canned question the guide sorts into "needs Perfetto" really
  does read a per-process or per-instant thing, which is checkable
  from the SQL: those are the `debug.` keys Plane 2 carries, and the
  counter track.

What it deliberately does not check is the *sorting* of the seven
questions the guide says the page already answers. That is a judgement
about what a reader wants, not a property of the payload, and a guard
that pretended otherwise would be asserting its own opinion.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bga_view import _degradation_steps, payloads

RUN = REPO / "tests/fixtures/macro_micro/run"
GUIDE = REPO / "docs/guides/what-the-viewer-answers.md"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# The per-element half of each crossing the guide names. If one of
# these disappears the guide's table is wrong.
CROSSINGS = ("peak_rss_bytes", "dominant_binary")

def _guide_tables():
    """The two question tables of the guide, as `{id}` sets.

    Read out of the document rather than restated here. The first cut
    of this file wrote the "needs Perfetto" list as a literal, which
    made the guard a check that the *library* still had six named
    questions - not that the guide sorted the library. Three questions
    were added over three rounds and none of them reached the guide;
    the count in its own prose said thirteen while the library served
    sixteen, and every clause in this file was green.
    """
    text = GUIDE.read_text(encoding="utf-8")
    body = text.split("## The canned questions", 1)[1].split("\n## ", 1)[0]
    needs, rest = body.split("**Does not need Perfetto", 1)
    return (frozenset(re.findall(r"^\| `([a-z-]+)` \|", needs, re.M)),
            frozenset(re.findall(r"^\| `([a-z-]+)` \|", rest, re.M)))


#: The questions the guide sorts as genuinely needing the trace.
NEEDS_PERFETTO, ANSWERED_BY_THE_PAGE = _guide_tables()

# What makes a query need the trace: it reads something finer than any
# population the report publishes.
#
# Usually that is one row **per process** or per instant, and two ways
# that shows up - the first draft of this guard only had the second.
# `element-commands` reads `s.name` and `s.dur` - the process *slice
# itself* - and no `debug.` annotation at all, so a pattern looking
# only for annotations called it a Plane 1 question. Scoping to the
# Plane 2 category is the real marker: one row per process.
#
# `debug.resource` is the one Plane 1 entry, and it is here for the
# same reason rather than as an exception (`UX-469`): the report's
# `attribution.resource_wait_us` is the waiting summed over every
# scheduler queue at once and `floors.lb` is the max over their
# ratios, so no published population is per queue. The trace is where
# that granularity exists.
#
# `debug.element` and `debug.kind` are deliberately absent - `UX-321`
# put `element` on both planes, so reading it says nothing about
# granularity.
ONLY_THE_TRACE = re.compile(
    r"category\s+glob\s+'\*native-process\*'"
    r"|debug\.(cmd|max_rss_kb|cpu_us|exit_status|resource)\b"
    r"|counter")


def _report():
    return payloads(str(RUN))["report.json"]


class TestTheReportHasNoTimeAxis:
    """The load-bearing half of the rule."""

    def test_occupancy_is_scalars_not_a_series(self):
        occupancy = _report()["occupancy"]
        for key in ("peak_concurrency", "average_concurrency"):
            value = occupancy[key]
            assert isinstance(value, (int, float)), (
                f"occupancy.{key} is {type(value).__name__}, not a scalar. "
                "If the report grew a concurrency series, the guide's rule "
                "and its `concurrency-curve` row are both out of date.")

    def test_utilisation_buckets_are_totals_not_instants(self):
        """The one section that looks like a series and is not."""
        buckets = _report()["utilisation"]["buckets"]
        assert isinstance(buckets, dict), (
            f"utilisation.buckets is a {type(buckets).__name__}; it was a "
            "dict of six totals when the guide was written, and a list "
            "would mean it had become a series")
        assert all(isinstance(v, (int, float)) for v in buckets.values()), (
            "a utilisation bucket stopped being a single total")

    def test_no_section_carries_a_list_of_timestamps(self):
        """The general form, so a new section cannot slip a series in."""
        report = _report()
        suspicious = []

        def walk(node, path):
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(value, f"{path}.{key}")
            # A list of bare numbers under a time-ish name is what a
            # series looks like. Element rows are lists of dicts.
            elif (isinstance(node, list) and len(node) > 3
                  and all(isinstance(v, (int, float)) for v in node)
                  and re.search(r"(time|ts|us|series|curve|samples)", path, re.I)):
                suspicious.append((path, len(node)))

        walk(report, "report")
        assert not suspicious, (
            f"a time series appeared in the report: {suspicious}. That is "
            "not forbidden - but it moves the boundary the guide states, "
            "so update the guide in the same change.")

    @pytest.mark.parametrize("key", CROSSINGS)
    def test_the_report_carries_the_per_element_side_of_each_crossing(self, key):
        elements = _report()["element_join"]
        assert elements, "element_join is empty; the crossings are unreadable"
        assert any(key in row for row in elements), (
            f"no element carries {key!r}, which the guide's crossing table "
            "names as the report's half of the answer")


@needs_node
class TestTheQuestionsThatNeedTheTraceReallyDo:

    def test_each_one_reads_something_only_the_trace_has(self):
        script = ('const { QUESTIONS } = await import('
                  '"./bga/viewer/questions.js");'
                  'console.log(JSON.stringify(QUESTIONS));')
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=60)
        assert done.returncode == 0, done.stderr
        questions = {q["id"]: q for q in json.loads(done.stdout)}

        missing = sorted(NEEDS_PERFETTO - set(questions))
        assert not missing, (
            f"the guide sorts {missing} as needing Perfetto and the library "
            "has no such question - one was renamed or removed")

        for qid in sorted(NEEDS_PERFETTO):
            sql = questions[qid]["sql"]
            assert ONLY_THE_TRACE.search(sql), (
                f"{qid} is listed as needing the trace, but its SQL reads "
                "nothing the report does not already publish. Either the "
                "query changed or it belongs in the other table.")


    def test_the_guide_sorts_every_question_the_library_serves(self):
        """The direction that was missing, and the reason it mattered.

        The clause above asks whether every question the guide *names*
        is in the library. That cannot see a question the library
        gained and the guide never heard of - which is exactly what
        happened three times, and left the guide's own count three
        short of the library it describes.

        Sorting is still the guide's judgement and is not asserted
        here; only that a judgement was made at all.
        """
        script = ('const { QUESTIONS } = await import('
                  '"./bga/viewer/questions.js");'
                  'console.log(JSON.stringify(QUESTIONS.map((q) => q.id)));')
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=60)
        assert done.returncode == 0, done.stderr
        served = set(json.loads(done.stdout))
        sorted_ = NEEDS_PERFETTO | ANSWERED_BY_THE_PAGE
        assert not served - sorted_, (
            f"the library serves {sorted(served - sorted_)} and the guide's "
            f"two tables sort neither into 'needs Perfetto' nor into 'the "
            f"page answers it' - a reader of the guide cannot tell the "
            f"question exists")
        assert not sorted_ - served, (
            f"the guide sorts {sorted(sorted_ - served)}, which the library "
            f"no longer serves")

    def test_the_count_in_the_prose_is_the_count_in_the_tables(self):
        """`UX-326`: the tool's own sentences are contracts, and a
        number written in words is one. "thirteen questions" stayed in
        this guide across three additions."""
        words = {13: "thirteen", 14: "fourteen", 15: "fifteen",
                 16: "sixteen", 17: "seventeen", 18: "eighteen"}
        total = len(NEEDS_PERFETTO | ANSWERED_BY_THE_PAGE)
        assert total in words, (
            f"{total} questions, and this clause has no word for it - add "
            f"one rather than letting the prose go unchecked")
        guide = GUIDE.read_text(encoding="utf-8")
        assert f"serves {words[total]} questions" in guide, (
            f"the guide's prose does not say it serves {words[total]} "
            f"questions, and its two tables sort {total}")


class TestTheGuideAndTheRolesAgree:

    def test_the_guide_names_every_role_the_model_has(self):
        guide = GUIDE.read_text(encoding="utf-8")
        roles = (REPO / "docs/design/roles.md").read_text(encoding="utf-8")
        known = set(re.findall(r"^\| (R\d) \|", roles, re.M))
        assert known, "no roles parsed out of roles.md"
        missing = sorted(known - set(re.findall(r"\*\*(R\d)\*\*", guide)))
        assert not missing, (
            f"the guide's by-role table does not mention {missing}. A role "
            "left out reads as 'not considered' rather than 'no'.")

    def test_it_says_the_trace_cannot_serve_the_gap_roles(self):
        """The finding the next brainstorm is meant to pick up."""
        guide = GUIDE.read_text(encoding="utf-8")
        assert "R1 and R2 only" in guide, (
            "the guide no longer states which roles the Perfetto escape "
            "hatch actually serves, which is the whole of its gap-analysis "
            "value")


class TestTheDegradationLadderIsTheCode:
    """`UX-548`: the guide said the timeline was refused above the track
    ceiling for a round after `UX-530` made it degrade to `--planes 1`
    first. The ladder is read off the code here, not restated."""

    @staticmethod
    def _flat():
        return " ".join(GUIDE.read_text(encoding="utf-8").split())

    def test_the_guide_names_every_narrowing_the_export_tries(self):
        steps = [narrowing for _, narrowing in _degradation_steps()
                 if narrowing]
        assert steps, "no narrowing step in the ladder at all"
        flat = self._flat()
        missing = [step for step in steps if step not in flat]
        assert not missing, (
            f"the ladder narrows with {missing}, and the guide does not say "
            f"so. A step the export takes and no document names is what "
            f"this clause exists for")

    def test_the_count_of_steps_is_the_count_in_the_prose(self):
        words = {2: "two", 3: "three", 4: "four", 5: "five"}
        steps = len(_degradation_steps())
        assert steps in words, (
            f"{steps} steps, and this clause has no word for it - add one "
            f"rather than letting the prose go unchecked")
        assert f"it has {words[steps]} steps" in self._flat(), (
            f"the guide does not say the ladder has {words[steps]} steps, "
            f"and `_degradation_steps` returns {steps}")
