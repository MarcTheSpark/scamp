#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #
#  This file is part of SCAMP (Suite for Computer-Assisted Music in Python)                      #
#  Copyright © 2020 Marc Evanstein <marc@marcevanstein.com>.                                     #
#                                                                                                #
#  This program is free software: you can redistribute it and/or modify it under the terms of    #
#  the GNU General Public License as published by the Free Software Foundation, either version   #
#  3 of the License, or (at your option) any later version.                                      #
#                                                                                                #
#  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;     #
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.     #
#  See the GNU General Public License for more details.                                          #
#                                                                                                #
#  You should have received a copy of the GNU General Public License along with this program.    #
#  If not, see <http://www.gnu.org/licenses/>.                                                   #
#  ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++  #

import pkgutil
import importlib
import inspect
from types import ModuleType


template = """{package_name} package
==============================================

.. automodule:: {package_name}
   :members:
   :undoc-members:
   :show-inheritance:

{subpackages}
{modules}
{api}
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

api_template = """.. rubric:: Public-Facing API (result of `import *`):

.. autosummary::

{api_names}"""

packages = ["scamp", "clockblocks", "expenvelope", "pymusicxml", "scamp_extensions"]

# these are here, because some extension modules are actually just re-imports of protected scamp modules
# so when we inspect the import path of the objects they lead to the wrong place
api_name_path_replacements = {
    "scamp._metric_structure.MeterArithmeticGroup": "scamp_extensions.rhythm.metric_structure.MeterArithmeticGroup",
    "scamp._metric_structure.MetricStructure": "scamp_extensions.rhythm.metric_structure.MetricStructure",
}


for package_name in packages:
    package = importlib.import_module(package_name)

    module_names = ""
    sub_package_names = ""
    api_names = ""

    for module_or_subpackage in pkgutil.iter_modules(package.__path__):
        # skip protected modules and subpackages (for now, the only sub-package is "_thirdparty")
        if not module_or_subpackage.name.startswith("_"):
            if module_or_subpackage.ispkg:
                sub_package_names += "   {}.{}\n".format(package_name, module_or_subpackage.name)
                packages.append("{}.{}".format(package_name, module_or_subpackage.name))
            else:
                module_names += "   {}.{}\n".format(package_name, module_or_subpackage.name)

    api_name_paths = []
    for x in package.__dict__:
        if not x.startswith("_"):
            if inspect.getmodule(package.__dict__[x]) and not isinstance(package.__dict__[x], ModuleType):
                api_name_path = inspect.getmodule(package.__dict__[x]).__name__ + "." + x
                if api_name_path in api_name_path_replacements:
                    api_name_path = api_name_path_replacements[api_name_path]
                api_name_paths.append(api_name_path)
    if len(api_name_paths) > 0:
        api_name_paths.sort()
        api_names = "   ~" + "\n   ~".join(x for x in api_name_paths)

    modules_string = modules_template.format(package_name=package_name, module_names=module_names) \
        if len(module_names) > 0 else ""
    subpackages_string = subpackages_template.format(package_name=package_name, subpackage_names=sub_package_names) \
        if len(sub_package_names) > 0 else ""
    api_string = api_template.format(api_names=api_names) if len(api_names) > 0 else ""

    with open(package_name + ".rst", "w") as file:
        file.write(
            template.format(package_name=package_name, subpackages=subpackages_string,
                            modules=modules_string, api=api_string)
        )
