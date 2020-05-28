{{ fullname | escape | underline }}

.. currentmodule:: {{ fullname }}

.. automodule:: {{ fullname }}

{% set manual_classes = members | pick_classes_manually(fullname) %}
{% if classes or manual_classes %}
.. rubric:: Classes

.. autosummary::
    :toctree: .
    {% for class in classes %}
    {{ class }}
    {% endfor %}
    {% for function in manual_classes %}
    {{ function }}
    {% endfor %}
{% endif %}

{% set manual_functions = members | pick_functions_manually(fullname) %}
{% if functions or manual_functions %}
.. rubric:: Functions

.. autosummary::
    :toctree: .
    {% for function in functions %}
    {{ function }}
    {% endfor %}
    {% for function in manual_functions %}
    {{ function }}
    {% endfor %}
{% endif %}

{% set attributes = members | pick_attributes_manually(fullname) %}
{% if attributes %}
.. rubric:: Attributes

.. autosummary::
{% for item in attributes %}
  ~{{ fullname }}.{{ item }}
{%- endfor %}
{% endif %}

{% if exceptions %}
.. rubric:: Exceptions

.. autosummary::
{% for item in exceptions %}
  ~{{ fullname }}.{{ item }}
{%- endfor %}
{% endif %}