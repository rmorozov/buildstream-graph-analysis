"""UX-1329: `bga --help` opens with the three first commands, and the README's
install line installs bga's checkout from beside the user's project."""

import pathlib
import re
import subprocess
import sys

from bga import tools_dispatch

REPO = pathlib.Path(__file__).resolve().parents[2]


def _help():
    out = subprocess.run([sys.executable, "-m", "bga.cli", "--help"], capture_output=True, text=True, cwd=REPO)
    assert out.returncode == 0, out.stderr
    return out.stdout


class TestHelpOpensWithTheFirstCommands:
    def test_the_three_commands_come_first_in_order(self):
        text = _help()
        block = text.split("Start here:", 1)[1].split("\n\n", 1)[0]

        positions = [block.index(c) for c in ("bga doctor .", "bga snapshot -- bst build TARGET", "bga view")]
        assert positions == sorted(positions)
        assert text.index("Start here:") < text.index("positional arguments:")

    def test_release_notes_is_not_among_the_user_commands_and_still_runs(self):
        text = _help()
        user, maintainer = text.split("maintainer tools", 1)

        assert "release-notes" not in user
        assert "release-notes" in maintainer
        assert "release-notes" in tools_dispatch.TOOL_ALIASES


class TestTheReadmeInstallsTheCheckoutFromBesideTheProject:
    def test_the_real_project_install_line_matches_the_clone(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        section = readme.split("## Use it on your real project", 1)[1].split("\n## ", 1)[0]
        [line] = [ln for ln in section.splitlines() if ln.startswith("pip install")]

        assert line.startswith('pip install "./buildstream-graph-analysis[bst]"')
        assert "-e" not in line.split("#")[0].split()

    def test_no_readme_line_installs_the_users_directory_with_the_bst_extra(self):
        readme = (REPO / "README.md").read_text(encoding="utf-8")

        assert not re.search(r'pip install -e "\.\[bst\]"', readme)
