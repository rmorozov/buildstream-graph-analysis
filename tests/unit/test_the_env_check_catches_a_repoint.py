"""UX-887: `dev_env_check`'s decisions - a worktree-repointed `bga`
(round 109) and a shadowed non-pinned `ruff` (a UX-882 near-miss) are
each caught. The functions are pure, so this guards the logic without a
broken environment; `main`'s I/O (subprocess `ruff`, a fresh `import
bga`) is the thin shell around them."""
from tools.dev_env_check import (
    bga_install_ok,
    pinned_ruff_version,
    ruff_version_ok,
)

REPO = "/home/user/buildstream-graph-analysis"


class TestThePinnedRuffIsRead:
    def test_it_reads_the_ruff_pin_from_a_lockfile(self):
        assert pinned_ruff_version("anyio==4.0\nruff==0.16.7\nsix==1.16\n") == "0.16.7"

    def test_no_ruff_line_is_none(self):
        assert pinned_ruff_version("anyio==4.0\nsix==1.16\n") is None


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


class TestTheRuffOnPathIsPinned:
    def test_the_pinned_version_passes(self):
        assert ruff_version_ok("0.16.7", "0.16.7")

    def test_the_shadowed_stale_ruff_is_caught(self):
        # /root/.local/bin/ruff 0.15.8 shadowing the pinned /usr/local one
        assert not ruff_version_ok("0.15.8", "0.16.7")

    def test_a_missing_version_either_side_is_rejected(self):
        assert not ruff_version_ok(None, "0.16.7")
        assert not ruff_version_ok("0.16.7", None)
