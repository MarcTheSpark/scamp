{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :inherited-members:
   :undoc-members:

   {# autodoc drops ":meta private:" members from the body; reject_meta_private does the same for the
      summary tables below, which autosummary builds from its own introspection. #}

   {% block methods %}
   {% if methods %}
   {% set shown_methods = methods | reject_meta_private(fullname) | reject('equalto', '__init__') | list %}

   {% if shown_methods | difference(inherited_members) %}
   .. rubric:: Methods
   .. autosummary::
   {% endif %}

   {% for item in shown_methods | difference(inherited_members) %}
      ~{{ name }}.{{ item }}
   {%- endfor %}

   {% if shown_methods | intersect(inherited_members) %}
   .. rubric:: Inherited Methods
   .. autosummary::
   {% endif %}

   {% for item in shown_methods | intersect(inherited_members) %}
      ~{{ name }}.{{ item }}
   {%- endfor %}

   {% endif %}
   {% endblock %}

   {% block attributes %}
   {% set shown_attributes = attributes | reject_meta_private(fullname) | list %}
   {% if shown_attributes %}
   .. rubric:: Attributes

   .. autosummary::
   {% for item in shown_attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}
