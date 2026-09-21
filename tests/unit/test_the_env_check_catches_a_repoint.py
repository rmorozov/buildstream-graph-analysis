"""UX-887/889: `dev_env_check`'s decisions - a worktree-repointed `bga`
(round 109), and a binary on PATH that is not the pinned one. `UX-887`
guarded ruff alone; `UX-889` added pyright (a live 1.1.408-over-1.1.414
shadow the ruff-only check passed) and node (absent, and off the
declared major). The functions are pure, so this guards the logic
without a broken environment; `main`'s I/O is the thin shell around
them."""
import pathlib

from tools.dev_env_check import (
    TOOLS,
    bga_install_ok,
    node_major,
    pinned_version,
    reported_version,
    version_ok,
)

REPO = "/home/user/buildstream-graph-analysis"

#: `requirements.lock`'s real shape: a pin at column 0, its `# via`
#: provenance indented under it, the whole file alphabetical. Two lines
#: here are the population this file exists for. `nodeenv`'s
#: `# via pyright` names a tool and pins nothing. `pytest-ruff` is a
#: real PyPI package whose name **ends** in one - so an unanchored
#: `ruff==` matches inside it, and alphabetical order puts it first.
LOCK = """\
nodeenv==1.10.0
    # via pyright
pyright==1.1.414
    # via bga (pyproject.toml)
pytest-ruff==0.5.0
    # via bga (pyproject.toml)
ruff==0.16.7
    # via bga (pyproject.toml)
typing-extensions==4.16.0
    # via
    #   pymarkdownlnt
    #   pyright
"""

#: What `pyright --version` really prints on a box whose PATH pyright
#: is behind the pin. The warning line names `pyright` and then a word,
#: so the naive `pyright\s+(\S+)` answers `version`. Two things stop
#: that - the line anchor and the leading `\d` - and this file reddens
#: when both go, not when either does; said here because a reader who
#: drops one and stays green would otherwise think it guarded neither.
PYRIGHT_OUT = """\
WARNING: there is a new pyright version available (v1.1.408 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

pyright 1.1.408
"""


class TestThePinIsReadFromTheLockfile:
    def test_it_reads_the_ruff_pin_and_not_pytest_ruffs(self):
        """`pytest-ruff==0.5.0` sorts above `ruff==0.16.7` and contains
        it. An unanchored read answers 0.5.0 and the check then passes
        a stale ruff for a pinned one, which is the whole failure this
        module was built to catch."""
        assert pinned_version(LOCK, "ruff") == "0.16.7"

    def test_it_reads_the_pyright_pin(self):
        assert pinned_version(LOCK, "pyright") == "1.1.414"

    def test_a_via_line_naming_the_tool_pins_nothing(self):
        """`    # via pyright` is indented and has no `==`. A pattern
        that is not anchored to the line start reads the tool's name out
        of another package's provenance and answers with that package's
        version."""
        assert pinned_version("nodeenv==1.10.0\n    # via pyright\n",
                              "pyright") is None

    def test_no_line_for_the_tool_is_none(self):
        assert pinned_version("anyio==4.0\nsix==1.16\n", "ruff") is None

    def test_no_lockfile_at_all_is_none(self):
        assert pinned_version("", "ruff") is None
        assert pinned_version(None, "ruff") is None


class TestTheVersionOnPathIsRead:
    def test_it_reads_ruffs_answer(self):
        assert reported_version("ruff 0.16.7\n", "ruff") == "0.16.7"

    def test_it_reads_pyrights_answer_past_its_own_warning(self):
        """The UX-889 trap: the warning line comes first and says
        "new pyright version available", and the version it names there
        is the pinned one - so a read that takes it answers `1.1.414`
        for a box running `1.1.408` and the check goes green on exactly
        the machine it was added for."""
        assert reported_version(PYRIGHT_OUT, "pyright") == "1.1.408"

    def test_a_missing_binary_answers_nothing(self):
        assert reported_version(None, "ruff") is None
        assert reported_version("", "ruff") is None


class TestTheNodeMajorIsOneReadingOfBothSides:
    def test_the_pin_file_is_a_bare_major(self):
        assert node_major("22\n") == "22"

    def test_nodes_own_answer_is_a_v_triple(self):
        assert node_major("v22.22.2\n") == "22"

    def test_a_pin_file_written_as_a_triple_still_reads_the_major(self):
        assert node_major("v20.20.2\n") == "20"

    def test_an_absent_node_is_none(self):
        assert node_major(None) is None
        assert node_major("") is None


class TestTheBgaInstallIsUnderTheMainCheckout:
    def test_a_path_under_the_checkout_is_ok(self):
        assert bga_install_ok(f"{REPO}/bga/__init__.py", REPO)

    def test_a_worktree_path_is_the_round_109_repoint(self):
        # the shared editable install repointed at a linked worktree
        wt = f"{REPO}/.claude/worktrees/agent-abc/bga/__init__.py"
        assert not bga_install_ok(wt, REPO)

    def test_a_path_outside_the_checkout_is_rejected(self):
        assert not bga_install_ok("/usr/lib/python3/site-packages/bga/__init__.py", REPO)

    def test_a_missing_import_is_rejected(self):
        assert not bga_install_ok(None, REPO)
        assert not bga_install_ok("", REPO)


class TestWhatPathAnswersIsWhatIsPinned:
    def test_the_pinned_version_passes(self):
        assert version_ok("0.16.7", "0.16.7")

    def test_the_shadowed_stale_ruff_is_caught(self):
        # /root/.local/bin/ruff 0.15.8 shadowing the pinned /usr/local one
        assert not version_ok("0.15.8", "0.16.7")

    def test_the_shadowed_stale_pyright_is_caught(self):
        # measured on the dev container this round, and green before it
        assert not version_ok("1.1.408", "1.1.414")

    def test_the_wrong_node_major_is_caught(self):
        assert not version_ok("20", "22")

    def test_a_missing_version_either_side_is_rejected(self):
        assert not version_ok(None, "0.16.7")
        assert not version_ok("0.16.7", None)


class TestEveryCheckedBinaryHasAPinToCheckAgainst:
    """A row whose pin file is not in the tree reports `None` against
    `None` forever, which `version_ok` rejects - but a row added with a
    typo'd path would then be red for the wrong reason, and a reader
    would chase the binary instead of the path."""

    def test_the_population_is_the_three_binaries(self):
        assert sorted(TOOLS) == ["node", "pyright", "ruff"]

    def test_each_row_reads_a_file_that_is_here(self):
        missing = [t for t, c in TOOLS.items() if not c.source.is_file()]
        assert missing == [], f"pin file(s) not in the tree: {missing}"

    def test_each_row_reads_a_real_pin_out_of_its_own_file(self):
        """Not that the file exists - that the reading finds something
        in it. A pin file can be present and say nothing about the tool,
        which is the cheaper question this repository calls a proxy."""
        blank = [t for t, c in TOOLS.items()
                 if not c.pin(pathlib.Path(c.source).read_text())]
        assert blank == [], f"row(s) whose pin file carries no pin: {blank}"
