"""UX-1373: `BGA_HOOK=source` (default) builds the pure wheel that compiles its hook at capture time;
`BGA_HOOK=prebuilt` builds a `py3-none-<platform>` wheel carrying the hook and spine compiled here."""

import importlib.util
import os

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution as _Distribution

MODES = ("source", "prebuilt")
MODE = os.environ.get("BGA_HOOK", "source")
if MODE not in MODES:
    raise SystemExit(f"BGA_HOOK={MODE!r}: expected one of {', '.join(MODES)}")
ROOT = os.path.dirname(os.path.abspath(__file__))


def _prebuilt_module():
    # By path: an isolated build has neither the package nor its dependencies.
    spec = importlib.util.spec_from_file_location(
        "_bga_prebuilt", os.path.join(ROOT, "tools", "native_trace", "prebuilt.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildPy(build_py):
    def run(self):
        super().run()
        if MODE == "prebuilt":
            dest = os.path.join(self.build_lib, "bga", "_tools", "native_trace", "prebuilt")
            prebuilt = _prebuilt_module()
            cc, reason = prebuilt.compiler()
            if cc is None:
                raise SystemExit(f"BGA_HOOK=prebuilt: {reason}")
            prebuilt.build(dest, cc)


class Distribution(_Distribution):
    def has_ext_modules(self):
        # Native files go to platlib and the wheel stops being pure.
        return MODE == "prebuilt"


class BdistWheel(bdist_wheel):
    def get_tag(self):
        python, abi, plat = super().get_tag()
        # Native code, but no Python ABI: one wheel per machine serves every supported Python.
        return ("py3", "none", plat) if MODE == "prebuilt" else (python, abi, plat)


setup(distclass=Distribution, cmdclass={"build_py": BuildPy, "bdist_wheel": BdistWheel})
