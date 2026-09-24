#!/usr/bin/env python3
"""`UX-1000`: an area page names each scenario's guard.

    python tools/dev_area_pages.py --areas [NAME]        # print, never writes
    python tools/dev_area_pages.py --out DIR --link-base URL

Takes `area_page_body`/`report_areas` out of `dev_close_task.py`
(`area_pages()` stays there - `dev_scenario.py` imports it) and adds a
Guard column: every `test_*.py` a task's text names - **declared**
(the Decision's `Guard:` field, else the Acceptance Test) or else
**inferred** from the Outcome - marked present or missing under
`tests/`; an inferred guard is marked ` (inferred)`; none named reads
"no guard named". A page ends `covered N / M (declared D, inferred
I)`: N = D + I rows naming >= 1 existing file, of M listed - a row
with both counts declared. A verifier found prose the Outcome names
for other reasons (`UX-219`, `UX-826`); no regex tells that from a
real guard, so the page marks the kind instead of chasing a fourth
extraction rule.

`--areas` only prints (`UX-996`); `--out DIR --link-base URL` is the
only writer, for CI to publish to `refs/heads/records` (`UX-997`) -
`link_base` replaces the `../scenarios/` relative link, which resolves
only beside a checkout's own `docs/backlog/scenarios/`, not on a page
published alone.
"""
import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import dev_close_task as tasks

#: Where a guard is looked for - overridable so a guard can sandbox it.
TESTS_ROOT = REPO / "tests"

#: `UX-689`: a hand-written `docs/design/areas/<area>.md`, if one
#: exists, gets one derived `Mechanism:` line in the printed page.
DESIGN_AREA_PAGES = REPO / "docs/design/areas"

_GUARD_FILE = re.compile(r"\btest_\w+\.py\b")
_BACKTICKED_GUARD_FILE = re.compile(r"`(?:[\w./-]*/)?(test_\w+\.py)`")
_FIELD_LINE = re.compile(r"^([A-Z][A-Za-z]*):\s?")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_MUTATIONS_SUBSECTION = re.compile(
    r"\n#{2,3} Mutations verified red and reverted.*?(?=\n#{2,3} |\Z)", re.S)

#: Pre-`UX-497` task files (`UX-72`, `UX-81`, `UX-93`) carry no `##
#: Outcome` at all - the same close-measurement lives under these two
#: headings instead, read the same way.
_LEGACY_OUTCOME_HEADINGS = ("Fix Implemented", "Verification Log")


def existing_guard_files():
    """Every `test_*.py` basename under `tests/`, so presence is a set
    lookup rather than a stat per candidate."""
    return {p.name for p in TESTS_ROOT.rglob("test_*.py")}


def _decision_field(decision_text, name):
    """One field's continuation-joined value from a `## Decision`
    block's fenced `Name:  value` shape (each field starts a line with
    no leading space; a continuation is indented), or `''`."""
    capturing, out = False, []
    for line in decision_text.splitlines():
        match = _FIELD_LINE.match(line)
        if match:
            if capturing:
                break
            capturing = match.group(1) == name
            if capturing:
                out.append(line[match.end():])
            continue
        if capturing:
            out.append(line.strip())
    return " ".join(out)


def _dedup(found):
    seen = []
    for name in found:
        if name not in seen:
            seen.append(name)
    return seen


def _outcome_sections(text):
    """Every `## Outcome` section, in document order - `_section` reads
    only the first, and a stub-then-real shape (`UX-443`: `_Not
    started._`, then the real one) needs both; `_section` itself is
    unchanged, other callers rely on its single-section reading."""
    parts = text.split("\n## Outcome")
    return [part.split("\n## ", 1)[0] for part in parts[1:]]


def _outcome_texts(text):
    """The Outcome section(s) to scan, or - pre-`UX-497` task files
    (`UX-72`, `UX-81`, `UX-93`) carry no `## Outcome` - the two legacy
    headings that held the same close-measurement before it existed."""
    sections = _outcome_sections(text)
    if sections:
        return sections
    return [tasks._section(text, name) for name in _LEGACY_OUTCOME_HEADINGS]


def _outcome_guard_files(outcome_section):
    """One Outcome (or legacy) section's own guard, not its boilerplate
    or its citations.

    Every closed Outcome carries the identical `<!-- N lines, held by
    test_the_register_is_terse.py -->` footer (`OUTCOME_SKELETON`), and
    `### Mutations verified red and reverted` names whichever files a
    mutation happened to touch, not what covers *this* row - both cut
    (only that subsection, up to the next heading: a guard cited after
    it, e.g. `UX-610`'s own `### Deviation`, is still real - UX-527's
    `### Acceptance Test` follows Mutations too). What is left still
    cites *other* rows' guards as prior art (`UX-724`:
    "test_the_journey_has_an_answer_key.py", no backticks, borrowed
    from `UX-439`) - this codebase's own convention marks a real path
    in backticks (`UX-610`'s own `` `tests/unit/test_x.py` ``, path
    prefix and all) or as a `pytest` command's own argument; a bare
    mention in prose is neither, so only those two count."""
    text = _HTML_COMMENT.sub(
        "", _MUTATIONS_SUBSECTION.sub("\n", outcome_section))
    found = _BACKTICKED_GUARD_FILE.findall(text)
    for line in text.splitlines():
        if "pytest" in line:
            found += _GUARD_FILE.findall(line)
    return _dedup(found)


def _declared_guard_files(text):
    """The Decision's `Guard:` field, then the Acceptance Test - a task
    *stating* its guard, not prose naming one for some other reason."""
    decision = tasks._section(text, "Decision")
    found = _GUARD_FILE.findall(
        _decision_field(decision, "Guard") if decision else "")
    if found:
        return _dedup(found)
    return _dedup(_GUARD_FILE.findall(tasks._section(text, "Acceptance Test")))


def guard_files(text):
    """Every `test_*.py` a task's own text names, and which of two
    kinds: `"declared"` (the Decision's `Guard:` field or the
    Acceptance Test), else `"inferred"` from the first Outcome (or
    legacy) section naming one - never boilerplate or a mutation
    table. No regex tells "this file proves my claim" (a real guard)
    from "this file is named while explaining why it doesn't"
    (`UX-219`, `UX-826`) - both are prose an Outcome can equally
    contain, so the page marks the *kind* instead of chasing a fourth
    extraction rule."""
    declared = _declared_guard_files(text)
    if declared:
        return declared, "declared"
    for outcome_text in _outcome_texts(text):
        found = _outcome_guard_files(outcome_text)
        if found:
            return found, "inferred"
    return [], None


def area_page_body(area, ids, link_base=None):
    """`UX-688`/`UX-996`/`UX-1000`: one area's page - a view, not a
    file, so it cannot drift from the headers and guards it reads."""
    listed = [uid for uid in ids if tasks.task_file(uid).exists()]
    present = existing_guard_files()
    declared = inferred = 0
    lines = []
    for uid in listed:
        path = tasks.task_file(uid)
        text = path.read_text(encoding="utf-8")
        link = (f"{link_base.rstrip('/')}/{path.name}" if link_base
                else f"../scenarios/{path.name}")
        names, kind = guard_files(text)
        if not names:
            guard_cell = "no guard named"
        else:
            if any(name in present for name in names):
                if kind == "inferred":
                    inferred += 1
                else:
                    declared += 1
            suffix = " (inferred)" if kind == "inferred" else ""
            guard_cell = ", ".join(
                (f"`{name}`" if name in present else f"`{name}` (missing)")
                + suffix
                for name in names)
        lines.append(f"| [{uid}]({link}) | "
                     f"{tasks.header_topic(text) or ''} | {guard_cell} |")
    rows = "\n".join(lines)
    name = area.replace("/", "-") + ".md"
    mechanism = (f"Mechanism: [docs/design/areas/{name}]"
                 f"(../../design/areas/{name})\n\n"
                 if (DESIGN_AREA_PAGES / name).exists() else "")
    covered = declared + inferred
    return (f"# {area}\n\n"
            f"Printed by `dev_area_pages.py --areas` (`UX-688`, `UX-1000`) "
            f"from each task's `**Area:**` header. {len(listed)} row(s); "
            f"the module tree is the fixing guide's §6.\n\n"
            f"{mechanism}| Task | Topic | Guard |\n|---|---|---|\n{rows}\n\n"
            f"covered {covered} / {len(listed)} "
            f"(declared {declared}, inferred {inferred})\n")


def report_areas(name):
    """Print one area's page, or every one, and exit 0 - or 1 naming
    the unknown area (`--areas` never writes: `UX-996`)."""
    pages = tasks.area_pages()
    if name:
        if name not in pages:
            print(f"no such area: {name!r}. Known: {', '.join(sorted(pages))}",
                 file=sys.stderr)
            return 1
        print(area_page_body(name, pages[name]))
        return 0
    for area, ids in pages.items():
        print(area_page_body(area, ids))
    return 0


def write_pages(out_dir, link_base):
    """The only writer (`UX-1000`): one file per area, for
    `dev_records.py publish --pages` to overlay on the records tip."""
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for area, ids in tasks.area_pages().items():
        path = out_dir / (area.replace("/", "-") + ".md")
        path.write_text(area_page_body(area, ids, link_base=link_base),
                        encoding="utf-8")
        written.append(path)
    print(f"wrote {len(written)} page(s) to {out_dir}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--areas", nargs="?", const="", default=None,
                        metavar="NAME",
                        help="print an area page - one named area, or "
                             "every one; never committed (UX-996)")
    parser.add_argument("--out", default=None, metavar="DIR",
                        help="write every area's page here - the only "
                             "writer (needs --link-base)")
    parser.add_argument("--link-base", default=None, metavar="URL",
                        help="with --out: task links point here instead "
                             "of the checkout-relative ../scenarios/")
    args = parser.parse_args(argv)
    if args.out:
        if not args.link_base:
            parser.error("--out needs --link-base - a page published "
                         "alone has no sibling docs/backlog/scenarios/")
        return write_pages(args.out, args.link_base)
    if args.areas is not None:
        return report_areas(args.areas or None)
    parser.error("give --areas or --out --link-base")


if __name__ == "__main__":
    sys.exit(main())
