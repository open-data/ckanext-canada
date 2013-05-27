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

``canada_package``
  package processing between CKAN and Solr


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
     * canada_package
 * - WET-BOEW theme
   - `open-data/ckanext-wet-boew <https://github.com/open-data/ckanext-wet-boew>`_
   - master
   - * wet_theme
 * - WET-BOEW
   - `open-data/wet-boew <https://github.com/open-data/wet-boew>`_
   - master
   - N/A
 * - ckanapi
   - `open-data/ckanapi <https://github.com/open-data/ckanapi>`_
   - master
   - N/A


Configuration: development.ini or production.ini
------------------------------------------------

The CKAN ini file needs the following plugins for the registry server::

   ckan.plugins = stats canada_forms canada_internal canada_public canada_package wet_theme

For the public server use only::

   ckan.plugins = stats canada_forms canada_public canada_package wet_theme

CKAN also needs to be able to find the licenses file for the license list
to be correctly populated::

   licenses_group_url = http://<ckan instance>/static/licenses.json

Users that don't belong to an Organization should not be allowed to create
datasets, without this setting the form will be presented but fail during
validation::

   ckan.auth.create_dataset_if_not_in_organization = false

We aren't using notification emails, so they need to be disabled::

   ckan.activity_streams_email_notifications = false


Configuration: who.ini
----------------------

The following lines need to be changed in ``[plugin:friendlyform]``::

   -post_login_url = /user/logged_in
   -post_logout_url = /user/logged_out
   +post_login_url =
   +post_logout_url =


Configuration: Solr
----------------------

This extension uses a custom Solr schema based on the ckan 2.0 schema. You can find the schema in the root directory of the project. 
Overwrite the default CKAN Solr schema with this one in order to enable search faceting over custom metadata fields.

You will need to rebuild your search index using::

   paster --plugin ckan search-index rebuild



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
  ``{'eng': English example value, 'fra': French example value}``

``'existing'``
  ``True`` if this field exists in the default CKAN schema in at least
  one language, used by ``dataset_field_iter`` and ``resource_field_iter``
  to filter English fields when passed ``include_existing=False``

``'bilingual'``
  ``True`` if there are two separate versions of this field, one for
  English and one for French with ``"_fra"`` appended to the ``'id'``,
  ``False`` for fields that contain no language component or have both
  languages stored together in one field, e.g. choice fields

``'mandatory'``
  ``"all"`` if always required, ``"geo"`` if required for geo datasets,
  ``"raw"`` if required for raw datasets, ``None`` if not required

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

  ``'subject_ids'``
    topic_category choices only: this field contains a list of ids from the
    subject choices list that correspond to this topic_category choice

``'choices_by_pilot_uuid'``
  if ``'choices'`` exists then this will be a dict mapping pilot UUIDs
  to the choices dicts above

``'type'``
  one of the following values:

  ``'primary_key'``
    the id field

  ``'choice'``
    select one of the ``'choices'`` list above

  ``'calculated'``
    value determined by code in CKAN or this plugin, not for user-entry

  ``'fixed'``
    fixed value for all datasets, all datasets will use ``'example'`` value
    above

  ``'slug'``
    text suitable for use as part of a URL: lowercase Unicode characters and
    hyphens

  ``'text'``
    free-form text

  ``'tag_vocabulary'``
    allow selection of 0 or more values from ``'choices'`` list above

  ``'keywords'``
    free-form keywords in a string separated with commas; Unicode
    letter characters, hyphen (-) and single spaces between words are allowed

  ``'date'``
    iso8601 date: YYYY-MM-DD

  ``'boolean'``
    ``True`` or ``False`` (not strings, but strings are accepted when setting)

  ``'url'``
    fully qualified URL

  ``'integer'``
    integer value in base 10

  ``'image_url'``
    fully qualified URL to an image file (gif, png or jpg)

``'ui_options'``
  if present a list containing strings such as ``'disabled'`` or ``'hidden'``
  which affect the form presented to users entering datasets


Google Analytics Integration
----------------------------

`okfn/ckanext-googleanalytics <https://github.com/okfn/ckanext-googleanalytics>`_ is used for Google Analytics integration. 
Follow these steps to integrate:

1. $ pip install -e  git+https://github.com/okfn/ckanext-googleanalytics.git#egg=ckanext-googleanalytics

2. Edit your CKAN ini file to add the Google Analytics tracking parameters::

      googleanalytics.id = UA-1010101-1
      googleanalytics.account = Account name (i.e. data.gov.uk, see top level item at https://www.google.com/analytics)

3. To the list of installed extensions, add `googleanalytics`. For example::

      ckan.plugins = stats json_preview googleanalytics canada_public canada_internal canada_forms wet_theme

Compiling the updated French localization strings
-------------------------------------------------

1. The open-data/ckan repo, branch canada-v2.0 should contain the compiled localization file. But if it doesn't, you can compile like so::

   $ python setup.py compile_catalog --locale fr

2. If you are not running CKAN from source, you need to copy the compiled .mo file to your deploy environment::

   $cp ckan_source/ckan/i18n/fr/LC_MESSAGES/ckan.mo virtualenv/ckan/src/ckan/ckan/i18n/fr/LC_MESSAGES/ckan.mo
