"""UX-321: one gate for the optional reader, asked in one place.

`test_the_real_reader_agrees.py` honoured `BGA_TRACE_PROCESSOR` and
`test_the_perfetto_handoff.py` did not, so a machine with the binary in
an unusual place ran half the clauses that could have run and skipped
the other half - and the skip census counted the skip as if the tool
were absent.

The reason string is one string for the same reason: the census counts
by reason, and a second wording for "the same optional tool is absent"
would split one family into two for no gain.
"""
import os
import shutil

#: Where a reader who hits the skip finds out what to install.
REASON = "trace_processor_shell is not installed"


def shell():
    """The binary, or `None`.

    `BGA_TRACE_PROCESSOR` wins, so a runner with Perfetto unpacked
    somewhere unusual can say where; `PATH` is the fallback.
    """
    named = os.environ.get("BGA_TRACE_PROCESSOR")
    if named and os.path.isfile(named) and os.access(named, os.X_OK):
        return named
    return shutil.which("trace_processor_shell")
