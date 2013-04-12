ckanext-canada
==============

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Team: Ian Ward, Ross Thompson, Peder Jakobsen, Denis Zgonjanin

Features:

* Forms and Validation for GoC Metadata Schema (in progress)
* Batch import of data

Installation:

* Use CKAN Version: 2.0+
* After every pull or fetch, use ``python setup.py develop`` just in case entry points have changed.

From a clean database you must run::

   paster canada create-vocabularies
   paster canada create-organizations

Once to create the tag vocabularies and organizations this extension requires
before loading any data.


Plugins
-------

``canada_forms``
  dataset forms for data.gc.ca metadata schema

``canada_public``
  base and public facing data.gc.ca templates (requires
  ``canada_forms`` and ``wet_theme`` from
  `ckanext-wet-boew <https://github.com/open-data/ckanext-wet-boew>`_ )

``canada_internal``
  templates for internal site and registration (requires
  ``canada_forms`` and ``canada_public``)


Requirements
------------

.. list-table:: Related projects, repositories, branches and CKAN plugins
 :header-rows: 1

 * - Project
   - Github group/repo
   - Branch
   - Plugins
 * - CKAN
   - `open-data/ckan <https://github.com/open-data/ckan>`_
   - canada-v2.0
   - * stats
 * - Spatial extension
   - `open-data/ckanext-spatial <https://github.com/open-data/ckanext-spatial>`_
   - release-v2.0
   - * spatial_metadata
     * spatial_query
 * - data.gc.ca extension
   - `open-data/ckanext-canada <https://github.com/open-data/ckanext-canada>`_
   - master
   - * canada_forms
     * canada_internal
     * canada_public
 * - WET-BOEW theme
   - `open-data/ckanext-wet-boew <https://github.com/open-data/ckanext-wet-boew>`_
   - master
   - * wet_theme
 * - WET-BOEW
   - `open-data/wet-boew <https://github.com/open-data/wet-boew>`_
   - master
   - N/A


Loading Data
------------

These are the steps we use to import data faster during development.
Choose the ones you like, there are no dependencies.

1. use the latest version of ckan from the
   `canada-v2.0 branch <https://github.com/open-data/ckan/tree/canada-v2.0>`_
   for fixes related to importing tags (~30% faster)

2. disable solr updates while importing with the following lines in your
   development.ini (~15% faster)::

     ckan.search.automatic_indexing = false
     ckan.search.solr_commit = false

   With this change you need to remember to run
   ``paster --plugin ckan search-index rebuild`` (or ``rebuild_fast``)
   after the import, and remove the changes to development.ini.

3. Drop the indexes on the database while importing (~40% faster)

   Apply the changes in ``tuning/contraints.sql`` and
   ``tuning/what_to_alter.sql`` to your database.

4. Do the import in parallel with the load-datasets command (close to linear
   scaling until you hit cpu or disk I/O limits):

   For example load 150K records from "nrcan-1.jl" in parallel with three
   processes::

     paster canada load-datasets nrcan-1.jl 0 150000 -p 3

For UI testing, simply load the 50 test datasets from the data folder.  It contains a mixture of the latest version of assorted datasets from NRCAN and the Enviroment Canada Pilot::

   paster canada load-datasets data/sample.jl


Working with the API
--------------------

To view a raw dataset using the api, pipe your curl requests to python's mjson.tool to ensure readable formatting of the output::

  curl http://localhost:5000/api/action/package_show -d '{"id": "0007a010-556d-4f83-bb8e-6e22dcc62e84"}' |  python -mjson.tool


schema_description
------------------

The GoC Metadata Schema is available within the plugin by importing::

   from ckanext.canada.metadata_schema import schema_description

It is also available within the jinja2 templates as the variable
``schema_description``.

The ``schema_description`` object contains attributes:

``dataset_fields``
  an ordered list of [descriptions](#field-descriptions) of fields
  available in a dataset

``resource_fields``
  an ordered list of [descriptions](#field-descriptions) of fields
  available in each resource in a dataset

``dataset_sections``
  a list of dataset fields grouped into sections, dicts with ``'name'``
  and ``'fields'`` keys, currently used to separate fields across the
  dataset creation pages and group the geo fields together

``dataset_field_by_id``
  a dict mapping dataset field ids to their
  [descriptions](#field-descriptions)

``resource_field_by_id``
  a dict mapping resource field ids to their
  [descriptions](#field-descriptions)

``dataset_field_iter(include_existing=True, section=None)``
  returns a generator of (field id, language, field description) tuples
  where field ids generated includes ``*_fra`` fields.  both French
  and English versions of a field point use the same
  [field description](#field-descriptions).
  language is ``'eng'``, ``'fra'`` or ``None`` for fields without
  separate language versions.
  ``include_existing=False`` would *exclude* standard CKAN fields and
  ``section`` may be used to limith the fields to the passed dataset
  section.

``resource_field_iter(include_existing=True)``
  returns a generator of (field id, language, field description) tuples
  where field ids generated includes ``*_fra`` fields.  both French
  and English versions of a field point use the same
  [field description](#field-descriptions).
  language is ``'eng'``, ``'fra'`` or ``None`` for fields without
  separate language versions.
  ``include_existing=False`` would *exclude* standard CKAN fields.

``languages``
  ``['eng', 'fra']``, useful for keeping literal ``eng`` and ``fra``
  strings out of the source code

``vocabularies``
  a dict mapping CKAN tag vocabulary ids to their corresponding dataset
  field ids


Field Descriptions
~~~~~~~~~~~~~~~~~~

Dataset and resource field descriptions are dicts containing the following:

``'id'``
  the CKAN internal name for this field, e.g. ``"notes"``, ``"title"``, ...
  ; note that these do not include French versions of fields such as
  ``"notes_fra"``; if you need both language versions use the
  ``dataset_field_iter`` or ``resource_field_iter`` methods above

``'label'``
  ``{'eng': English field label, 'fra': French field label}``

``'description'``
  ``{'eng': English field description, 'fra': French field description}``

``'example'``
  an example value used as a placeholder in the form, with only one language
  version avalable, so we're currently hiding it on French fields

``'existing'``
  ``True`` if this field exists in the default CKAN schema in at least
  one language, used by ``dataset_field_iter`` and ``resource_field_iter``
  to filter English fields when passed ``include_existing=False``

``'bilingual'``
  ``True`` if there are two separate versions of this field, one for
  English and one for French with ``"_fra"`` appended to the ``'id'``,
  not for fields that contain no language or both languages in the
  same value

``'choices'``
  if this key exists then the user must select one of the choices
  in this list; the list contains dicts with the following:

  ``'eng'``
    English text for this choice to display to English users

  ``'fra'``
    French text for this choice to display to French users

  ``'key'``
    valid field value

  ``'id'``
    an id for this choice from the proposed choices list, if available

  ``'pilot_uuid'``
    correspongind UUID for this choice when importing pilot data

``'choices_by_pilot_uuid'``
  if ``'choices'`` exists then this will be a dict mapping pilot UUIDs
  to the choices dicts above

``'type'``
  one of the following values:

  ``'primary_key'``
    the id field

  ``'choice'``
    select one of the choices

  ``'calculated'``
    value determined by CKAN

  ``'fixed'``
    fixed value for all datasets equal to example provided

  ``'slug'``
    text suitable for use as part of a URL: lowercase and hyphens

  ``'text'``
    free-form text

  ``'tag_vocabulary'``
    select 0 or more values from choices

  ``'tags'``
    free-form tags

  ``'date'``
    iso8601 date

  ``'boolean'``
    one-character strings ``0`` or ``1``

  ``'url'``
    fully qualified URL

  ``'integer'``
    integer

  ``'image_url'``
    fully qualified URL to an image file
