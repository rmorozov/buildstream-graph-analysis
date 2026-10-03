"""UX-1301: `bga capture run --help` names every flag `bga/cli.py`'s
`_translate_capture_*` functions strip before the tracer's argparse,
`--jobserver`'s `auto|N|off`, and `--jobserver-auth`'s `auto` as
`jobserver_auth_style` resolves it."""

import contextlib
import inspect
import io
import re

import pytest

from bga import cli
from tools.jobserver.ledger import jobserver_auth_style


def _translated_flags() -> set:
    flags = set()
    for name, fn in inspect.getmembers(cli, inspect.isfunction):
        if name.startswith('_translate_capture_'):
            flags |= set(re.findall(r"tok == '(--[a-z-]+)'", inspect.getsource(fn)))
    return flags


def _capture_run_help() -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), pytest.raises(SystemExit):
        cli.main(['capture', 'run', '--help'])
    return ' '.join(out.getvalue().split())


def test_the_translators_are_read():
    assert {'--jobserver', '--jobserver-auth-override', '--lto-cap', '--wrapper-dir'} <= _translated_flags()


def test_every_translated_flag_is_in_the_help():
    rendered = _capture_run_help()
    missing = sorted(f for f in _translated_flags() if not re.search(re.escape(f) + r'(?![a-z-])', rendered))
    assert not missing, f'`bga capture run --help` does not list {missing}'


def test_the_jobserver_line_shows_auto_n_off():
    assert 'auto|N|off' in _capture_run_help()


def test_the_auth_help_says_what_auto_resolves_to():
    assert f'auto resolves to {jobserver_auth_style("auto")}' in _capture_run_help()


def test_a_help_after_the_separator_is_the_wrapped_command_s():
    assert not cli._asks_capture_run_help(['capture', 'run', '.', 'r.json', '--', 'bst', '--help'])
