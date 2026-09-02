"""UX-529: the export's data half was bounded by nothing but 8 MiB.

`PAGE_BUDGET_B` bounds the hand-written half of an exported report and
`EXPORT_BUDGET_B` only *reports*, so between the two the embedded
payload grew with the element population and nothing read the number.
Measured before the fix, `bga gen-synthetic --seed 1` and the same with
`--layers 20 --width 200`:

```text
                  @1,202       @4,002      per element
data half        629,385 B  2,042,989 B      ~515 B
export total   1,016,963 B  2,430,567 B
```

`EXPORT_BUDGET_B` is reached at about 16,000 elements with nothing in
between - and a report of a project that size is exactly the one worth
attaching.

**Two claims, one file.** The budget per size class is the bound; the
compact form is what pays for it. `DATA_COMPACT_MIN_B` is the switch
between them, and `test_a_small_export_is_still_readable_json` is the
clause that keeps it a switch rather than "always compact" - the two
committed fixtures export the same readable blocks they always did,
which is what every other guard in the export family is reading.
"""
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages                                         # noqa: E402
from tools import bga_view as view                              # noqa: E402

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: `UX-529`: the data half's bound, per size class, largest class last.
#: Each row is `(elements at most, data bytes at most)`, and the class
#: boundaries are `test_the_page_has_a_volume_budget.py`'s - the page a
#: reader downloads has one notion of how big a run is, not two.
#:
#: Measured on the merge, after the compact form:
#:
#: ```text
#:                elements     data      budget    of it
#: golden                4   29,700     100,000     30%
#: macro_micro          11   79,820     100,000     80%
#: scale             1,202   70,222     240,000     29%
#: xl                4,002  194,536     240,000     81%
#: ```
#:
#: The large class is *smaller* than the small class at its bottom and
#: bigger at its top, which reads wrong and is not: `scale` compacts and
#: `macro_micro` does not, and 70 KB of gzip is 629 KB of JSON. Each
#: class is set at ~1.25x the largest run in it, which is the headroom
#: an ordinary round's new key fits in and a new population does not.
DATA_BUDGETS = (
    (50, 100_000),
    (4_100, 240_000),
)

#: The four runs, and what builds each. The two generated members are
#: the whole point - the committed fixtures are 4 and 11 elements, and
#: the defect this file is about is invisible below a thousand.
_GENERATED = {"scale": pages.scale_run, "xl": pages.xl_run}
LABELS = sorted(pages.FIXTURES) + sorted(_GENERATED)


def budget_for(elements):
    """The row `elements` is measured against.

    Not clamped, for `test_the_page_has_a_volume_budget.py`'s reason: a
    run past the last class has no decided bound, and inheriting the
    largest one silently is this item one size up.
    """
    for row in DATA_BUDGETS:
        if elements <= row[0]:
            return row
    raise AssertionError(
        f"{elements:,} elements is past every class in DATA_BUDGETS; "
        f"decide a bound for that size rather than inheriting one")


def _halves(path):
    """`(page, schemas, data, blocks)` of an exported report.

    The same split every other size guard uses - `application/json`
    **and** `application/octet-stream`, because `UX-529` made the data
    half arrive in the second of those and a regex that named only the
    first would have counted a compacted payload as page.
    """
    html = pathlib.Path(path).read_text(encoding="utf-8")
    page = re.sub(r'<script[^>]*type="application/(json|octet-stream)"'
                  r'[^>]*>.*?</script>', "", html, flags=re.S)
    blocks = dict(re.findall(
        r'<script[^>]*type="application/(?:json|octet-stream)"[^>]*'
        r'id="([^"]+)"[^>]*>(.*?)</script>', html, re.S))
    schemas = len(blocks.get("bga-schemas", ""))
    data = sum(len(body) for name, body in blocks.items()
               if name != "bga-schemas")
    return len(page), schemas, data, blocks


def _document(blocks, name):
    """The `name` document an export carries, either form."""
    plain = blocks.get(f"bga-{name}")
    if plain is not None:
        return json.loads(plain.replace("<\\/", "</"))
    import base64

    return json.loads(gzip.decompress(
        base64.b64decode(blocks[f"bga-{name}-gz"])).decode("utf-8"))


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    """`{label: (path, elements)}` for the four runs, exported once."""
    made = {}
    for label, fixture in pages.FIXTURES.items():
        into = tmp_path_factory.mktemp(f"data-{label}")
        made[label] = pages.export_page(fixture, into, name=f"{label}.html")
    for label, build in _GENERATED.items():
        into = tmp_path_factory.mktemp(f"data-{label}")
        path = into / f"{label}.html"
        view.export(str(build(into)), str(path))
        made[label] = path
    return {label: (path,
                    len(_document(_halves(path)[3], "report")
                        ["elements"]["element_durations"]))
            for label, path in made.items()}


@pytest.mark.large
class TestTheDataHalfIsBounded:

    @pytest.mark.parametrize("label", LABELS)
    def test_it_is_inside_its_class_budget(self, exports, label):
        path, elements = exports[label]
        klass, bound = budget_for(elements)
        _page, _schemas, data, _blocks = _halves(path)
        assert data <= bound, (
            f"{label} embeds {data:,} B of this run's documents at "
            f"{elements:,} elements, over the {bound:,} B budget for runs "
            f"up to {klass:,}. The data half is what an attachment "
            f"weighs; move the bound on a measurement or compact it")

    @pytest.mark.parametrize("row", DATA_BUDGETS, ids=lambda r: str(r[0]))
    def test_no_class_is_met_from_far_below(self, exports, row):
        """The clause that keeps a budget a measurement.

        A bound nothing in its class comes within a factor of two of is
        governing nothing, and would go on passing through the growth it
        exists to catch.
        """
        klass, bound = row
        inside = {label: _halves(path)[2]
                  for label, (path, count) in exports.items()
                  if budget_for(count)[0] == klass}
        assert inside, f"no run falls in the class bounded at {klass:,}"
        largest = max(inside.values())
        assert largest * 2 >= bound, (
            f"the largest data half in the class bounded at {klass:,} "
            f"elements is {largest:,} B against a {bound:,} B budget - "
            f"the bound is met from below and governs nothing")

    def test_every_class_has_a_run_behind_it(self, exports):
        covered = {budget_for(count)[0] for _path, count in exports.values()}
        missing = [row[0] for row in DATA_BUDGETS if row[0] not in covered]
        assert missing == [], (
            f"no run in the population falls in the class(es) bounded at "
            f"{missing} - those bounds govern nothing")


@pytest.mark.large
class TestTheCompactFormIsASwitch:

    @pytest.mark.parametrize("label", sorted(pages.FIXTURES))
    def test_a_small_export_is_still_readable_json(self, exports, label):
        """`DATA_COMPACT_MIN_B` is a threshold, not a mode.

        Every other guard in the export family reads `bga-report` as
        text, and a person opening a small report in an editor reads it
        the same way. Compacting unconditionally would pass every
        clause above and take that away.
        """
        _page, _schemas, _data, blocks = _halves(exports[label][0])
        assert "bga-report" in blocks, sorted(blocks)
        assert "bga-report-gz" not in blocks, sorted(blocks)

    @pytest.mark.parametrize("label", sorted(_GENERATED))
    def test_a_large_export_carries_the_compact_form(self, exports, label):
        _page, _schemas, _data, blocks = _halves(exports[label][0])
        assert "bga-report-gz" in blocks, sorted(blocks)
        assert "bga-report" not in blocks, (
            "the export carries the payload twice, which is the defect "
            "one worse")

    @pytest.mark.parametrize("label", sorted(_GENERATED))
    def test_the_compact_form_is_the_same_document(self, exports, label):
        """Not smaller *and* different. Compared against what `bga view`
        serves for the same run, so the two delivery modes cannot
        disagree - `UX-195`'s property, at the new seam."""
        path, _elements = exports[label]
        _page, _schemas, _data, blocks = _halves(path)
        run = path.parent / label
        assert _document(blocks, "report") == \
            view.payloads(str(run))["report.json"]


_PROBE = """
// `UX-529`: the page's own loader, against a real compacted export.
// Not a re-implementation of the inflate - that would pass whatever
// `app.js` does - and `fetch` throws, so a payload the loader cannot
// read inline is a failure here rather than a silent network call.
const shim = await import(process.env.BGA_DOM_SHIM);
const html = (await import("node:fs")).readFileSync(process.env.BGA_EXPORT,
                                                    "utf-8");
const nodes = {};
for (const m of html.matchAll(
    /<script type="application\\/(?:json|octet-stream)" id="(bga-[a-z-]+)">([\\s\\S]*?)<\\/script>/g)) {
  const node = shim.makeNode("script");
  node.textContent = m[2].replace(/<\\\\\\//g, "</");
  nodes[m[1]] = node;
}
shim.installDocument({ getElementById: (id) => nodes[id] ?? null });
globalThis.fetch = () => { throw new Error("the export fetched something"); };
const app = await import("./tests/viewer.mjs");

const report = await app.load("report");
const run = await app.load("run");
console.log = (...a) => process.stdout.write(a.join(" ") + "\\n");
console.log(JSON.stringify({
  ids: Object.keys(nodes).sort(),
  schema: report?.schema ?? null,
  elements: Object.keys(report?.elements?.element_durations ?? {}).length,
  offered: app.offered(run, "report"),
  inlined: app.inlined("report") !== null,
  absent: await app.inflated("compare"),
}));
"""


@pytest.fixture(scope="module")
def probed(exports):
    path, elements = exports["scale"]
    result = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env=dict(os.environ, BGA_EXPORT=str(path),
                 BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")))
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout), elements


@needs_node
@pytest.mark.large
class TestThePageReadsIt:
    """Read by `app.js`'s own `load`, which is the half that would
    otherwise ship unexercised: a writer with no reader produces an
    export that is small, valid and blank."""

    def test_the_loader_inflates_it_without_the_network(self, probed):
        seen, elements = probed
        assert "bga-report-gz" in seen["ids"], seen["ids"]
        assert seen["schema"] is not None, "the loader returned no document"
        assert seen["elements"] == elements, (seen["elements"], elements)

    def test_the_inline_reader_is_not_what_answered(self, probed):
        """The clause that says the compact path is the one on the wire.
        `inlined` is synchronous and reads `bga-report`, which a
        compacted export does not carry - so a page that answered this
        run from `inlined` would be reading a block that is not there."""
        seen, _elements = probed
        assert seen["inlined"] is False

    def test_the_manifest_answer_counts_the_compact_block(self, probed):
        """`offered` decides whether to ask for an optional payload at
        all (`UX-334`). Reading only `bga-report` would call a
        compacted payload absent and put three fetches back on a
        `file://` page."""
        seen, _elements = probed
        assert seen["offered"] is True

    def test_an_absent_compact_block_is_null_not_a_throw(self, probed):
        """`compare` is optional and this run has none. `inflated` is
        asked before the fetch, so a throw there would be a boot that
        never reaches the section."""
        seen, _elements = probed
        assert seen["absent"] is None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
