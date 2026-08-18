"""UX-84: the environment a bst-gated test hands to a real `bst`.

Every one of these tests points `bst` at a throwaway `HOME` so it uses a
fresh cache and config rather than the developer's. They did that by
building a two-key environment from scratch - `{"HOME": ..., "PATH":
...}` - which also drops everything else, and one of those droppings
matters: Python resolves the per-user `site-packages` directory *from
`HOME`*. On a machine where BuildStream was installed with
`pip install --user`, replacing `HOME` unimports half of it, and `bst`
dies at startup with `ModuleNotFoundError: No module named 'jinja2'`
before it ever reads the project.

Round 10's audit recorded four bst-gated failures. Against a clean venv
exactly one of them was real (the `cpu_accounting_available` assertion,
re-baselined in `test_bst_extract_run.py`); the rest were this, and so
were five more that the audit's own environment happened not to reach.
Nine phantom failures pointing at the tool, caused by the harness.

So: inherit the environment and override only `HOME`. The isolation is
unchanged - `HOME` is the only thing `bst` keys its cache and config off
- and a `--user` install keeps working.
"""
import os
import site
import sys
from typing import Optional


def _user_site_to_preserve() -> Optional[str]:
    """The real user `site-packages`, if this interpreter is actually
    using it.

    Inheriting the environment is not by itself enough: `HOME` is *how*
    Python finds the per-user `site-packages`, so overriding it removes
    that directory from the child's path no matter what else is
    inherited. Where an install genuinely lives there, the directory has
    to be carried across explicitly, and `PYTHONPATH` is the only channel
    that survives a changed `HOME`.

    Returns None on the common case - a venv or a system-wide install -
    so nothing is added to `PYTHONPATH` that does not need to be.
    """
    if not site.ENABLE_USER_SITE:
        return None
    try:
        user_site = site.getusersitepackages()
    except Exception:  # pragma: no cover - defensive; site is not required to work
        return None
    return user_site if user_site in sys.path and os.path.isdir(user_site) else None


def isolated_bst_env(home, **extra: Optional[str]) -> dict:
    """The parent environment with `HOME` pointed at `home`.

    `extra` overrides further keys; a value of None removes the key,
    for a test that wants to prove something is absent.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    user_site = _user_site_to_preserve()
    if user_site:
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = f"{user_site}{os.pathsep}{existing}" if existing else user_site
    for key, value in extra.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env
