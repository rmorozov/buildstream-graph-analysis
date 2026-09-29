"""UX-1131: `contracts.printable()` is exactly the set `bga --schema` prints.

Every real subcommand (and each of its flags) is asked `--schema`; the
ids that come back are the printable set, and a schema name none of them
prints is refused.
"""

import argparse
import json

from bga import cli, contracts, schemas


def _asked():
    """Every (command, flag) pair the real parser offers, flag-less first."""
    subparsers = next(a for a in cli.create_parser()._actions if isinstance(a, argparse._SubParsersAction))
    asked = []
    for command, sub in subparsers.choices.items():
        asked.append([command])
        asked += [[command, opt] for a in sub._actions for opt in a.option_strings if opt.startswith("--")]
    # `snapshot` is an alias attached outside the parser (`UX-67`), so it is named here.
    return asked + [["snapshot"], *[["snapshot", f] for f in ("--aggregate", "--capacity", "--list")]]


def _printed(capsys):
    printed = set()
    for argv in _asked():
        capsys.readouterr()
        if cli._maybe_print_schema([*argv, "--schema"]) == 0:
            printed.add(json.loads(capsys.readouterr().out)["properties"]["schema"]["const"])
    return printed


def test_every_printable_member_prints_and_nothing_else_does(capsys):
    assert _printed(capsys) == set(contracts.printable())


def test_every_other_schema_name_is_refused(capsys):
    printed = _printed(capsys)
    refused = set(schemas.names()) - set(contracts.printable())
    assert refused, "every schema name prints; the refusal half checks nothing"
    assert not refused & printed
