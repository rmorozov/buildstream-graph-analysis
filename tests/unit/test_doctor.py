"""UX-125: the environment checked before a build proves it broken.

Every capture-capable environment this project has stood up was
assembled by failure - and each of those failures already had its answer
written down, in a CI comment, a staging script's header, or the
ingestion guide. What did not exist was the *sequence*.

These cover the properties that make `doctor` worth running rather than
its exact prose: that it never mutates anything, that a check which
cannot run says so instead of passing, that two problems wearing the
same error message get different remedies, and that the exit code means
what a script would assume.
"""
import json
import os
import re
import subprocess
import sys

import pytest

from tools.bga_doctor import (
    FAIL, OK, SKIP, WARN, check_compiler, check_plane3, check_project_loads,
    check_staged_sources, format_text, main, run_checks,
)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def bare_project(tmp_path):
    """A loadable project that stages nothing executable - the
    `stage_*.sh` trap, which fails a real build with a cryptic exec
    error deep inside it."""
    root = tmp_path / "bare"
    (root / "elements").mkdir(parents=True)
    (root / "files" / "src").mkdir(parents=True)
    (root / "project.conf").write_text(
        "name: bare-project\nmin-version: 2.0\nelement-path: elements\n")
    (root / "elements" / "all.bst").write_text(
        "kind: import\nsources:\n- kind: local\n  path: files/src\n")
    (root / "files" / "src" / "README").write_text("nothing executable here\n")
    return root


class TestItNeverChangesAnything:
    def test_a_project_directory_is_untouched(self, bare_project):
        """Read-only by contract: it recommends `stage_runtimes.sh`, it
        does not run it. A diagnostic that mutates what it diagnoses
        cannot be run twice with the same meaning."""
        before = {
            path: os.stat(os.path.join(root, path)).st_mtime
            for root, _dirs, files in os.walk(bare_project)
            for path in files
        }

        run_checks(str(bare_project))

        after = {
            path: os.stat(os.path.join(root, path)).st_mtime
            for root, _dirs, files in os.walk(bare_project)
            for path in files
        }
        assert before == after

    def test_no_new_files_appear(self, bare_project):
        listing = sorted(
            os.path.join(r, f) for r, _d, fs in os.walk(bare_project) for f in fs)

        run_checks(str(bare_project))

        assert sorted(
            os.path.join(r, f) for r, _d, fs in os.walk(bare_project) for f in fs
        ) == listing


class TestAnUnrunnableCheckSaysSoRatherThanPassing:
    def test_a_project_with_no_elements_directory_skips_the_census(self, tmp_path):
        """`skip` and `ok` are different claims. A census that could not
        run must not read as "nothing static here"."""
        root = tmp_path / "empty"
        root.mkdir()
        (root / "project.conf").write_text("name: x\n")

        [finding] = check_staged_sources(str(root))

        assert finding["status"] == SKIP

    def test_a_directory_that_is_not_a_project_fails_rather_than_skips(self, tmp_path):
        """Being handed the wrong path is a user error worth reporting,
        not a check to wave through."""
        [finding] = check_project_loads(str(tmp_path))

        assert finding["status"] == FAIL
        assert "no project.conf" in finding["summary"]

    def test_a_missing_log_tree_warns_rather_than_fails(self, tmp_path, monkeypatch):
        """Plane 3 having nothing to read is a fact about the machine,
        not a broken environment - Planes 1 and 2 are unaffected."""
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "nothing"))

        assert check_plane3()["status"] == WARN


class TestTheCensusChecksAreTwoDifferentThings:
    def test_a_project_staging_nothing_executable_is_warned_about(self, bare_project):
        findings = {f["id"]: f for f in check_staged_sources(str(bare_project))}

        assert findings["staged-sources"]["status"] == WARN
        assert "stage_runtimes.sh" in findings["staged-sources"]["remedy"]

    def test_a_busybox_project_is_reported_as_a_blind_spot_not_a_failure(self):
        """`examples/01` builds perfectly and produces an empty Plane 2
        capture. That is a coverage fact with a remedy (`--trace-spine`),
        not a broken environment."""
        project = os.path.join(REPO, "examples", "01-resource-contention")
        if not os.path.isfile(
                os.path.join(project, "files", "runtime", "bin", "sh")):
            pytest.skip("examples/01 is not staged - run examples/stage_runtimes.sh")

        findings = {f["id"]: f for f in check_staged_sources(project)}

        assert findings["static-blind-spot"]["status"] == WARN
        assert "--trace-spine=auto" in findings["static-blind-spot"]["remedy"]
        assert findings["staged-sources"]["status"] == OK

    def test_an_all_dynamic_project_is_not_flagged_blind(self):
        project = os.path.join(REPO, "examples", "06-macro-micro-optimization")
        if not os.path.isfile(
                os.path.join(project, "files", "toolchain", "usr", "bin", "gcc")):
            pytest.skip("examples/06 is not staged - run examples/stage_cpp_toolchain.sh")

        findings = {f["id"]: f for f in check_staged_sources(project)}

        assert findings["static-blind-spot"]["status"] == OK


class TestTwoProblemsWearingOneErrorGetDifferentRemedies:
    """"No element plugin registered for kind 'cmake'" is produced both
    by a missing `buildstream-plugins` **and** by a project that has not
    declared it. The remedies are opposites, and telling a user to
    install what they already have is how a diagnostic loses its
    reader."""

    @pytest.fixture
    def undeclared_cmake(self, tmp_path):
        root = tmp_path / "nocmake"
        (root / "elements").mkdir(parents=True)
        (root / "files" / "src").mkdir(parents=True)
        (root / "project.conf").write_text(
            "name: no-plugins-project\nmin-version: 2.0\nelement-path: elements\n")
        (root / "elements" / "all.bst").write_text(
            "kind: cmake\nsources:\n- kind: local\n  path: files/src\n")
        (root / "files" / "src" / "CMakeLists.txt").write_text("")
        return root

    def _remedy(self, project, installed, monkeypatch):
        import tools.bga_doctor as doctor
        monkeypatch.setattr(doctor, "_plugins_package_installed", lambda: installed)
        [finding] = doctor.check_project_loads(str(project))
        assert finding["status"] == FAIL, finding
        return finding["remedy"]

    @pytest.mark.bst
    @pytest.mark.skipif(not os.environ.get("PATH"), reason="no PATH")
    def test_the_package_missing_says_install_it(self, undeclared_cmake, monkeypatch):
        import shutil
        if not shutil.which("bst"):
            pytest.skip("bst not on PATH")

        remedy = self._remedy(undeclared_cmake, False, monkeypatch)

        assert "pip install buildstream-plugins" in remedy

    @pytest.mark.bst
    def test_the_package_present_says_declare_it(self, undeclared_cmake, monkeypatch):
        import shutil
        if not shutil.which("bst"):
            pytest.skip("bst not on PATH")

        remedy = self._remedy(undeclared_cmake, True, monkeypatch)

        assert "has not declared it" in remedy
        assert "pip install" not in remedy


class TestTheContractAScriptWouldAssume:
    def test_only_a_failure_makes_the_exit_code_nonzero(self, capsys):
        """A warning is a thing to read, not a thing to block on - a
        static-binary blind spot and a missing log tree are both normal."""
        assert main([]) in (0, 1)
        out = capsys.readouterr().out
        assert "bga doctor" in out

    def test_the_json_form_carries_an_id_per_check(self, capsys):
        main(["--format", "json"])

        payload = json.loads(capsys.readouterr().out)
        assert payload["checks"]
        assert all({"id", "status", "summary"} <= set(c) for c in payload["checks"])

    def test_every_status_renders(self):
        """`format_text` indexes a table by status; a status with no entry
        would be a KeyError in the one command a broken environment
        runs."""
        checks = [
            {"id": "a", "status": OK, "summary": "s", "remedy": None, "detail": []},
            {"id": "b", "status": FAIL, "summary": "s", "remedy": "r", "detail": ["d"]},
            {"id": "c", "status": WARN, "summary": "s", "remedy": "r", "detail": []},
            {"id": "d", "status": SKIP, "summary": "s", "remedy": None, "detail": []},
        ]

        rendered = format_text(checks, "/some/project")

        assert "[FAIL]" in rendered and "[warn]" in rendered and "[skip]" in rendered
        assert "-> r" in rendered

    def test_a_remedy_is_printed_for_everything_that_is_not_ok(self):
        checks = [{"id": "x", "status": WARN, "summary": "s",
                   "remedy": "do the thing", "detail": []}]

        assert "do the thing" in format_text(checks, None)

    def test_an_ok_check_does_not_print_a_remedy(self):
        checks = [{"id": "x", "status": OK, "summary": "fine",
                   "remedy": "unused", "detail": []}]

        assert "unused" not in format_text(checks, None)


def test_the_compiler_check_is_the_one_the_capture_performs():
    """`compile_hook` raises on a missing cc/gcc after the build has
    already started. This is the same check, moved earlier - so it must
    stay the same check.

    UX-143: this used to restate the implementation (`shutil.which("cc")
    or shutil.which("gcc")`), which is not a comparison - the two could
    diverge and both this test and the doctor would agree with each other
    while disagreeing with the capture. Now it reads the predicate the
    tracer itself uses.
    """
    import inspect

    from tools import bst_native_build_tracer as tracer

    source = inspect.getsource(tracer.compile_hook)
    compilers = set(re.findall(r'shutil\.which\(["\'](\w+)["\']\)', source))
    assert compilers, "compile_hook no longer resolves a compiler by name"

    import shutil
    if not any(shutil.which(name) for name in compilers):
        assert check_compiler()["status"] == FAIL
        return
    # UX-153: present is not the same as capable, so OK is no longer the
    # only pass - a compiler that cannot link `-static` warns, naming
    # which capability is missing, rather than reporting a spine that
    # will not build as a healthy environment.
    assert check_compiler()["status"] in (OK, WARN), (
        f"doctor and compile_hook disagree about {sorted(compilers)}")


def test_doctor_is_reachable_through_the_cli():
    """It is only useful if it is the thing a confused user can find."""
    result = subprocess.run(
        [sys.executable, "-m", "bga.cli", "doctor", "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=300,
    )

    assert result.returncode in (0, 1), result.stderr
    assert json.loads(result.stdout)["checks"]


class TestTheLoadProbeUsesTheProjectsOwnElements:
    """UX-142: it ran `bst show ... all.bst`, hardcoded. Every project
    here ships an `all.bst`, so nine fixtures agreed and every real
    project - freedesktop-sdk included - got `[FAIL] project-loads` and
    exit 1 while being perfectly healthy. A fixture convention read back
    as a world fact, by the command the walkthrough teaches first."""

    def test_elements_are_discovered_shallowest_first(self, tmp_path):
        from tools.bga_doctor import discover_elements

        root = tmp_path / "p" / "elements"
        (root / "components" / "deep").mkdir(parents=True)
        (tmp_path / "p" / "project.conf").write_text("name: p\n")
        for relative in ("z.bst", "components/b.bst", "components/deep/c.bst"):
            (root / relative).write_text("kind: manual\n")

        assert discover_elements(str(tmp_path / "p")) == [
            "z.bst", os.path.join("components", "b.bst"),
            os.path.join("components", "deep", "c.bst")]

    def test_a_declared_element_path_is_honoured(self, tmp_path):
        from tools.bga_doctor import discover_elements, element_path

        project = tmp_path / "p"
        (project / "parts").mkdir(parents=True)
        (project / "project.conf").write_text(
            "name: p\nmin-version: 2.0\nelement-path: parts\n")
        (project / "parts" / "only.bst").write_text("kind: manual\n")

        assert element_path(str(project)) == "parts"
        assert discover_elements(str(project)) == ["only.bst"]

    def test_the_default_element_path_is_buildstreams(self, tmp_path):
        from tools.bga_doctor import element_path

        (tmp_path / "project.conf").write_text("name: p\n")

        assert element_path(str(tmp_path)) == "elements"

    def test_a_project_with_no_elements_warns_rather_than_failing(self, tmp_path):
        """"Nothing to probe" is not "does not load" - the second sends a
        user hunting a plugin problem that is not there."""
        from tools.bga_doctor import check_project_loads

        (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")

        [finding] = check_project_loads(str(tmp_path))

        assert finding["status"] in (WARN, SKIP)
        if finding["status"] == WARN:
            assert "no element found to probe" in finding["summary"]

    @pytest.mark.bst
    def test_a_project_whose_only_element_is_not_all_bst_passes(self, tmp_path):
        """The acceptance: `examples/06` with `all.bst` renamed."""
        import shutil
        if not shutil.which("bst"):
            pytest.skip("bst not on PATH")
        source = os.path.join(REPO, "examples", "06-macro-micro-optimization")
        if not os.path.isfile(
                os.path.join(source, "files", "toolchain", "usr", "bin", "gcc")):
            pytest.skip("examples/06 is not staged - run examples/stage_cpp_toolchain.sh")

        project = tmp_path / "renamed"
        shutil.copytree(source, project, symlinks=True)
        shutil.rmtree(project / "optimized", ignore_errors=True)
        os.rename(project / "elements" / "all.bst",
                  project / "elements" / "everything.bst")

        [finding] = check_project_loads(str(project))

        assert finding["status"] == OK, finding
        assert "all.bst" not in finding["summary"]

    @pytest.mark.bst
    def test_one_broken_element_does_not_condemn_the_project(self, tmp_path):
        """A single element failing on its own is a fact about that
        element. The probe falls through to the next one."""
        import shutil
        if not shutil.which("bst"):
            pytest.skip("bst not on PATH")

        project = tmp_path / "mixed"
        (project / "elements").mkdir(parents=True)
        (project / "files").mkdir()
        (project / "project.conf").write_text(
            "name: mixed\nmin-version: 2.0\nelement-path: elements\n")
        # Sorts first, and names a kind no plugin provides.
        (project / "elements" / "aaa-broken.bst").write_text(
            "kind: cmake\nsources:\n- kind: local\n  path: files\n")
        (project / "elements" / "zzz-fine.bst").write_text(
            "kind: import\nsources:\n- kind: local\n  path: files\n")

        [finding] = check_project_loads(str(project))

        assert finding["status"] == OK, finding
        assert "zzz-fine.bst" in finding["summary"]


class TestTheCompilerCheckProbesRatherThanChecks:
    """UX-153: `bga doctor`'s own principle, applied to itself. A
    compiler on PATH is not the question - the capture needs `-shared
    -fPIC` for the hook and `-static` for the spine, and they fail
    separately. A static libc is a separate package on some
    distributions, so the spine is the half that goes missing on a
    machine where the hook compiles fine."""

    def test_both_capabilities_are_probed(self):
        import inspect

        import tools.bga_doctor as doctor

        source = inspect.getsource(doctor.check_compiler)
        assert "-shared" in source and "-fPIC" in source
        assert "-static" in source

    def test_a_compiler_that_cannot_link_static_warns_and_says_which(
            self, monkeypatch):
        """Not FAIL: Plane 1, Plane 3 and the hook all still work. Not
        OK either, because `--trace-spine` will not."""
        import tools.bga_doctor as doctor

        monkeypatch.setattr(doctor, "_compiles",
                            lambda argv: "-static" not in argv)

        finding = doctor.check_compiler()

        assert finding["status"] == WARN, finding
        assert "-static" in finding["summary"]
        assert "ptrace spine" in finding["summary"]
        assert "-shared" not in finding["summary"], "the hook half is fine"

    def test_a_working_compiler_is_ok(self, monkeypatch):
        import tools.bga_doctor as doctor

        monkeypatch.setattr(doctor, "_compiles", lambda argv: True)

        assert doctor.check_compiler()["status"] == OK

    def test_it_writes_nothing(self, monkeypatch, tmp_path):
        """A diagnostic that leaves files behind cannot be run twice with
        the same meaning. The probe feeds source on stdin and links to
        /dev/null."""
        import inspect

        import tools.bga_doctor as doctor

        source = inspect.getsource(doctor._compiles)
        assert "/dev/null" in source
        assert "input=" in source

        before = sorted(os.listdir(tmp_path))
        monkeypatch.chdir(tmp_path)
        doctor.check_compiler()
        assert sorted(os.listdir(tmp_path)) == before


class TestTheWholeChainProbe:
    """UX-149: doctor proved the *parts* - bst runs, bwrap builds a
    sandbox with bga's own arguments, a compiler exists - and
    `--diagnose` instruments the user's real build, which costs a real
    build and yields evidence only after the failure. Nothing ran the
    actual chain: bst → buildbox-run → the PATH shim → the rewritten
    argv → the hook inside the sandbox."""

    def test_it_is_off_unless_asked_for(self, capsys):
        """It builds something. A default `bga doctor` must stay the
        seconds-long read-only check it is documented as."""
        main([])

        out = capsys.readouterr().out
        assert "chain-" not in out

    def test_without_bst_it_skips_rather_than_failing(self, monkeypatch):
        import tools.bga_doctor as doctor

        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

        [finding] = doctor.check_capture_chain()

        assert finding["status"] == SKIP

    def test_without_a_staged_runtime_it_skips_and_names_the_script(
            self, monkeypatch):
        """It will not build a sysroot: a diagnostic that builds a
        sysroot is not a diagnostic.

        `bst` is faked present as well as the runtime faked absent - on a
        machine with no bst the earlier skip fires first, and asserting
        on `remedy` then reads None. That is how this passed locally and
        failed on every matrix job.
        """
        import tools.bga_doctor as doctor

        monkeypatch.setattr(doctor.shutil, "which",
                            lambda name: "/usr/bin/bst" if name == "bst" else None)
        monkeypatch.setattr(doctor, "_find_stageable_runtime", lambda: None)

        [finding] = doctor.check_capture_chain()

        assert finding["status"] == SKIP
        assert "stage_runtimes.sh" in (finding["remedy"] or "")

    def test_the_isolated_home_keeps_the_user_site_packages(self, tmp_path):
        """UX-84, hit again in production code the first time this ran:
        `HOME` is how Python finds the per-user site-packages, so
        replacing it unimports a `pip install --user` BuildStream and
        `bst` dies with `ModuleNotFoundError: No module named 'jinja2'`
        before reading the project."""
        import site
        import sys

        import tools.bga_doctor as doctor

        env = doctor._isolated_home(str(tmp_path))

        assert env["HOME"] == str(tmp_path)
        try:
            user_site = site.getusersitepackages() if site.ENABLE_USER_SITE else None
        except Exception:
            user_site = None
        if user_site and user_site in sys.path and os.path.isdir(user_site):
            assert user_site in env["PYTHONPATH"]

    @pytest.mark.bst
    def test_the_chain_reports_every_link_in_order(self):
        """The acceptance: each link named, in chain order, with its own
        verdict."""
        import shutil

        import tools.bga_doctor as doctor

        for tool in ("bst", "bwrap"):
            if not shutil.which(tool):
                pytest.skip(f"{tool} not on PATH")
        if doctor._find_stageable_runtime() is None:
            pytest.skip("no staged runtime - run examples/stage_runtimes.sh")

        findings = doctor.check_capture_chain()

        ids = [f["id"] for f in findings]
        assert ids[:3] == ["chain-shim-exec", "chain-build", "chain-shim-reached"], ids
        assert ids[-1] == "chain-records", ids
        assert all(f["status"] in (OK, WARN) for f in findings), findings

    @pytest.mark.bst
    def test_a_static_runtime_warns_rather_than_failing(self):
        """The probe's runtime is busybox, which the LD_PRELOAD hook
        structurally cannot see - so the spine answers instead. That is
        the blind spot being covered, working; reporting it as a broken
        chain would fail every machine where everything is fine."""
        import shutil

        import tools.bga_doctor as doctor

        if not shutil.which("bst") or doctor._find_stageable_runtime() is None:
            pytest.skip("bst or a staged runtime is missing")

        records = [f for f in doctor.check_capture_chain()
                   if f["id"] == "chain-records"]

        assert records and records[0]["status"] in (OK, WARN)
        if records[0]["status"] == WARN:
            assert "spine" in records[0]["remedy"]


class TestBstBesideTheConsoleScriptButNotOnPath:
    """Found by `installed-capture`'s first run: invoking `bga` by its
    full path — `/venv/bin/bga` — does *not* put that venv's `bin` on
    PATH, so a `bst` installed right beside it is invisible to
    `shutil.which` and to every subprocess the capture launches.

    "Not installed" and "installed next to me and not on PATH" are
    different problems, and only one is fixed by installing something."""

    def test_a_sibling_bst_is_named_rather_than_missed(self, tmp_path, monkeypatch):
        import tools.bga_doctor as doctor

        venv_bin = tmp_path / "bin"
        venv_bin.mkdir()
        (venv_bin / "bst").write_text("#!/bin/sh\nexit 0\n")
        (venv_bin / "bst").chmod(0o755)
        monkeypatch.setattr(doctor.sys, "executable", str(venv_bin / "python3"))
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

        finding = doctor.check_bst()

        assert finding["status"] == FAIL
        assert str(venv_bin / "bst") in finding["summary"]
        assert "activate" in finding["remedy"]
        assert "pip install" not in finding["remedy"], (
            "telling a user to install what is already beside the binary "
            "they just ran is how a diagnostic loses its reader")

    def test_with_no_bst_anywhere_the_install_remedy_stands(
            self, tmp_path, monkeypatch):
        import tools.bga_doctor as doctor

        monkeypatch.setattr(doctor.sys, "executable", str(tmp_path / "python3"))
        monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

        finding = doctor.check_bst()

        assert finding["status"] == FAIL
        assert "pip install" in finding["remedy"]
