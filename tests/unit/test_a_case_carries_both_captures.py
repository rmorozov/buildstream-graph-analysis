"""UX-902: every showcase case in `docs/cases/` carries both captures -
a **Before:** (arm `off`) and an **After:** (arm `auto`), each with a
bga-bench run id, the same leg and reproducer paths that exist - and a
**Delta:** with its band, agreeing with the two means to 0.1 pp.
A case with one capture is a projection, and `whatif` holds those.
"""

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

_RUN = re.compile(r"\brun \d{5,}\b")
_ARM = re.compile(r"\barm `(\w+)`")
_LEG = re.compile(r"\bleg `(\w+)`")
_MEAN = re.compile(r"\bmean (\d+(?:\.\d+)?) ?s\b")
_ARM_OF = {"Before": "off", "After": "auto"}
_PATH = re.compile(r"`([\w.-]+(?:/[\w.-]+)+)`")
_SIGNED_PERCENT = re.compile(r"(?<![\w.])[+\-−]\d+(?:\.\d+)? ?%")
_BAND = re.compile(r"\bband\b[^%]*\d+(?:\.\d+)? ?%")


def _case_files():
    out = subprocess.run(
        ["git", "ls-files", "docs/cases/*.md"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    return [REPO / line for line in out.splitlines() if line]


def _paragraph(lines, label):
    """The paragraph opened by `**label:**`, joined - a wrapped line is still that line."""
    out = []
    for line in lines:
        if out and not line.strip():
            break
        if out or line.startswith(f"**{label}:**"):
            out.append(line.strip())
    return " ".join(out)


def _cases(text):
    """Each `## ` section that holds a **Before:** line, as its lines."""
    sections = re.split(r"(?m)^## ", text)[1:]
    return [s.splitlines() for s in sections if any(line.startswith("**Before:**") for line in s.splitlines())]


def _capture_problems(capture, label):
    problems = []
    if not capture:
        return [f"no **{label}:** line"]
    if not _RUN.search(capture):
        problems.append(f"**{label}:** names no `run <id>`")
    arm = _ARM.search(capture)
    if not arm or arm.group(1) != _ARM_OF[label]:
        problems.append(f"**{label}:** names no arm `{_ARM_OF[label]}`")
    if not _LEG.search(capture):
        problems.append(f"**{label}:** names no leg")
    if not _MEAN.search(capture):
        problems.append(f"**{label}:** names no `mean <wall> s`")
    paths = _PATH.findall(capture)
    if not paths:
        problems.append(f"**{label}:** names no reproducer path")
    problems += [f"**{label}:** cites {p}, which does not exist" for p in paths if not (REPO / p).exists()]
    return problems


def _problems(text):
    cases = _cases(text)
    if not cases:
        return ["no case with a **Before:** line"]
    problems = []
    for lines in cases:
        name = lines[0]
        before, after = _paragraph(lines, "Before"), _paragraph(lines, "After")
        for label, capture in (("Before", before), ("After", after)):
            problems += [f"{name}: {p}" for p in _capture_problems(capture, label)]
        legs = {m.group(1) for m in (_LEG.search(before), _LEG.search(after)) if m}
        if len(legs) > 1:
            problems.append(f"{name}: **Before:** and **After:** name different legs {sorted(legs)}")
        delta = _paragraph(lines, "Delta")
        signed = _SIGNED_PERCENT.search(delta)
        if not (signed and _BAND.search(delta)):
            problems.append(f"{name}: **Delta:** needs a signed % and its band")
            continue
        means = [_MEAN.search(before), _MEAN.search(after)]
        if all(means):
            off, auto = (float(m.group(1)) for m in means)
            stated = float(signed.group(0).replace("−", "-").replace("%", ""))
            measured = (auto / off - 1) * 100
            if abs(stated - measured) > 0.1:
                problems.append(f"{name}: **Delta:** {stated:+.1f} % but the means give {measured:+.2f} %")
    return problems


def test_there_is_a_case():
    assert _case_files(), "docs/cases/ tracks no case file"


@pytest.mark.parametrize("path", _case_files(), ids=lambda p: p.name)
def test_every_case_carries_both_captures_and_a_banded_delta(path):
    problems = _problems(path.read_text(encoding="utf-8"))
    assert not problems, f"{path.relative_to(REPO)}: " + "; ".join(problems)
