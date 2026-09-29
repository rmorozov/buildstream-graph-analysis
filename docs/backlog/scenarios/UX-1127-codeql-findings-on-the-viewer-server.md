# UX-1127: the viewer's pre-flight echoes any header list, and CodeQL reads the asset path as the request's

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-198 | **Found by:** CodeQL on PR #301 (`a49e34a3`), Ruslan took it (2026-09-29 08:51) | **Serves:** anyone running `bga view` on a shared host | **Topic:** viewer | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** test_the_perfetto_handoff.py

## Motivation

CodeQL reported four alerts once `UX-1118` reflowed the files. Two are
real. `tools/bga_view.py` echoed `Access-Control-Request-Headers`
verbatim into `Access-Control-Allow-Headers` (HTTP response splitting,
medium), and `test_the_report_you_can_attach.py` accepted any URL
*prefixed* `https://ui.perfetto.dev`, which `https://ui.perfetto.dev.example`
also is. The `_asset` path alert reads a name already on the `ASSETS`
allowlist. The `bga/blast.py` alert is a CLI argument naming the
user's own file, which is the command's purpose.

## Decomposition

Input classes: a token list, one token, a CRLF, an obs-fold continuation, a space, an empty value.
Journey: `bga view` serving a trace to Perfetto's pre-flight.

## Required Fix

Echo the header list only when it is RFC 9110 tokens and commas; open
an asset through a table keyed by `ASSETS`; match the Perfetto URL by
scheme and host.

## Out of Scope

`bga/blast.py`'s `os.path.exists` on the user's target: intended, and
dismissed on the alert rather than coded around.

## Acceptance Test

A token list is echoed; a CRLF, an obs-fold, a space or an empty value
is not; the handler asks the pattern before it echoes.

## Outcome

Gap measured: CodeQL on `a49e34a3`, 4 alerts (3 high, 1 medium):
`bga/blast.py:124`, `tools/bga_view.py:1815` (path), `tools/bga_view.py:1690`
(response splitting), `test_the_report_you_can_attach.py:1207` (URL substring).

Close measured: `test_the_perfetto_handoff.py` and
`test_the_report_you_can_attach.py`, 105 passed, 1 skipped; the new class,
9 passed. `dev_sizes.py --adopt --force`: `tools/bga_view.py` file_lines
2196 -> 2200.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| the echo drops `_HEADER_LIST.fullmatch(asked)` | `test_the_perfetto_handoff.py` | 1 failed / 9 |
| `_HEADER_LIST` = `.+` | same | 4 failed / 9 |

Deviation: the `blast.py` alert stays for a dismissal, not a fix.
