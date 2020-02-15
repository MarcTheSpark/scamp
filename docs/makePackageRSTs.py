import pkgutil
import importlib


template = """{package_name} package
==============================================

.. automodule:: {package_name}
   :members:
   :undoc-members:
   :show-inheritance:


.. rubric:: Modules:

.. autosummary::
   :template: autosummary/module.rst
   :toctree: {package_name}

{module_names}
"""


packages = ["scamp", "clockblocks", "expenvelope", "pymusicxml"]

for package_name in packages:
    package = importlib.import_module(package_name)

    module_names = ""
    for module in pkgutil.iter_modules(package.__path__):
        # skip protected modules and subpackages (for now, the only sub-package is "thirdparty")
        if not module.name.startswith("_") and not module.ispkg:
            module_names += "   {}.{}\n".format(package_name, module.name)

    with open(package_name + ".rst", "w") as file:
        file.write(template.format(package_name=package_name, module_names=module_names))
