# Round 171 - the Python 3.9 floor installs and passes again, UX-1335

Run on 2026-10-03 by the merge-steward thread, no agents launched. Main's
`test (3.9)` cell had failed at install on every merge from `057bc920` to
`19f1fd73`; Ruslan chose to keep the floor.

```text
closed   UX-1335
local    make test on Python 3.9.23: 12330 passed, 216 skipped
```

## What closed

| row | close |
|---|---|
| `UX-1335` | hypothesis pinned per Python; `zip(strict=)` out of three test files; `test_every_dev_pin_installs_on_the_python_floor.py` and a `zip` clause in `test_the_package_runs_on_the_python_it_claims.py` |
