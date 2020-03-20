import setuptools
import os
from types import SimpleNamespace

# load _package_info.py into a SimpleNamespace, without having to import the whole scamp package
# (this is similar to the way abjad handles things)
package_info_file_path = os.path.join(os.path.dirname(__file__), "scamp", "_package_info.py")
with open(package_info_file_path, "r") as f:
    file_contents_string = f.read()
package_info_dict: dict = {}
exec(file_contents_string, None, package_info_dict)
package_info = SimpleNamespace(**package_info_dict)


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=package_info.name,
    version=package_info.version,
    author=package_info.author,
    author_email=package_info.author_email,
    description=package_info.description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=package_info.url,
    project_urls=package_info.project_urls,
    packages=setuptools.find_packages(),
    install_requires=package_info.install_requires,
    extras_require=package_info.extras_require,
    package_data=package_info.package_data,
    classifiers=package_info.classifiers,
)
