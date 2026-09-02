"""UX-429: a command drawn as a list of its words does not run.

The page's "What should I run next?" table has a `Run` column holding
`next_steps[].argv`. Measured through the page's own resolution, on
`macro_micro`, before this item:

```text
classify without the hint: inline code list
cell tag: span class: ""
cell text: "bga, blast, core.bst, tests/fixtures/macro_micro/run"
```

Not monospace, no `code` element, and a comma between every word. The
same field renders correctly in `decision.js` and `views.js`, which
each hand-joined it with a space - so one payload field read as a
runnable command in two places and as prose in the third.

**The mapping was being followed correctly.** `["bga", "blast", …]` is
a *short scalar array*, whose §1 control is the inline `code` list, and
`["cmake", "ninja"]` is the same measured shape and genuinely is a
list. Only the schema can tell them apart, so §1 gained a row and §1a a
hint: `bga:command`, declared on `argv`, read by `classify`. Declared,
never guessed - the rule `bga:series` and `bga:distribution` already
follow, and the reason this guard checks the *hint* rather than
sniffing for a verb.

After:

```text
hint on argv: "shell"
classify says: command line + copy
cell tag: code class: next-command
cell text: "bga blast core.bst tests/fixtures/macro_micro/run"
data-argv: "bga blast core.bst tests/fixtures/macro_micro/run"
```

`controls.js:commandLine` is the one control all three sites call, which
is what stops the third from drifting again.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}

_PROBE = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const v = await import(process.env.BGA_VIEWER);
const fs = await import("node:fs");
const payload = JSON.parse(fs.readFileSync(process.env.BGA_PAYLOAD, "utf8"));
const schemas = JSON.parse(fs.readFileSync(process.env.BGA_SCHEMAS, "utf8"));

const steps = schemas[payload.schema].properties.next_steps;
const argvNode = steps.items.properties.argv;
const out = { declared: v.hintsOf(argvNode)["bga:command"] ?? null, sites: {} };

// Every argv this run publishes, as the reader would have to paste it.
out.commands = (payload.next_steps ?? [])
  .filter((step) => Array.isArray(step.argv))
  .map((step) => ({ joined: step.argv.join(" "), listed: step.argv.join(", ") }));

const first = (payload.next_steps ?? []).find((s) => Array.isArray(s.argv));

function look(el) {
  return el ? { tag: el.tagName, cls: el.className ?? "",
                text: el.textContent ?? "",
                argv: el.getAttribute?.("data-argv") ?? null } : null;
}

// 1. the table path, through `renderStructured`
out.sites.table = look(v.renderStructured(
  "argv", first.argv, v.hintsOf(argvNode), argvNode, 0, "next_steps.argv"));

// 2. the shared control itself, with and without a clipboard
const [line, button] = v.commandLine(first.argv, { copy: () => {} });
out.sites.control = look(line);

// 3. and the two sections that draw one, read out of their real DOM
//    rather than out of their source - a scan of the text cannot tell
//    a `copy-step` in code from one in a comment, and this file's
//    first cut of that clause proved it by matching a comment.
function find(root, cls) {
  if (!root) return null;
  if ((root.className ?? "").split(" ").includes(cls)) return root;
  for (const kid of root.childNodes ?? root.children ?? []) {
    const hit = find(kid, cls);
    if (hit) return hit;
  }
  return null;
}
const make = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (name === "class") el.className = value; else el.setAttribute(name, value);
  }
  for (const kid of kids) el.append(kid);
  return el;
};
try {
  const blast = v.renderBlastOffline(payload, () => {}, make);
  out.sites.blast = look(find(blast, "next-command"));
  out.sites.blastCopy = Boolean(find(blast, "copy-step"));
} catch (error) { out.sites.blast = { error: String(error) }; }
try {
  const panel = v.renderDecision(payload, null, () => {});
  out.sites.decision = look(find(panel, "next-command"));
  out.sites.decisionCopy = Boolean(find(panel, "copy-step"));
} catch (error) { out.sites.decision = { error: String(error) }; }
out.sites.button = button
  ? { tag: button.tagName, cls: button.className,
      copies: button.getAttribute?.("data-copies") }
  : null;
out.sites.exported = v.commandLine(first.argv).length;

console.log(JSON.stringify(out));
"""


def _probe(label):
    from bga import schemas
    from tools.bga_view import payloads

    scratch = pathlib.Path(tempfile.mkdtemp())
    (scratch / "p.json").write_text(
        json.dumps(payloads(str(FIXTURES[label]))["report.json"]))
    (scratch / "s.json").write_text(
        json.dumps({name: schemas.schema(name) for name in schemas.names()}))
    done = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env={**os.environ,
             "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri(),
             "BGA_VIEWER": (REPO / "tests/viewer.mjs").as_uri(),
             "BGA_PAYLOAD": str(scratch / "p.json"),
             "BGA_SCHEMAS": str(scratch / "s.json")})
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


class TestTheShapeIsDeclared:

    def test_argv_carries_the_command_hint(self):
        """Declared, not guessed. A scalar array is argv because the
        schema said so - `["cmake", "ninja"]` is the same measured
        shape and is genuinely a list."""
        from bga import schemas

        argv = schemas.schema("analyze/v4")["properties"]["next_steps"][
            "items"]["properties"]["argv"]
        assert argv.get(schemas.COMMAND) == "shell", argv

    def test_the_hint_only_fires_on_a_scalar_array(self):
        """A declaration that fits nothing is a schema bug, and drawing
        a command line over an array of objects would hide it - the
        rule `UX-303` set for `bga:distribution`."""
        from bga import schemas

        for name in schemas.names():
            document = schemas.schema(name)
            for path, node in _walk(document, name):
                if not isinstance(node, dict) or schemas.COMMAND not in node:
                    continue
                assert node.get("type") == "array", (
                    f"{path} declares {schemas.COMMAND} and is not an array")


def _walk(node, path):
    if not isinstance(node, dict):
        return
    yield path, node
    for key, sub in (node.get("properties") or {}).items():
        yield from _walk(sub, f"{path}.{key}")
    if isinstance(node.get("items"), dict):
        yield from _walk(node["items"], f"{path}[]")
    if isinstance(node.get("additionalProperties"), dict):
        yield from _walk(node["additionalProperties"], path + "{}")


@needs_node
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestEverySiteDrawsTheSameCommand:

    def test_the_table_cell_is_a_monospace_command(self, label):
        """The defect, at the site that had it."""
        seen = _probe(label)
        assert seen["declared"] == "shell", seen["declared"]
        cell = seen["sites"]["table"]
        assert cell["tag"].lower() == "code", cell
        assert "next-command" in cell["cls"], cell
        assert cell["argv"] == cell["text"], cell

    def test_no_argv_is_ever_drawn_comma_separated(self, label):
        """The acceptance test's own rule. Reads the *rendered* text
        against the payload's own join, so it cannot pass by the cell
        happening to be empty."""
        seen = _probe(label)
        drawn = {seen["sites"][site]["text"]
                 for site in ("table", "control")}
        listed = {command["listed"] for command in seen["commands"]}
        assert not (drawn & listed), sorted(drawn & listed)
        joined = {command["joined"] for command in seen["commands"]}
        assert drawn <= joined, sorted(drawn - joined)

    def test_the_control_carries_the_copy_affordance(self, label):
        """§4c, where there is a clipboard to write to."""
        seen = _probe(label)
        button = seen["sites"]["button"]
        assert button is not None, seen["sites"]
        assert button["cls"] == "copy-step", button
        assert button["copies"] == "command", button

    def test_all_three_sites_draw_the_same_element(self, label):
        """"One control" as a property of the rendered page.

        Read out of the DOM each section really builds, not out of its
        source: a text scan cannot tell a `copy-step` in code from one
        in a comment, and this file's first attempt at this clause
        matched a comment in `structured.js` and failed for it.
        """
        seen = _probe(label)
        drawn = {site: seen["sites"][site]
                 for site in ("table", "control", "blast", "decision")
                 if seen["sites"].get(site)}
        assert "error" not in json.dumps(drawn), drawn
        assert len(drawn) == 4, sorted(drawn)
        shapes = {(one["tag"].lower(), one["cls"], one["argv"] == one["text"])
                  for one in drawn.values()}
        assert shapes == {("code", "next-command", True)}, (shapes, drawn)

    def test_the_two_sections_keep_their_copy_button(self, label):
        """The refactor must not have dropped what it replaced."""
        seen = _probe(label)
        assert seen["sites"]["blastCopy"] is True
        assert seen["sites"]["decisionCopy"] is True

    def test_the_export_still_gets_the_line(self, label):
        """No server, no clipboard - and the command still renders,
        because one you can select beats none at all."""
        seen = _probe(label)
        assert seen["sites"]["exported"] == 1, seen["sites"]["exported"]


class TestOneControlNotThree:
    """The drift this item is really about: three sites, one control."""

    SITES = ("bga/viewer/structured.js", "bga/viewer/decision.js",
             "bga/viewer/views.js")

    def test_every_site_calls_the_shared_control(self):
        for site in self.SITES:
            text = (REPO / site).read_text(encoding="utf-8")
            assert "commandLine(" in text, site

    def test_the_control_lives_where_every_site_can_reach_it(self):
        """`controls.js` inlines third; `questions.js`, which holds the
        query library's own copy control, inlines after `decision.js`.
        A command control living there could not be imported here
        without reordering the export."""
        order = (REPO / "tests/viewer.mjs").read_text(encoding="utf-8")
        modules = [line.split('viewer/')[1].split('"')[0]
                   for line in order.splitlines()
                   if line.startswith("export * from")]
        assert modules.index("controls.js") < modules.index("structured.js")
        assert modules.index("controls.js") < modules.index("decision.js")
        assert modules.index("controls.js") < modules.index("views.js")
