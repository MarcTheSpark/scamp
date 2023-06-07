# -*- coding: utf-8 -*-

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

#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, '/home/marc/Nextcloud/Programming/PycharmProjects/scamp/scamp')

import scamp
import sphinx_rtd_theme
import datetime
import re


##################################################################################################################
#                            Hack to add intersect and difference filters in templates
##################################################################################################################

import jinja2


def intersect(a, b):
    return [x for x in a if x in b]


def difference(a, b):
    return [x for x in a if x not in b]


jinja2.filters.FILTERS['intersect'] = intersect
jinja2.filters.FILTERS['difference'] = difference

##################################################################################################################
#                                   Hack to allow certain named module attributes
##################################################################################################################

_manually_documented_attributes = {
    'scamp.settings': {"playback_settings", "quantization_settings", "engraving_settings"},
    'clockblocks.settings': {'running_behind_warning_threshold_long', 'running_behind_warning_threshold_short',
                             'catching_up_child_clocks_threshold_min', 'catching_up_child_clocks_threshold_max'}
}

_manually_documented_functions = {
    'scamp_extensions.utilities.math': {
        "gcd", "is_x_pow_of_y", "floor_x_to_pow_of_y", "ceil_x_to_pow_of_y", "round_x_to_pow_of_y", "floor_to_multiple",
        "ceil_to_multiple", "round_to_multiple", "is_multiple", "prime_factor", "is_prime"
    },
    'scamp_extensions.utilities.sequences': {"make_flat_list", "sum_nested_list"},
    'scamp_extensions.rhythm.metric_structure': {"flatten_beat_groups"}
}


_manually_documented_classes = {
    'scamp_extensions.rhythm.metric_structure': {"MetricStructure", "MeterArithmeticGroup"}
}


def pick_attributes_manually(a, module_name):
    if module_name in _manually_documented_attributes:
        return list(_manually_documented_attributes[module_name])
    else:
        return []


def pick_functions_manually(a, module_name):
    if module_name in _manually_documented_functions:
        return list(_manually_documented_functions[module_name])
    else:
        return []


def pick_classes_manually(a, module_name):
    if module_name in _manually_documented_classes:
        return list(_manually_documented_classes[module_name])
    else:
        return []


jinja2.filters.FILTERS['pick_attributes_manually'] = pick_attributes_manually
jinja2.filters.FILTERS['pick_functions_manually'] = pick_functions_manually
jinja2.filters.FILTERS['pick_classes_manually'] = pick_classes_manually

# -- Project information -----------------------------------------------------

project = "scamp"
author = scamp.__author__
copyright = '{}, {}'.format(datetime.datetime.now().year, author)

# The short X.Y version
version = scamp.__version__
# The full version, including alpha/beta/rc tags
release = scamp.__version__

# Update the version of abjad referenced in experienced_setup.rst
# to the one SCAMP currently depends on
with open("narrative/experienced_setup.rst", "r+") as f:
    data = f.read()
    f.seek(0)
    output = re.sub(r'abjad==.*', r'abjad=={}'.format(scamp._dependencies.ABJAD_VERSION), data)
    f.write(output)
    f.truncate()

# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx_rtd_theme',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
#
# html_sidebars = {}

html_css_files = [
    'css/custom.css',
]

html_logo = "_static/ScampLogo.svg"


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'scampdoc'
autodoc_default_options = {
    'show-inheritance': True,
}

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'scamp.tex', 'scamp Documentation',
     'Author', 'manual'),
]


# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'scamp', 'scamp Documentation',
     [author], 1)
]


# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'scamp', 'scamp Documentation',
     author, 'scamp', 'One line description of project.',
     'Miscellaneous'),
]


# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#
# epub_identifier = ''

# A unique identification for the text.
#
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']


# -- Extension configuration -------------------------------------------------

autodoc_member_order = 'bysource'
autoclass_content = 'class'
autosummary_generate = True
autosummary_generate_overwrite = False  # Doesn't seem to work?
autodoc_type_aliases = {
    'NotePropertiesCompatible': 'NotePropertiesCompatible',
    'PitchCompatible': 'PitchCompatible',
    'VolumeCompatible': 'VolumeCompatible',
    'DurationCompatible': 'DurationCompatible'
}
autodoc_typehints_format = 'short'
python_use_unqualified_type_names = True

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

