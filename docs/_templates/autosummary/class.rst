{{ fullname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :inherited-members:
   :undoc-members:


   {% block methods %}
   {% if methods %}

   {% if methods | reject('equalto', '__init__') | difference(inherited_members) %}
   .. rubric:: Methods
   .. autosummary::
   {% endif %}

   {% for item in methods | reject('equalto', '__init__') | difference(inherited_members) %}
      ~{{ name }}.{{ item }}
   {%- endfor %}

   {% if methods | reject('equalto', '__init__') | intersect(inherited_members) %}
   .. rubric:: Inherited Methods
   .. autosummary::
   {% endif %}

   {% for item in methods | reject('equalto', '__init__') | intersect(inherited_members) %}
      ~{{ name }}.{{ item }}
   {%- endfor %}

   {% endif %}
   {% endblock %}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: Attributes

   .. autosummary::
   {% for item in attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}
