"""
Minimal setup.py that exists solely to make setuptools tag built wheels as
platform-specific (e.g. cp312-cp312-macosx_11_0_arm64) instead of pure-Python
(py3-none-any).

scamp contains no C extensions, but its wheels bundle native FluidSynth
libraries that are arch/OS-specific. setuptools decides purity by checking
``Distribution.has_ext_modules()``; overriding that to return True forces
platform tags without us actually compiling anything.

All real package configuration lives in pyproject.toml.
"""

from setuptools import setup
from setuptools.dist import Distribution


class BinaryDistribution(Distribution):
    def has_ext_modules(self):
        return True


setup(distclass=BinaryDistribution)
