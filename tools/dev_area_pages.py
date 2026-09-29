#!/usr/bin/env python3
"""`UX-1000`: an area page names each scenario's guard.

    python tools/dev_area_pages.py --areas [NAME]        # print, never writes
    python tools/dev_area_pages.py --out DIR --link-base URL

Takes `area_page_body`/`report_areas` out of `dev_close_task.py`
(`area_pages()` stays there - `dev_scenario.py` imports it) and adds a
Guard column read from the task's one `**Guard:**` line (`UX-1092`) -
each named `test_*.py` marked present or missing under `tests/`, a
`none — <reason>` shown as written, a file with no line said so. A
line r149's backfill took from Outcome prose ends ` · inferred r149`
and is counted apart. A page ends `covered N / M (none K, inferred r149
I, no line F)`: N rows naming >= 1 existing file, of M listed.

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

#: `UX-689`: a hand-written `docs/design/areas/<area>.md`, if one
#: exists, gets one derived `Mechanism:` line in the printed page.
DESIGN_AREA_PAGES = REPO / "docs/design/areas"
#: `UX-1092` step B: a guard the backfill read from prose, not a field.
INFERRED = "inferred r149"
_INFERRED_LINE = re.compile(r"^\*\*Guard:\*\*.*· " + INFERRED + r"[ \t]*$", re.M)


def guard_files(text):
    """`(names, kind)` from the task's `**Guard:**` line alone
    (`UX-1092`): `"named"`, `"inferred"` (named, with the r149 mark),
    `"none"` (the reason in place of names) or `None` for no line."""
    guard = tasks.checks.header_guard(text)
    if guard is None:
        return [], None
    names, reason = guard
    if not names:
        return [reason], "none"
    marked = _INFERRED_LINE.search(text.split("\n## ", 1)[0])
    return names, "inferred" if marked else "named"


def _guard_cell(names, kind, present):
    if kind is None:
        return "no `Guard:` line"
    if kind == "none":
        return "none — " + names[0].replace("|", "\\|")
    cell = ", ".join(f"`{name}`" if name in present else f"`{name}` (missing)" for name in names)
    return cell + (f" · {INFERRED}" if kind == "inferred" else "")


def area_page_body(area, ids, link_base=None):
    """`UX-688`/`UX-996`/`UX-1000`: one area's page - a view, not a
    file, so it cannot drift from the headers and guards it reads."""
    listed = [uid for uid in ids if tasks.task_file(uid).exists()]
    present = tasks.checks.present_guards(tasks.TESTS_ROOT)
    counts = {"named": 0, "inferred": 0, "none": 0, None: 0}
    covered, lines = 0, []
    for uid in listed:
        path = tasks.task_file(uid)
        text = path.read_text(encoding="utf-8")
        link = f"{link_base.rstrip('/')}/{path.name}" if link_base else f"../scenarios/{path.name}"
        names, kind = guard_files(text)
        counts[kind] += 1
        covered += kind in ("named", "inferred") and any(n in present for n in names)
        lines.append(f"| [{uid}]({link}) | {tasks.header_topic(text) or ''} | {_guard_cell(names, kind, present)} |")
    rows = "\n".join(lines)
    name = area.replace("/", "-") + ".md"
    mechanism = (
        f"Mechanism: [docs/design/areas/{name}](../../design/areas/{name})\n\n"
        if (DESIGN_AREA_PAGES / name).exists()
        else ""
    )
    return (
        f"# {area}\n\n"
        f"Printed by `dev_area_pages.py --areas` (`UX-688`, `UX-1000`) "
        f"from each task's `**Area:**` header. {len(listed)} row(s); "
        f"the module tree is the fixing guide's §6.\n\n"
        f"{mechanism}| Task | Topic | Guard |\n|---|---|---|\n{rows}\n\n"
        f"covered {covered} / {len(listed)} "
        f"(none {counts['none']}, {INFERRED} {counts['inferred']}, "
        f"no line {counts[None]})\n"
    )


def report_areas(name):
    """Print one area's page, or every one, and exit 0 - or 1 naming
    the unknown area (`--areas` never writes: `UX-996`)."""
    pages = tasks.area_pages()
    if name:
        if name not in pages:
            print(f"no such area: {name!r}. Known: {', '.join(sorted(pages))}", file=sys.stderr)
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
        path.write_text(area_page_body(area, ids, link_base=link_base), encoding="utf-8")
        written.append(path)
    print(f"wrote {len(written)} page(s) to {out_dir}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--areas",
        nargs="?",
        const="",
        default=None,
        metavar="NAME",
        help="print an area page - one named area, or every one; never committed (UX-996)",
    )
    parser.add_argument(
        "--out", default=None, metavar="DIR", help="write every area's page here - the only writer (needs --link-base)"
    )
    parser.add_argument(
        "--link-base",
        default=None,
        metavar="URL",
        help="with --out: task links point here instead of the checkout-relative ../scenarios/",
    )
    args = parser.parse_args(argv)
    if args.out:
        if not args.link_base:
            parser.error("--out needs --link-base - a page published alone has no sibling docs/backlog/scenarios/")
        return write_pages(args.out, args.link_base)
    if args.areas is not None:
        return report_areas(args.areas or None)
    parser.error("give --areas or --out --link-base")


if __name__ == "__main__":
    sys.exit(main())
