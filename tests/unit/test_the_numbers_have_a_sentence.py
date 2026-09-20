"""UX-220: a published number that needs explaining carries the sentence.

The round-24 review proposed "Why?" popovers on the headline metrics and
called them nearly free, "because the schema already carries
descriptions". It did not, exactly where it mattered: `floors`,
`capacity_verdict` and `occupancy` declared no members at all, and
`utilisation` declared three that no code path emits. The renderer was
never the missing piece (`UX-201` already renders `description`
recursively, at every depth) - the descriptions were.

So these guards are about the *schema*, not the viewer:

1. Every leaf that declares a `bga:quantity` also declares a
   description, so the next number added cannot arrive mute.
2. Every key the schema describes is one the payload actually carries -
   the failure `utilisation` was in, where three hinted names described
   a shape that never existed and every real member went unhinted.
3. The sentences have one home. `bga analyze`'s text report and
   `--help` read them from the schema rather than keeping their own.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from bga import schemas

GOLDEN = Path(__file__).parent.parent / "fixtures" / "golden" / "mixed_task_kinds"
MACRO_MICRO = Path(__file__).parent.parent / "fixtures" / "macro_micro"


def _quantity_leaves(document):
    """Every (path, node) in `document` that declares a quantity."""
    found = []

    def walk(node, path):
        if not isinstance(node, dict):
            return
        if schemas.QUANTITY in node:
            found.append((path, node))
        for key, child in (node.get("properties") or {}).items():
            walk(child, f"{path}.{key}" if path else key)
        items = node.get("items")
        if isinstance(items, dict):
            walk(items, path + "[]")

    walk(schemas.schema(document), "")
    return found


class TestEveryQuantityCarriesItsSentence:
    """Clause 4: a number that declares what it *is* also says what it means."""

    @pytest.mark.parametrize("document", schemas.names())
    def test_no_published_quantity_is_mute(self, document):
        mute = [path for path, node in _quantity_leaves(document)
                if not node.get("description")]
        assert mute == [], (
            f"{document}: these declare a quantity but no description, so the "
            f"page renders a number with nothing to say about it: {mute}")

    def test_the_guard_has_something_to_guard(self):
        """A completeness guard over an empty set passes vacuously.

        This is the count the guard above actually covers - if a
        refactor emptied the schema, that guard would still be green and
        this one would not.
        """
        total = sum(len(_quantity_leaves(name)) for name in schemas.names())
        assert total > 100, total

    @pytest.mark.parametrize("document", schemas.names())
    def test_a_sentence_is_a_sentence(self, document):
        """Not a label, not a repeated key name."""
        for path, node in _quantity_leaves(document):
            sentence = node["description"]
            leaf = path.rsplit(".", 1)[-1]
            assert sentence.strip().endswith("."), (path, sentence)
            assert len(sentence.split()) >= 4, (path, sentence)
            assert sentence.strip().rstrip(".") != leaf, (path, sentence)


class TestTheSchemaDescribesWhatIsPublished:
    """Clause 1, and the failure that motivated it.

    `utilisation` declared `peak_rss_bytes`, `cpu_pct` and `cpu_seconds` -
    three names `_compute_utilization` has never emitted. The hints were
    aimed at a shape that did not exist, so every member the object
    really carries went unhinted and undescribed.
    """

    @staticmethod
    def _analyze(run, plane2=None):
        argv = [sys.executable, "-m", "bga.cli", "analyze", str(run),
                "--format", "json", "--diagnostics"]
        argv += ["--plane2", str(plane2)] if plane2 else ["--no-plane2"]
        proc = subprocess.run(argv, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    @classmethod
    def _documents(cls):
        """Both runs, because one of them cannot publish half the schema.

        `UX-891`: the golden run carries no Plane 2 report, so a member
        computed from Plane 2 - the CPU floor's five - is absent from it
        by design and would read here as a phantom. A guard whose only
        fixture structurally excludes what it is checking for is the
        shape `CLAUDE.md` lists third, so the population is a run
        without Plane 2 and a run with one.
        """
        if not getattr(cls, "_cache", None):
            cls._cache = [
                cls._analyze(GOLDEN),
                cls._analyze(MACRO_MICRO / "run", MACRO_MICRO / "plane2.json"),
            ]
        return cls._cache

    @pytest.mark.parametrize("section", [
        "floors", "capacity_verdict", "occupancy", "utilisation"])
    def test_every_described_member_is_one_the_payload_carries(self, section):
        published = set().union(
            *(document[section] for document in self._documents()))
        declared = set(
            schemas.schema(schemas.ANALYZE)["properties"][section]
             .get("properties") or {})
        assert declared, f"{section} declares no members at all"
        phantom = sorted(declared - published)
        assert phantom == [], (
            f"analyze/v2.{section} describes {phantom}, which neither run "
            f"publishes - a sentence about a field nobody emits")

    @pytest.mark.parametrize("section", [
        "floors", "capacity_verdict", "occupancy", "utilisation"])
    def test_every_published_member_is_described(self, section):
        properties = (schemas.schema(schemas.ANALYZE)["properties"][section]
                      .get("properties") or {})
        published = set().union(
            *(document[section] for document in self._documents()))
        mute = sorted(k for k in published if not properties.get(k, {}).get("description"))
        assert mute == [], f"analyze/v2.{section}: undescribed members {mute}"


class TestTheSentencesHaveOneHome:
    """Clause 3: the report and `--help` read the schema, not their own copy."""

    def test_the_text_report_prints_the_schema_sentence(self):
        proc = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(GOLDEN)],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        sentence = schemas.description(schemas.ANALYZE, "floors.occupancy_share")
        assert sentence in proc.stdout

    def test_help_states_what_a_floor_is_from_the_schema(self):
        proc = subprocess.run(
            [sys.executable, "-m", "bga.cli", "floors", "--help"],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        # argparse re-wraps, so compare on collapsed whitespace.
        rendered = " ".join(proc.stdout.split())
        sentence = " ".join(schemas.description(schemas.ANALYZE, "floors").split())
        assert sentence in rendered

    def test_no_second_wording_of_the_occupancy_sentence(self):
        """The parenthetical this line used to carry, spelled out here so
        reintroducing it fails rather than quietly drifting."""
        source = (Path(__file__).parent.parent.parent
                  / "bga" / "report" / "text.py").read_text()
        assert "unlike Efficiency Score, this falls when independent" not in source


class TestTheAccessorRefusesToInvent:
    """A sentence that does not exist must raise, never render empty."""

    def test_an_unknown_path_raises(self):
        # The round-24 review named `floors.certified_us` as "the most
        # misreadable number this tool publishes". No such field has ever
        # been published; the certified floor is `floors.lb`.
        with pytest.raises(KeyError, match="no such path"):
            schemas.description(schemas.ANALYZE, "floors.certified_us")

    def test_a_described_path_returns_the_schema_string(self):
        node = schemas.schema(schemas.ANALYZE)["properties"]["floors"]
        assert (schemas.description(schemas.ANALYZE, "floors.lb")
                == node["properties"]["lb"]["description"])

    def test_an_array_step_walks_into_items(self):
        assert schemas.description(schemas.STORE, "snapshots[].bytes")

    def test_a_path_without_a_sentence_raises_rather_than_returning_empty(self):
        with pytest.raises(KeyError, match="carries no description"):
            schemas.description(schemas.ANALYZE, "run_id")
