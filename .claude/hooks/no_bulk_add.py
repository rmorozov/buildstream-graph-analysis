"""Decide whether a Bash payload really runs a bulk `git add`.

`UX-424`. The first version of this control matched the command's
**text** with a regex, and a text scan cannot tell a command from a
mention of one. It blocked its own commit three times in round 67,
because a commit message quoting the rule is still a string containing
the rule. Measured on the fourteen payloads in
`tests/unit/test_the_agent_configuration_holds.py`, the regex was wrong
on prose after a semicolon inside a heredoc, and on the pattern sitting
inside a single-quoted argument - the shape that blocked the probe
written to measure it.

The fix is the one `UX-403` used for the same defect one file over:
**tokenise, do not lengthen the regex.** A longer pattern chases an
unbounded class of confusions; a token stream simply does not have
them. Heredoc bodies are dropped, then `shlex` splits the rest with
shell quoting rules, and a match counts only where `git` stands in
**command position** - first token, or straight after a separator.

Two directions were considered and rejected:

- Stripping quoted spans and re-running the regex. `git add "-A"` then
  reads as `git add` with no operand and passes, which is a real bulk
  add lost. Tokenising keeps it, because `shlex` removes the quotes and
  leaves the word.
- Accepting the false blocks and documenting them. Cheap, and it leaves
  a control whose failure mode is "the agent stops writing about the
  rule it is enforcing".

**When it cannot parse, it falls back to the raw-text regex.** An
unbalanced quote is common in a real command line, and the conservative
direction here is to block: a false block costs one retry with explicit
paths, a missed one costs a tree somebody else unpicks.
"""
import json
import re
import shlex
import sys

#: The old rule, kept for the unparseable case only. Not the decision.
FALLBACK = re.compile(r"(^|[;&|(]\s*)git\s+add\s+(-A\b|--all\b|\.(\s|$))")

#: `shlex` with `punctuation_chars` emits these as tokens of their own,
#: which is what makes "command position" computable without a shell
#: grammar. Measured, not assumed: `a && b` gives `['a', '&&', 'b']`.
#:
#: A newline is **not** among them - `shlex` treats it as whitespace,
#: so `foo\ngit add -A` would put `git` in argument position and pass.
#: `_as_one_line` substitutes it first; see there for why that is safe
#: inside a quoted string.
SEPARATORS = {";", ";;", "&&", "||", "|", "|&", "&", "(", ")"}

#: `git add` with any of these as an operand stages the whole tree.
#: Exactly the three the old regex named - `-u` stages every tracked
#: modification and is arguably a fourth, but it was never blocked and
#: adding it here would be a rule change wearing an instrument fix's
#: clothes.
BULK_WORDS = {"-A", "--all", "."}

_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def without_heredocs(command):
    """`command` with every heredoc body removed.

    A heredoc body is data being written to a file - a commit message,
    a task file, a test fixture. It is the single largest source of
    false blocks, because this repository's commit messages quote the
    rules they are enforcing.
    """
    out, pending, lines = [], None, command.split("\n")
    for line in lines:
        if pending is not None:
            if line.strip() == pending:
                pending = None
            continue
        out.append(line)
        # Only the last heredoc on a line matters for the terminator we
        # wait on; multiple redirections on one line are rare enough
        # that the fallback covers them.
        found = _HEREDOC.findall(line)
        if found:
            pending = found[-1][1]
    return "\n".join(out)


def _as_one_line(command):
    """Newlines turned into a separator `shlex` will actually emit.

    Safe inside a quoted string: the substitution changes that string's
    *content*, which nothing here reads, and not the token structure,
    because quoting still protects the `;` from being split out. Outside
    a quoted string a newline already separates two commands, which is
    exactly what `;` means.
    """
    return command.replace("\n", " ; ")


def tokens_of(command):
    """`shlex` tokens, or None when the command will not parse."""
    lexer = shlex.shlex(_as_one_line(command), posix=True,
                        punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def is_bulk_add(command):
    """True when `command` actually runs a bulk `git add`."""
    stripped = without_heredocs(command)
    words = tokens_of(stripped)
    if words is None:
        return bool(FALLBACK.search(command))
    at_command_start = True
    for index, word in enumerate(words):
        if word in SEPARATORS:
            at_command_start = True
            continue
        if at_command_start and word == "git":
            rest = words[index + 1:]
            if rest and rest[0] == "add":
                for operand in rest[1:]:
                    if operand in SEPARATORS:
                        break
                    if operand in BULK_WORDS:
                        return True
                    # A short-flag cluster such as `-Av`, but never a
                    # path like `./bga/x.py` or a long option.
                    if (operand.startswith("-")
                            and not operand.startswith("--")
                            and "A" in operand[1:]):
                        return True
        at_command_start = False
    return False


MESSAGE = """Blocked: a bulk `git add` (fixing guide section 4a.1).

Stage the paths you changed, by name. A bulk add is how this repository
has committed scratch captures, .pyc files and half-finished fixtures -
`make check-clean` then fails on a tree somebody else has to unpick.

    git status --short      # see what is really there
    git add path/one path/two

This reads the command's tokens, not its text, so writing *about* the
rule is not blocked (UX-424). If this fired on a command that only
mentions the pattern, the parse fell back to the old regex - say so in
the task file rather than working around it.
"""


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if command and is_bulk_add(command):
        sys.stderr.write(MESSAGE)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
