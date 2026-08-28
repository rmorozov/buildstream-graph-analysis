"""UX-342: an exported page carries the schemas its documents declare.

An export embeds its payloads and can fetch nothing — it opens from a
download folder or an email attachment. It used to embed **every**
schema the tool publishes, and the measurement is what filed this:

```text                          golden        macro_micro
page                          330,517 B      369,959 B
  bga-report                   17,891 B       57,246 B
  bga-run                         378 B          465 B
  bga-schemas                  83,669 B       83,669 B   <- identical
  module blob                 203,073 B      203,073 B
```

On the golden export the schemas were **4.7x the data**, and identical
between two different runs because they were the published set rather
than this page's. The page resolves a schema in exactly two places —
`schemas[payload.schema]` and `schemas[store?.schema]` — so
`blast/v2`, `compare/v2`, `whatif/v1`, `sweep/v1`, `correlate/v2` and
`store-aggregate/v1` were 35,185 B nothing could reach. `blast` and
`whatif` are answers the *server* computes on demand, and in an export
there is no server.

**Why these clauses are shaped this way.** The set is asserted to equal
what the embedded documents *declare*, derived on both sides. A clause
naming `analyze/v3` would pass with the set hardcoded, and hardcoding is
the failure this replaces: a page that later embeds a `correlate/v2`
document has to get that schema with no edit to the exporter.
"""
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
MACRO_MICRO = REPO / "tests/fixtures/macro_micro/run"

BLOCK = r'<script type="application/json" id="bga-{}">(.*?)</script>'


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    """Both committed fixtures, exported once."""
    from tools.bga_view import export

    out = {}
    directory = tmp_path_factory.mktemp("exports")
    for label, run in (("golden", GOLDEN), ("macro_micro", MACRO_MICRO)):
        path = directory / f"{label}.html"
        result = export(str(run), str(path))
        html = path.read_text(encoding="utf-8")
        blocks = {}
        for name in re.findall(r'id="bga-([\w-]+)"', html):
            found = re.search(BLOCK.format(re.escape(name)), html, re.S)
            if found:
                blocks[name] = json.loads(found.group(1))
        out[label] = {"result": result, "blocks": blocks, "html": html}
    return out


def _declared_by(blocks, known):
    """Every schema id the embedded documents name, at any depth."""
    found = set()

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("schema"), str) and value["schema"] in known:
                found.add(value["schema"])
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk({name: body for name, body in blocks.items() if name != "schemas"})
    return found


@pytest.mark.parametrize("label", ["golden", "macro_micro"])
class TestItEmbedsWhatItsDocumentsDeclare:

    def test_the_embedded_set_is_the_declared_set(self, exports, label):
        """Derived on both sides, so a hardcoded list reddens."""
        from bga import schemas

        blocks = exports[label]["blocks"]
        embedded = set(blocks["schemas"])
        declared = _declared_by(blocks, set(schemas.names()))
        assert embedded == declared, (
            f"{label}: the export embeds {sorted(embedded)} and its "
            f"documents declare {sorted(declared)}. Embedding more is dead "
            f"weight the page cannot reach; embedding less is a section "
            f"that renders without its units")

    def test_the_page_can_resolve_the_schema_its_report_declares(
            self, exports, label):
        """The clause the trim must not break: `render(payload,
        schemas[payload.schema], …)` is the first thing `boot()` does,
        and an id with no schema behind it renders the whole report
        generically."""
        blocks = exports[label]["blocks"]
        declared = blocks["report"]["schema"]
        assert declared in blocks["schemas"], (
            f"{label}: the report declares {declared!r} and the page does "
            f"not carry it")

    def test_it_stops_carrying_the_ones_nothing_declares(self, exports, label):
        """The subtraction actually happened.

        Without this, the clause above is satisfied by embedding
        everything — which is the state UX-342 was filed for.
        """
        from bga import schemas

        left_out = set(schemas.names()) - set(exports[label]["blocks"]["schemas"])
        assert left_out, (
            f"{label}: the export carries every published schema again. "
            f"The page resolves `payload.schema` and `store.schema` and "
            f"nothing else, so the rest is bytes in an attachment nobody "
            f"can use")
        assert {"blast/v2", "whatif/v1"} <= left_out, (
            f"{label}: `blast/v2` and `whatif/v1` are answers the *server* "
            f"computes on demand. An export has no server, so carrying "
            f"their schemas is carrying a contract for a document this "
            f"file can never hold. Still embedded: "
            f"{sorted(set(schemas.names()) - left_out)}")


class TestTheServedEndpointIsUnchanged:

    def test_schemas_json_still_answers_for_every_published_id(self):
        """`schemas.json` is a published API. The export is a page with
        no network; the server is not, and `curl .../schemas.json` has
        to keep answering the question a reader asks of it."""
        from bga import schemas
        from tools.bga_view import schemas_payload

        assert set(schemas_payload()) == set(schemas.names()), (
            "the served schemas endpoint lost ids along with the export")

    def test_the_export_and_the_server_read_the_same_function(self):
        """One function, two answers, told apart by its argument.

        Two functions would drift: the served side would keep gaining
        ids the export path never learned to drop, which is how the
        export came to carry all eight in the first place.
        """
        import inspect

        from tools.bga_view import schemas_payload

        signature = inspect.signature(schemas_payload)
        assert list(signature.parameters) == ["documents"], (
            f"schemas_payload takes {list(signature.parameters)}: the "
            f"export's set and the server's set are no longer the same "
            f"function answering differently")
        assert signature.parameters["documents"].default is None, (
            "the server's answer must be the default, so a caller that "
            "says nothing gets everything")


class TestADeclarationDeeperInADocumentStillCounts:
    """`UX-253`'s aggregate names the contract sets it mixes, and a
    store document can carry another document's id inside it. Reading
    only the top level would drop the schema for a table the page draws.
    """

    def test_a_nested_schema_id_is_found(self):
        from tools.bga_view import _declared_schemas

        documents = {"report": {"schema": "analyze/v3",
                                "nested": [{"deep": {"schema": "store/v1"}}]}}
        found = _declared_schemas(documents, {"analyze/v3", "store/v1"})
        assert found == {"analyze/v3", "store/v1"}, found

    def test_an_id_this_build_does_not_publish_is_dropped_not_raised(self):
        """A payload written by a newer build names a contract this one
        has never heard of. Rendering it generically beats refusing to
        export it."""
        from tools.bga_view import _declared_schemas

        found = _declared_schemas({"report": {"schema": "analyze/v9"}},
                                  {"analyze/v3"})
        assert found == set(), found
