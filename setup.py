"""
Minimal setup.py that customizes wheel tagging.

scamp contains no Python C extensions, but its wheels bundle native FluidSynth
libraries that are arch/OS-specific. We want wheels tagged
``py3-none-<platform>`` (one wheel per platform, works on every CPython 3.x
that meets requires-python) rather than:

  * ``py3-none-any``   — what setuptools defaults to for a pure-Python package.
                         No platform tag, so pip would happily install our
                         macOS wheel on Linux even though the bundled dylibs
                         won't run.
  * ``cp312-cp312-<plat>`` — what setuptools produces if you tell it the
                         distribution has ext modules. ABI-locked to one
                         CPython version even though our code isn't, forcing
                         us to ship N wheels per platform.

To get ``py3-none-<platform>`` we (a) override
``Distribution.has_ext_modules`` so setuptools picks a platform tag, then
(b) override ``bdist_wheel.get_tag`` to reset the python and abi tags back
to ``py3`` / ``none``.

All real package configuration lives in pyproject.toml.
"""

from setuptools import setup
from setuptools.dist import Distribution

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # setuptools >=70 vendors bdist_wheel
    from setuptools.command.bdist_wheel import bdist_wheel as _bdist_wheel


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


class bdist_wheel(_bdist_wheel):
    def get_tag(self):
        _python, _abi, plat = super().get_tag()
        return "py3", "none", plat


setup(distclass=BinaryDistribution, cmdclass={"bdist_wheel": bdist_wheel})
