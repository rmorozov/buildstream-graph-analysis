# UX-703: the weekly mutation ledger

One section per run. A survivor is a filing, not a failure - see the
task file for the loop that produces this.

No run has landed yet: the header is committed because
`tools/dev_mutation.py --help` names this path, and a sentence the
tool prints is a contract (`UX-326`). `write_ledger` appends a dated
section per run and creates this header only when it is absent, so the
first weekly run adds rows below rather than rewriting anything above.
