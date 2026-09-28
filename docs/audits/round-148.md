# Round 148 — the #298 re-review's third pass closes

Run on 2026-09-28 in answer to the owner's third #298 review at
`76f2179e`. One track, UX-1088 then UX-1089, filed and fixed together
and landed as `1a498516`, linear on the pushed round 147 head.

```text
closed   UX-1088 UX-1089 UX-1105
index    dev_close_task.py --counts: 1038 scenarios, 22 open, 1016 closed
spread   dev_touching.py --spread: 33-173 of 663 test files
```

## Findings fixed

- UX-1088: `_value`'s digit branch pseudonymized any unrecognized
  numeric value by default, so `--otp=123456`/`--pin=1234` still
  landed reversibly in `PseudonymMap` even though the archive dropped
  them. `otp`/`pin`/`passcode`/`mfa`/`totp` join `_CREDENTIAL_NAME`,
  and an unsafe (binary, option) pair now drops to `<dropped>` like
  any named credential; a safe pair (`make -j8`, `gcc -O2`,
  `-DCMAKE_BUILD_PARALLEL_LEVEL=8`) is unaffected.
- UX-1089: the glued `-j<digits>` shortcut matched on any `argv[0]`,
  ahead of the make-like binary check UX-1084 already keyed the other
  forms on, so `curl -j123456` kept six digits verbatim. It now routes
  through the same `binary in _MAKE_LIKE_BINARIES` check as the
  space-separated and assigned forms; off one it falls to UX-1088's
  default-drop path. `-O\d` and `-l` were audited and already keyed;
  `g[0-3]?` is a bounded enum needing no key.

## The tier gate

- #298's CI tier gate went red on `test_the_page_conforms_to_its_sections.py` (14.5s, 16.4s against 7.4s): `--dist load` split it, rebuilding its page fixture per worker.
- UX-1105 builds it once per session under an `fcntl` lock with its two probes overlapped (file alone 27.9s -> 14.7-17.2s); `--dist loadgroup` was rejected at 515s -> 774s full suite.

## Verification

A verifier ran on `1a498516` and found one leak: a single-dash flag
glued to `=` (`-j=123456`) bypassed both paths, fixed in `05fe2c74`.

## Suite

Full `make test` on `1a498516`: 10241 passed / 199 skipped / 0 failed.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| implementer | sonnet | UX-1088+UX-1089, the #298 review's two remaining numeric-leak findings (filed and fixed, one track) | 144356 | — | — | no separate verifier; the session probed the leaks itself |
| closer | sonnet | close: row moves, ledger, round document | unknown | — | — | — |
