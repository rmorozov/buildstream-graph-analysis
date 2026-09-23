"""`UX-943`: an adopt job writes to the default branch only from the run it names.

`ci.yml` is replayed, not grepped: each `test` cell's steps run under
their own `if:` with one step made red, its job outputs are merged in
every completion order, and each adopt job's `if:` is evaluated on the
result. The tier reference and the touch map adopt from a green run;
the flake ledger from a green run or one red at the drift step alone.
"""
import itertools
import json
import os
import pathlib
import re
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
ADOPTS = ("tier-reference-adopt", "touch-map-adopt", "flake-ledger-adopt")
MAIN = {"event_name": "push", "ref": "refs/heads/main",
        "event": {"repository": {"default_branch": "main"}}}
STATUS = re.compile(r"\b(success|failure|always|cancelled)\(")
TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|'((?:[^']|'')*)'|"
                   r"(==|!=|<=|>=|&&|\|\||[()!<>,.\[\]])|([A-Za-z_][\w-]*))")


def _jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


class _Expr:
    """The subset of GitHub's expression language `ci.yml` uses."""

    def __init__(self, text, context, functions):
        text = text.strip()
        if text.startswith("${{") and text.endswith("}}"):
            text = text[3:-2]
        self.tokens, at = [], 0
        while text[at:].strip():
            match = TOKEN.match(text, at)
            assert match, f"cannot read {text[at:]!r}"
            self.tokens.append(match.groups())
            at = match.end()
        self.at, self.context, self.functions = 0, context, functions

    def value(self):
        result = self._or()
        assert self.at == len(self.tokens), self.tokens[self.at:]
        return result

    def _peek(self):
        return self.tokens[self.at][2] if self.at < len(self.tokens) else None

    def _take(self, op):
        assert self._peek() == op, (op, self.tokens[self.at:])
        self.at += 1

    def _or(self):
        left = self._and()
        while self._peek() == "||":
            self._take("||")
            right = self._and()
            left = left or right
        return left

    def _and(self):
        left = self._compare()
        while self._peek() == "&&":
            self._take("&&")
            right = self._compare()
            left = left and right
        return left

    def _compare(self):
        left = self._unary()
        if self._peek() in ("==", "!="):
            op = self._peek()
            self._take(op)
            same = str(left).lower() == str(self._unary()).lower()
            return same if op == "==" else not same
        return left

    def _unary(self):
        if self._peek() == "!":
            self._take("!")
            return not self._unary()
        return self._primary()

    def _primary(self):
        number, string, op, name = self.tokens[self.at]
        self.at += 1
        if op == "(":
            inner = self._or()
            self._take(")")
            return inner
        if number is not None:
            return float(number)
        if string is not None:
            return string.replace("''", "'")
        assert name, op
        if self._peek() == "(":
            self._take("(")
            args = []
            while self._peek() != ")":
                args.append(self._or())
                if self._peek() == ",":
                    self._take(",")
            self._take(")")
            if name == "format":
                return re.sub(r"\{(\d+)\}", lambda m: str(args[1 + int(m[1])]),
                              args[0])
            if name == "fromJSON":
                return json.loads(args[0])
            return self.functions[name]()
        value = self.context.get(name, "")
        while self._peek() == ".":
            self._take(".")
            key = self.tokens[self.at][3]
            self.at += 1
            value = value.get(key, "") if isinstance(value, dict) else ""
        return value


def _status(results):
    """The four status functions, over the results they read."""
    return {"success": lambda: all(r == "success" for r in results),
            "failure": lambda: "failure" in results,
            "always": lambda: True, "cancelled": lambda: False}


def _holds(condition, context, functions):
    condition = str(condition or "success()")
    if not STATUS.search(condition):
        condition = f"success() && ({condition})"
    return bool(_Expr(condition, context, functions).value())


def _render(text, context):
    return re.sub(r"\$\{\{(.*?)\}\}",
                  lambda m: str(_Expr(m[1], context, {}).value()), text)


def _raises(step):
    """A step whose script ends in `exit 1` is red whenever it runs."""
    lines = (step.get("run") or "").strip().splitlines()
    return bool(lines) and lines[-1].strip() == "exit 1"


def _cell(job, python, red, github, tmp_path):
    """One matrix cell: its result, and the outputs the runner sends."""
    steps, failed = {}, False
    for step in job["steps"]:
        context = {"matrix": {"python-version": python}, "github": github,
                   "steps": steps, "runner": {"temp": str(tmp_path)}}
        functions = _status(["failure" if failed else "success"])
        outputs = {}
        if not _holds(step.get("if"), context, functions):
            outcome = "skipped"
        elif step.get("name") in red or _raises(step):
            outcome = "failure"
        else:
            outcome = "success"
            if "GITHUB_OUTPUT" in (step.get("run") or ""):
                out = tmp_path / "github_output"
                out.write_text("", encoding="utf-8")
                env = {k: _render(str(v), context)
                       for k, v in (step.get("env") or {}).items()}
                subprocess.run(["bash", "-e", "-c", _render(step["run"], context)],
                               env={**os.environ, **env, "GITHUB_OUTPUT": str(out)},
                               check=True)
                outputs = dict(line.split("=", 1) for line in
                               out.read_text(encoding="utf-8").splitlines())
        excused = outcome == "failure" and step.get("continue-on-error") is True
        failed = failed or (outcome == "failure" and not excused)
        if "id" in step:
            steps[step["id"]] = {"outcome": outcome, "outputs": outputs,
                                 "conclusion": "success" if excused else outcome}
    context = {"steps": steps, "matrix": {"python-version": python}}
    sent = {key: _render(str(value), context)
            for key, value in (job.get("outputs") or {}).items()}
    # The runner skips an empty output (`JobExtension.cs`, "Skip output").
    return ("failure" if failed else "success"), {k: v for k, v in sent.items() if v}


def _matrix_cells(jobs, github):
    """`UX-995`: the matrix is an expression now, evaluated per event -
    a pull request gets the newest Python alone, a push all four."""
    return _Expr(jobs["test"]["strategy"]["matrix"]["python-version"],
                {"github": github}, {}).value()


def _adopted(red_by_cell, tmp_path, github=MAIN):
    """Which adopt jobs run, once per order the cells could finish in."""
    jobs = _jobs()
    cells = {python: _cell(jobs["test"], python, red_by_cell.get(python, ()),
                           github, tmp_path)
             for python in _matrix_cells(jobs, github)}
    result = "failure" if any(r == "failure" for r, _ in cells.values()) else "success"
    verdicts = set()
    for order in itertools.permutations(cells):
        merged = {}
        for python in order:
            merged.update(cells[python][1])  # last writer wins, per key
        needs = {"test": {"result": result, "outputs": merged}}
        ran = []
        for name in ADOPTS:
            wanted = jobs[name]["needs"]
            wanted = [wanted] if isinstance(wanted, str) else wanted
            results = [needs[need]["result"] for need in wanted]
            runs = _holds(jobs[name]["if"], {"needs": needs, "github": github},
                          _status(results))
            needs[name] = {"result": "success" if runs else "skipped"}
            if runs:
                ran.append(name)
        verdicts.add(tuple(ran))
    assert len(verdicts) == 1, f"the adopt depends on which cell finished last: {verdicts}"
    return result, set(verdicts.pop())


def _step(predicate):
    names = [s["name"] for s in _jobs()["test"]["steps"]
             if predicate(s.get("run") or "")]
    assert len(names) == 1, names
    return names[0]


def _suites():
    return [s["name"] for s in _jobs()["test"]["steps"]
            if re.search(r"\bmake test(?!-)", s.get("run") or "")]


DRIFT = _step(lambda run: "dev_tier_drift.py" in run and "--against" in run)
PERF = _step(lambda run: "dev_perf_ratchet.py --against" in run)
CELLS = _matrix_cells(_jobs(), MAIN)


def test_a_green_run_adopts_all_three(tmp_path):
    """The control: a condition nothing satisfies passes every red case."""
    assert _adopted({}, tmp_path) == ("success", set(ADOPTS))


def test_a_green_pull_request_adopts_nothing(tmp_path):
    github = {**MAIN, "event_name": "pull_request", "ref": "refs/pull/1/merge"}
    assert _adopted({}, tmp_path, github) == ("success", set())


@pytest.mark.parametrize("red_by_cell", [
    pytest.param({python: set(_suites()) for python in CELLS}, id="every-suite"),
    pytest.param({CELLS[0]: set(_suites())}, id="one-suite"),
    # `UX-995`: DRIFT and PERF moved onto 3.12.
    pytest.param({"3.12": {DRIFT, PERF}}, id="drift-and-perf"),
    pytest.param({"3.12": {DRIFT}, "3.11": set(_suites())}, id="drift-and-3.11"),
])
def test_a_run_red_for_another_reason_adopts_nothing(red_by_cell, tmp_path):
    assert _adopted(red_by_cell, tmp_path) == ("failure", set())


def test_a_run_red_only_at_the_drift_step_appends_the_ledger_alone(tmp_path):
    """Still red - the gate's verdict is raised - and the ledger's rows are
    exactly that step's excursions."""
    assert _adopted({"3.12": {DRIFT}}, tmp_path) == (
        "failure", {"flake-ledger-adopt"})
