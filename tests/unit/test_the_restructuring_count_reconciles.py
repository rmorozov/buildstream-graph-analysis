"""The restructuring headline says how many of the per-element never-read edges it covers."""

import json
import re
from pathlib import Path

from bga.cli import main

RUN = Path(__file__).resolve().parents[1] / "fixtures/macro_micro/run"


def _correlate(capsys, *extra):
    main(["correlate", str(RUN), *extra])
    return capsys.readouterr().out


def test_the_headline_carries_the_per_element_total_and_the_on_path_count(capsys):
    document = json.loads(_correlate(capsys, "--format", "json"))
    total = sum(len(e.get("unused_dependencies") or []) for e in document["actionable"])
    on_path = len(document["restructuring"][0]["edges"])
    headline = next(line for line in _correlate(capsys).splitlines() if line.startswith("Restructuring"))
    assert f"({on_path} of the {total} never-read declared edges" in headline
    assert re.search(r"\d+ of the \d+", headline) and on_path < total
