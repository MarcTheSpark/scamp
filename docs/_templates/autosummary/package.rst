{{ fullname | escape | underline}}

{% if modules %}
.. rubric:: Modules

.. autosummary::
    :toctree: .
    {% for module in modules %}
    {{ module }}
    {% endfor %}

{% endif %}



