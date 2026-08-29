"""UX-382: the element entity has two shapes, and one key joins them.

`analyze/v4` carries the element entity twice. Six maps keyed by uid
under `elements.*`, and a wide row per element in `element_join`.
Measured on `examples/06`'s capture:

```text
  elements.<map>   ( 6): blast_radius, criticality_probability,
                         downstream_count, element_durations, slack,
                         unweighted_depth
  element_join row (18): aggregating_dependencies, blast_radius,
                         cores_busy, cpu_coverage, critical_path_share,
                         declared, dominant_binary, native_findings,
                         on_critical_path, peak_rss_bytes,
                         potential_saving_us, recommendations,
                         redundancy_count, requested_jobs, saving_share,
                         serial_binary, unused_dependencies,
                         worst_redundancy
  in both          ( 1): blast_radius
```

**Neither shape is wrong.** The maps declare their value type once
under `additionalProperties` (`UX-343`), which is what lets one schema
describe a population of any size, and they are on every capture. The
join rows exist only where Plane 2 supplied a report - the schema's own
sentence, "there is no join with one plane". That *is* the placement
rule; it was simply written nowhere a contributor would meet it, so
every new view began by discovering where its columns live.

**What the reader actually got.** `elementFactsFor` returned the
`SOURCES` record when the report's ranking had reached an element, and
built from the column maps only when it had not - so no element ever
had both. Measured before this landed:

```text
run                    elements  ranked  a ranked record  an unranked one
macro_micro (11)             11      11        12 fields         (all ranked)
synthetic  (1,202)        1,202      26         1 field            10 fields
```

The report's own top-26 elements were the ones the page knew *least*
about, and on both runs **zero** records could answer "at depth 3, on
the critical path, and peaked above a gigabyte" - the question the item
was filed with, needing `unweighted_depth` from one shape and
`on_critical_path` and `peak_rss_bytes` from the other.

**Two denormalisations, and the filing found one.** `blast_radius` is
the one *name* in both shapes, and it does not mean the same thing in
each: `elements.blast_radius[uid]` is a record and
`element_join[].blast_radius` is an int - that record's own
`downstream_count`, which `elements.downstream_count[uid]` publishes a
third time.

The second is invisible to a count of shared names, because it is the
same fact under two of them: `element_join[].on_critical_path` is
`elements.criticality_probability[uid].observed_critical`, equal on
every element of every capture measured here. Counting attributes that
appear in both shapes finds one; asking which *facts* do finds two.

Both are kept - the join table sorts on them - and both are now
declared, held equal to their source, and taken from the map in the
resolved record.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga import schemas

REPO = pathlib.Path(__file__).resolve().parents[2]
SMALL = REPO / "tests/fixtures/macro_micro/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# The item's own question - "at depth 3, on the critical path, and
# peaked above a gigabyte" - as the fields a resolved record carries.
# The critical-path fact is `observed_critical`, the *map's* name for
# it: `element_join[].on_critical_path` is the same boolean under
# another name, and the placement rule says the resolved record takes
# the map's.
SPANNING = ("unweighted_depth", "observed_critical", "peak_rss_bytes")


def _analyze(run):
    done = subprocess.run(
        ["python", "-m", "bga.cli", "analyze", str(run), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def small():
    return _analyze(SMALL)


_PROBE = r"""
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(%(payload)s, "utf8"));
const views = await import("%(views)s");
const uids = views.elementUids(payload);
const ranked = new Set(views.elementFacts(payload).keys());
const fieldsOf = (uid) =>
  new Set(views.elementFactsFor(payload, uid).rows.map((r) => r.field));
const wanted = %(wanted)s;
let answerable = 0;
let measured = 0;
const labelClashes = [];
for (const uid of uids) {
  const record = views.elementFactsFor(payload, uid);
  const fields = new Set(record.rows.map((r) => r.field));
  if (fields.has("peak_rss_bytes")) measured += 1;
  if (wanted.every((w) => fields.has(w))) answerable += 1;
  const seen = new Map();
  for (const row of record.rows) {
    const before = seen.get(row.label);
    if (before !== undefined && before !== row.kind) {
      labelClashes.push([uid, row.label, before, row.kind]);
    }
    seen.set(row.label, row.kind);
  }
}
const sampleRanked = uids.find((u) => ranked.has(u)) ?? null;
const sampleUnranked = uids.find((u) => !ranked.has(u)) ?? null;
console.log(JSON.stringify({
  elements: uids.length,
  ranked: ranked.size,
  answerable,
  measured,
  label_clashes: labelClashes.slice(0, 5),
  ranked_fields: sampleRanked ? [...fieldsOf(sampleRanked)].sort() : null,
  unranked_fields: sampleUnranked ? [...fieldsOf(sampleUnranked)].sort() : null,
  duplicate_fields: uids.some((u) => {
    const rows = views.elementFactsFor(payload, u).rows.map((r) => r.field);
    return new Set(rows).size !== rows.length;
  }),
}));
"""


def _probe(payload):
    import tempfile
    scratch = tempfile.mkdtemp()
    try:
        doc = pathlib.Path(scratch, "payload.json")
        doc.write_text(json.dumps(payload), encoding="utf-8")
        script = _PROBE % {
            "views": (REPO / "tests/viewer.mjs").as_uri(),
            "payload": json.dumps(str(doc)),
            "wanted": json.dumps(list(SPANNING))}
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=300,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class TestTheSchemaDeclaresTheKey:
    """`UX-216` made every element one object for the *reader*. This
    makes it one object for the *schema*: the two shapes are stated to
    be keyed by the same identifier rather than conventionally so."""

    def test_the_key_is_named_once(self):
        assert schemas.ELEMENT_KEY == "element", (
            "the element entity's key is not declared, so `element_join`'s "
            "`element` and the `elements.*` map keys are the same "
            "identifier only by convention")

    def test_the_join_requires_it(self):
        node = schemas._ANALYZE_HINTS["element_join"]
        assert schemas.ELEMENT_KEY in node["items"]["required"], (
            "the join's rows do not require the key the entity is joined on")

    def test_the_column_maps_are_named_as_the_other_shape(self):
        """`ELEMENT_KEYED` is the list of maps carrying this entity. A
        map added to `elements` and not to it is a shape the page and
        every guard here would silently not know about."""
        assert set(schemas.ELEMENT_KEYED) == {
            "element_durations", "slack", "downstream_count",
            "unweighted_depth", "blast_radius", "criticality_probability"}

    def test_the_placement_rule_is_written_where_it_is_met(self):
        """A rule in a task file is a rule nobody reads. It goes beside
        the two declarations it governs."""
        source = (REPO / "bga/schemas.py").read_text(encoding="utf-8")
        assert "ELEMENT_PLACEMENT_RULE" in source
        rule = schemas.ELEMENT_PLACEMENT_RULE
        assert "elements" in rule and "element_join" in rule, rule
        assert "Plane 2" in rule, (
            "the rule does not say what decides the split - which is "
            "whether the attribute needs Plane 2 to exist")


class TestTheKeyIsOneIdentifier:
    def test_every_join_row_names_an_element_the_maps_know(self, small):
        population = set(small["elements"]["element_durations"])
        unknown = [row[schemas.ELEMENT_KEY] for row in small["element_join"]
                   if row[schemas.ELEMENT_KEY] not in population]
        assert unknown == [], (
            f"join rows keyed on elements no column map carries: {unknown}")

    def test_every_map_is_keyed_on_the_same_population(self, small):
        population = set(small["elements"]["element_durations"])
        for name in schemas.ELEMENT_KEYED:
            held = small["elements"].get(name) or {}
            assert set(held) <= population, (
                f"`elements.{name}` is keyed on elements outside the "
                f"population `element_durations` declares")


class TestTheDenormalisedColumns:
    """The two Plane 1 facts the join carries a second copy of. Kept
    because the join table sorts on them; declared so the resolved
    record can take the map's rather than render one fact twice."""

    def test_it_equals_the_map_it_was_copied_from(self, small):
        source = small["elements"]["blast_radius"]
        disagree = [
            (row[schemas.ELEMENT_KEY], row.get("blast_radius"),
             (source.get(row[schemas.ELEMENT_KEY]) or {}).get(
                 "downstream_count"))
            for row in small["element_join"]
            if row.get("blast_radius")
            != (source.get(row[schemas.ELEMENT_KEY]) or {}).get(
                "downstream_count")]
        assert disagree == [], (
            f"the join's `blast_radius` is not the map's "
            f"`downstream_count`: {disagree[:5]}")

    def test_and_the_third_publication_agrees_too(self, small):
        source = small["elements"]["downstream_count"]
        disagree = [row[schemas.ELEMENT_KEY] for row in small["element_join"]
                    if row.get("blast_radius")
                    != source.get(row[schemas.ELEMENT_KEY])]
        assert disagree == [], (
            f"`elements.downstream_count` publishes a third value for the "
            f"same fact: {disagree[:5]}")

    def test_the_second_one_is_the_same_boolean(self, small):
        """The one a count of shared *names* cannot see:
        `on_critical_path` and `observed_critical` are one fact."""
        source = small["elements"]["criticality_probability"]
        disagree = [
            (row[schemas.ELEMENT_KEY], row.get("on_critical_path"),
             (source.get(row[schemas.ELEMENT_KEY]) or {}).get(
                 "observed_critical"))
            for row in small["element_join"]
            if row.get("on_critical_path")
            != (source.get(row[schemas.ELEMENT_KEY]) or {}).get(
                "observed_critical")]
        assert disagree == [], (
            f"the join's `on_critical_path` is not the map's "
            f"`observed_critical`: {disagree[:5]}")

    def test_the_schema_says_which_value_each_one_is(self):
        node = schemas._ANALYZE_HINTS["element_join"]
        fields = node["items"]["properties"]
        assert "downstream_count" in fields["blast_radius"]["description"], (
            "the join's `blast_radius` is an int where the map's is a "
            "record, and nothing says the two are related")
        assert "observed_critical" in (
            fields["on_critical_path"].get("description") or ""), (
            "the join's `on_critical_path` is the map's "
            "`observed_critical` and nothing says so")

    def test_the_rule_names_both_of_them(self):
        rule = schemas.ELEMENT_PLACEMENT_RULE
        for field in ("blast_radius", "on_critical_path"):
            assert field in rule, (
                f"the placement rule does not name `{field}` as one of the "
                f"denormalisations it permits")


@needs_node
class TestOneResolvedRecord:
    """The Required Fix's third bullet: one resolved element record,
    built once, is what a new view asks for."""

    def test_a_record_spans_both_shapes(self, small):
        """Every element Plane 2 measured, not every element: `all.bst`
        and `toolchain.bst` carry no `peak_rss_bytes` because no
        sandbox process was billed to them, which is an absence rather
        than a gap (`UX-308`'s rule). Before this landed the count was
        zero on both runs."""
        probe = _probe(small)
        assert probe["measured"] > 0, "no element has a Plane 2 measurement"
        assert probe["answerable"] == probe["measured"], (
            f"{probe['answerable']} of {probe['measured']} measured records "
            f"can answer a question spanning both shapes "
            f"({', '.join(SPANNING)})")

    def test_the_ranked_and_the_unranked_get_the_same_shape(self, small):
        """The defect measured: a ranked element got the `SOURCES` rows
        and none of the column maps, so the report's own top elements
        were the ones the page knew least about."""
        probe = _probe(small)
        for field in ("unweighted_depth", "slack"):
            assert field in (probe["ranked_fields"] or []), (
                f"a ranked element's record has no `{field}` - the column "
                f"maps every capture carries")

    def test_no_attribute_lands_twice_in_one_record(self, small):
        probe = _probe(small)
        assert probe["duplicate_fields"] is False, (
            "one field reaches the resolved record from both shapes")

    def test_no_label_carries_two_quantities(self, small):
        """`blast_radius` again, seen from the page: the map's is a
        duration and the join's is a count, both labelled "Blast
        radius". Two rows, one name, two units."""
        probe = _probe(small)
        assert probe["label_clashes"] == [], probe["label_clashes"]


class TestTheBytesDoNotGrow:
    """`UX-288`'s property, which this must not spend: the fix is a
    declared relationship and a viewer merge, not a wider payload."""

    def test_the_payload_still_publishes_each_population_once(self, small):
        for name in schemas.ELEMENT_KEYED:
            assert name in small["elements"], (
                f"`{name}` left the `elements` grouping - which would "
                f"publish one population as several sections")
        assert "elements" not in {
            key for key in small if key in schemas.ELEMENT_KEYED}, (
            "a column map was lifted to the top level")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
