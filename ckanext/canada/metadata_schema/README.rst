metadata_schema
---------------

The old GoC Metadata Schema is available within the plugin by importing::

   from ckanext.canada.metadata_schema import schema_description

It is also available within the jinja2 templates as the variable
``schema_description``.

The ``schema_description`` object contains attributes:

``dataset_fields``
  an ordered list of `descriptions <#field-descriptions>`_ of fields
  available in a dataset

``resource_fields``
  an ordered list of `descriptions <#field-descriptions>`_ of fields
  available in each resource in a dataset

``dataset_sections``
  a list of dataset fields grouped into sections, dicts with ``'name'``
  and ``'fields'`` keys, currently used to separate fields across the
  dataset creation pages and group the geo fields together

``dataset_field_by_id``
  a dict mapping dataset field ids to their
  `descriptions <#field-descriptions>`_

``resource_field_by_id``
  a dict mapping resource field ids to their
  `descriptions <#field-descriptions>`_

``dataset_field_iter(include_existing=True, section=None)``
  returns a generator of (field id, language, field description) tuples
  where field ids generated includes ``*_fra`` fields.  both French
  and English versions of a field point use the same
  `field description <#field-descriptions>`_.
  language is ``'eng'``, ``'fra'`` or ``None`` for fields without
  separate language versions.
  ``include_existing=False`` would *exclude* standard CKAN fields and
  ``section`` may be used to limith the fields to the passed dataset
  section.

``resource_field_iter(include_existing=True)``
  returns a generator of (field id, language, field description) tuples
  where field ids generated includes ``*_fra`` fields.  both French
  and English versions of a field point use the same
  `field description <#field-descriptions>`_.
  language is ``'eng'``, ``'fra'`` or ``None`` for fields without
  separate language versions.
  ``include_existing=False`` would *exclude* standard CKAN fields.

``languages``
  ``['eng', 'fra']``, useful for keeping literal ``eng`` and ``fra``
  strings out of the source code

``vocabularies``
  a dict mapping CKAN tag vocabulary ids to their corresponding dataset
  field ids



