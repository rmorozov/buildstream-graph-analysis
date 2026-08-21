"""A pytest plugin that makes `jsonschema` unimportable.

`UX-197` seam 6: the guard for "the schema module goes red rather than
silent in a dev environment missing its extras" has to *be* in such an
environment. Building a venv per test run costs seconds and a network;
removing the module from `sys.modules` and refusing the import costs
neither, and reproduces the same `ImportError` the venv produced.
"""
import sys


class _Refuse:
    def find_spec(self, name, path=None, target=None):
        if name == "jsonschema" or name.startswith("jsonschema."):
            raise ImportError(f"no module named {name}")
        return None


def pytest_configure(config):
    for name in [n for n in sys.modules if n.split(".")[0] == "jsonschema"]:
        del sys.modules[name]
    sys.meta_path.insert(0, _Refuse())
