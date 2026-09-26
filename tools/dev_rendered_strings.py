#!/usr/bin/env python3
"""UX-1020: every rendered label read as one voice - sentence case,
and a plural chosen by its count, not spelled `(s)`.

Walks `golden` and `macro_micro`'s headings, buttons, `summary`,
rail entries, `th` and `option` text and normalises each (counts to
`#`) into `docs/design/rendered-strings.json` - one row per distinct
shape, with the exception class it needs (`code`, `unit`, `product
name`, `acronym`) where sentence case does not hold. `--check` is the
generator run read-only, for the test that walks the live page against
the committed file.
"""
import argparse
import json
import pathlib
import re
import sys
from typing import Optional

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

INVENTORY = REPO / "docs/design/rendered-strings.json"

ROLES = {
    "heading": "h1,h2,h3,h4,h5,h6",
    "button": "button",
    "summary": "summary",
    "rail-chapter": ".toc-rail, .toc-chapter-open",
    "rail-entry": "a[data-toc]",
    "th": "th",
    "option": "option",
}

#: A heading or rail label carries its own control - the "View as
#: JSON" toggle, the reader tag - as a sibling in the DOM, not its
#: label; walking `textContent` would concatenate both.
_STRIP = "button, [data-reader-tag], [data-json-toggle]"

WALK_JS = "(() => {\n  const out = [];\n" \
    f'  const strip = "{_STRIP}";\n' \
    "  const ownText = (el) => {\n" \
    "    const clone = el.cloneNode(true);\n" \
    "    for (const dead of clone.querySelectorAll(strip)) dead.remove();\n" \
    "    return (clone.textContent || \"\").trim().replace(/\\s+/g, \" \");\n" \
    "  };\n" \
    "  const grab = (sel, role) => {\n" \
    "    for (const el of document.querySelectorAll(sel)) {\n" \
    "      const t = ownText(el);\n" \
    "      if (t) out.push([role, t]);\n    }\n  };\n" \
    + "\n".join(f'  grab("{sel}", "{role}");' for role, sel in ROLES.items()) \
    + "\n  return out;\n})()"

#: A rendered word never has to be sentence case when it is one of
#: these - a published element/task name, a command, an id a schema
#: gave a hyphen or an underscore rather than a sentence, or a finite,
#: named acronym - never every all-caps word, which is the mutation
#: `restore text-transform: uppercase` still has to redden.
_ELEMENT = re.compile(r"^[\w./-]+\.bst$")
_CODE = re.compile(r"^[a-z][a-z0-9_]*$")
_ACRONYMS = {"JSON", "CPU", "ELF", "CI", "SQL", "PT_INTERP", "LD_PRELOAD"}


def normalize(text: str) -> str:
    """Counts and countable lists collapse to `#`, so one row of the
    inventory covers every run's population."""
    return re.sub(r"\d[\d,]*", "#", text)


def _lead_word(text: str) -> str:
    return text.lstrip("▾▸ ").split(" ", 1)[0] if text else ""


def exception_of(text: str) -> Optional[str]:
    """`None` if `text` must read sentence case; the class it claims
    otherwise. `bga` is the tool's own command name; a sentence the
    analyzer wrote *about* an element leads with the element's own
    name, unwaivable proper-noun case (`UX-374`)."""
    if text in ("bga", "anyone"):
        return "command name" if text == "bga" else "sentence continuation"
    if _ELEMENT.match(text) or _ELEMENT.match(_lead_word(text)):
        return "product name"
    words = text.split()
    if words and _CODE.match(words[-1]) and "_" in words[-1]:
        return "code"
    if any(w.strip("?.,:") in _ACRONYMS for w in words):
        return "acronym"
    return None


def is_sentence_case(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    if not letters[0].isupper():
        return False
    for word in re.findall(r"[A-Za-z_]+", text)[1:]:
        if word in _ACRONYMS:
            continue
        if len(word) > 1 and word.isupper():
            return False
    return True


def walk(browser, uri):
    return browser.measure(uri, WALK_JS)


def rows_for(browser, label, uri):
    seen, rows = set(), []
    for role, text in walk(browser, uri):
        norm = normalize(text)
        key = (role, norm)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"role": role, "text": norm,
                      "exception": exception_of(text)})
    return rows


def generate():
    import tempfile

    from tests import pages
    from tests.browser import Browser, find_chrome
    chrome = find_chrome()
    with Browser(chrome) as browser, tempfile.TemporaryDirectory() as td:
        tdp = pathlib.Path(td)
        rows = []
        seen = set()
        for label in ("golden", "macro_micro"):
            uri = pages.export_uri(pages.FIXTURES[label], tdp / label)
            for row in rows_for(browser, label, uri):
                key = (row["role"], row["text"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
        return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rows = generate()
    text = json.dumps(rows, indent=2, sort_keys=True) + "\n"
    if args.write:
        INVENTORY.write_text(text)
        print(f"wrote {INVENTORY} ({len(rows)} rows)")
    else:
        print(text)


if __name__ == "__main__":
    main()
