#!/usr/bin/env python3
"""UX-486: the rule a committed analysis document is written under.

Two fixtures in this tree hold an analysis the tool produced, and both
are compared against a fresh run - `tests/fixtures/golden/
mixed_task_kinds/expected_output.json` and
`tests/fixtures/with_timeline/analyze.json`. Regenerating one is not
`bga analyze > file`: parts of what `analyze` prints are properties of
the **machine that ran it**, and committing those makes the fixture
fail on the first release rather than on the first regression.

The rule, in one place because it was in three:

- **`run_instance`** (`UX-95`) names *which capture* this is - a
  wall-clock stamp and the absolute path it was read from. Dropped.
- **`producer`** (`UX-249`) names *which build of bga* ran it. Dropped;
  it is still asserted, by
  `tests/unit/test_an_artifact_says_what_wrote_it.py`.
- **The fixture's own path**, which `UX-218`'s next-step commands name
  because a command that did not name it would not be runnable.
  Replaced with one fixed token. The commands are still compared; only
  the directory they point at is neutralised.

Everything else is the analysis and is compared exactly.

`with_timeline/analyze.json` had no recipe and no guard, and drifted
four findings behind the analyzer before anything noticed - `UX-486`.

Usage
-----
    python3 tools/dev_refresh_analysis.py --check
    python3 tools/dev_refresh_analysis.py --write tests/fixtures/with_timeline

`--check` is what the guard runs; `--write` is what a round runs after
a deliberate behaviour change, and then reads `git diff` to confirm the
change it intended is the only one.
"""
import argparse
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

#: The keys that name the machine rather than the analysis. Named here
#: rather than in each caller, because "which keys are the fixture" is
#: the question a contributor regenerating one actually has.
MACHINE_KEYS = ("run_instance", "producer")


class Fixture:
    """A committed analysis, and how to reproduce it.

    `run` is what `analyze` is pointed at, relative to the fixture -
    `.` for the golden snapshot, which *is* the run directory, and
    `run` for a capture that keeps its analysis beside it. `token` is
    what the fixture's own path is rewritten to, and differs only
    because the two files were written in different rounds and their
    committed text is what it is.
    """

    def __init__(self, path, into, run=".", token="<run>"):
        self.path = REPO / path
        self.into = self.path / into
        self.run = run
        self.token = token

    @property
    def name(self):
        return str(self.path.relative_to(REPO))

    def target(self):
        return self.path if self.run == "." else self.path / self.run

    def analysed(self):
        """A fresh run, with the machine taken out of it."""
        target = self.target()
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(target),
             "--format", "json", "--diagnostics"],
            capture_output=True, text=True, cwd=REPO, timeout=600)
        if done.returncode != 0:
            raise SystemExit(f"{self.name}: analyze failed\n{done.stderr}")
        # The fixture directory, not the run directory: the committed
        # text is `<fixture>/run` on the capture, so the token stands
        # for the directory and `/run` survives it.
        payload = json.loads(done.stdout.replace(str(self.path), self.token))
        for key in MACHINE_KEYS:
            payload.pop(key, None)
        return payload

    def committed(self):
        return json.loads(self.into.read_text(encoding="utf-8"))

    def write(self):
        self.into.write_text(json.dumps(self.analysed(), indent=4) + "\n",
                             encoding="utf-8")
        return self.into


#: Every committed analysis in the tree. A fixture absent from here is
#: one nothing regenerates and nothing checks, which is the state
#: `with_timeline` was in.
FIXTURES = (
    Fixture("tests/fixtures/golden/mixed_task_kinds",
            into="expected_output.json", run=".", token="<run>"),
    Fixture("tests/fixtures/with_timeline",
            into="analyze.json", run="run", token="<fixture>"),
)


def differences(fixture):
    """`(where, what)` pairs where the committed file and a fresh run
    disagree, most legible first.

    Finding ids first because that is the drift this was written
    after: four findings a round added reached this fixture and none of
    them was in it, and the ids are the shape of the document a reader
    can check at a glance.
    """
    fresh, held = fixture.analysed(), fixture.committed()
    out = []
    ids_fresh = [f["id"] for f in fresh.get("findings", [])]
    ids_held = [f["id"] for f in held.get("findings", [])]
    if ids_fresh != ids_held:
        out.append(("findings", f"committed {ids_held}\n  analyzer  {ids_fresh}"))
    for key in sorted(set(fresh) | set(held)):
        if key == "findings":
            continue
        if json.dumps(fresh.get(key), sort_keys=True) != json.dumps(
                held.get(key), sort_keys=True):
            out.append((key, "differs"))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", metavar="FIXTURE", nargs="?", const="all",
                        help="rewrite the committed document(s) from a fresh "
                             "run, instead of checking")
    args = parser.parse_args(argv)
    if args.write:
        chosen = [f for f in FIXTURES
                  if args.write == "all" or f.name == args.write.rstrip("/")]
        if not chosen:
            raise SystemExit(f"no fixture named {args.write}; this tool knows "
                             f"{[f.name for f in FIXTURES]}")
        for fixture in chosen:
            print(f"wrote {fixture.write().relative_to(REPO)}")
        return 0
    problems = 0
    for fixture in FIXTURES:
        found = differences(fixture)
        if not found:
            print(f"  ok    {fixture.name}")
            continue
        problems += 1
        print(f"  DRIFT {fixture.name}")
        for where, what in found:
            print(f"          {where}: {what}")
    print(f"{problems} of {len(FIXTURES)} committed analysis document(s) "
          f"disagree with the analyzer")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
