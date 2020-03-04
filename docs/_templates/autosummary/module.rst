{{ fullname | escape | underline }}

.. currentmodule:: {{ fullname }}

.. automodule:: {{ fullname }}

{% if classes %}
.. rubric:: Classes

.. autosummary::
    :toctree: .
    {% for class in classes %}
    {{ class }}
    {% endfor %}

{% endif %}

{% if functions %}
.. rubric:: Functions

.. autosummary::
    :toctree: .
    {% for function in functions %}
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