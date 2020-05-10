import pkgutil
import importlib


template = """{package_name} package
==============================================

.. automodule:: {package_name}
   :members:
   :undoc-members:
   :show-inheritance:

{subpackages}

{modules}
"""

subpackages_template = """.. rubric:: Sub-packages:

.. autosummary::
   
{subpackage_names}

.. toctree::
   :hidden:
   
{subpackage_names}
"""

modules_template = """.. rubric:: Modules:

.. autosummary::
   :template: autosummary/module.rst
   :toctree: {package_name}

{module_names}"""

packages = ["scamp", "clockblocks", "expenvelope", "pymusicxml", "scamp_extensions"]

for package_name in packages:
    package = importlib.import_module(package_name)

    module_names = ""
    sub_package_names = ""
    for module in pkgutil.iter_modules(package.__path__):
        # skip protected modules and subpackages (for now, the only sub-package is "_thirdparty")
        if not module.name.startswith("_"):
            if module.ispkg:
                sub_package_names += "   {}.{}\n".format(package_name, module.name)
                packages.append("{}.{}".format(package_name, module.name))
            else:
                module_names += "   {}.{}\n".format(package_name, module.name)

    modules_string = modules_template.format(package_name=package_name, module_names=module_names) \
        if len(module_names) > 0 else ""
    subpackages_string = subpackages_template.format(package_name=package_name, subpackage_names=sub_package_names) \
        if len(sub_package_names) > 0 else ""

    with open(package_name + ".rst", "w") as file:
        file.write(
            template.format(package_name=package_name, subpackages=subpackages_string, modules=modules_string)
        )
