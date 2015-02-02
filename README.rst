ckanext-canada
==============

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Team: Ian Ward, Ross Thompson, Peder Jakobsen, Denis Zgonjanin

Features:

* Forms and Validation for GoC Metadata Schema

  * complete, but planning to migrate to ckanext-scheming once it is ready

Installation:

* Use `open-data fork of CKAN<https://github.com/open-data/ckan>`_,
  branch canada-v2.3

From a clean database you must run::

   paster canada create-vocabularies
   ckanapi load organizations -I transitional_orgs.jsonl

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
   - canada-v2.3
   - N/A
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
   - `ckan/ckanapi <https://github.com/ckan/ckanapi>`_
   - master
   - N/A
 * - ckanext-googleanalytics
   - `ofkn/ckanext-googleanalytics <https://github.com/okfn/ckanext-googleanalytics>`_
   - master
   - googleanalytics
 * - Recombinant tables extension
   - `open-data/ckanext-recombinant <https://github.com/open-data/ckanext-recombinant>`_
   - master
   - * recombinant


Configuration: development.ini or production.ini
------------------------------------------------

The CKAN ini file needs the following plugins for the registry server::

   ckan.plugins = googleanalytics canada_forms canada_internal canada_public canada_package wet_theme datastore recombinant

For the public server use only::

   ckan.plugins = googleanalytics canada_forms canada_public canada_package wet_theme

CKAN also needs to be able to find the licenses file for the license list
to be correctly populated::

   licenses_group_url = file://<path to this extension>/ckanext/canada/public/static/licenses.json

Combined ckan translations must be found the correct location::

   ckan.i18n_directory = <path to this extension>/build/i18n

Users that don't belong to an Organization should not be allowed to create
datasets, without this setting the form will be presented but fail during
validation::

   ckan.auth.create_dataset_if_not_in_organization = false

We aren't using notification emails, so they need to be disabled::

   ckan.activity_streams_email_notifications = false

Additionally, we want to limit the search results page to 10 results per page::

   ckan.datasets_per_page = 10

To integrate Google Analytics::

   googleanalytics.id = UA-1010101-1 (your analytics account id)
   googleanalytics.account = Account name (i.e. data.gov.uk, see top level item at https://www.google.com/analytics)

For the public server, also set the Drupal portal URL::

   canada.portal_url = http://myserver.com

For the registry server set up recombinant configuration for ATI summaries::

   recombinant.tables = ckanext.canada:recombinant_tables.json


Configuration: Solr
----------------------

This extension uses a custom Solr schema based on the ckan 2.3 schema. You can find the schema in the root directory of the project.
Overwrite the default CKAN Solr schema with this one in order to enable search faceting over custom metadata fields.

You will need to rebuild your search index using::

   paster --plugin ckan search-index rebuild



Working with the API
--------------------

To view a raw dataset using the api, use the ``ckanapi`` command line tool, e.g.::

  ckanapi package_show id=0007a010-556d-4f83-bb8e-6e22dcc62e84


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


Compiling the updated French localization strings
-------------------------------------------------

Each time you install or update this extension you need to install the
updated translations by running::

   bin/build-combined-ckan-mo.sh

This script overwrites the ckan French translations by combining it with
ours.

Linking with Drupal (Optional)
------------------------------

Data.gc.ca uses the Drupal web content management system to provide much of its content and to provide a means
for users to comment on and rate the data-sets found in the CKAN catalog. If using with Drupal, provide the database
connection string for the Drupal database in the CKAN configuration file::

   ckan.drupal.url =  postgresql://db_user:user_password/drupal_database

If this value is not defined, then the extension will not attempt to read from the Drupal database.

The installed Drupal site must have the opendata_package module enabled. In additional, 3 views are used by the
Drupal. Run the following SQL commands to create the necessary views in the Drupal database::

    create or replace view opendata_package_v as  select to_char(to_timestamp(c.changed::double precision),
        'YYYY-MM-DD'::text) AS changed, c.name, c.thread, f.comment_body_value, c.language, o.pkg_id FROM comment c
        JOIN field_data_comment_body f ON c.cid = f.entity_id
        JOIN opendata_package o ON (c.nid IN ( SELECT n.nid
        FROM node n
        WHERE n.nid = o.pkg_node_id and c.status = 1));

    create view opendata_package_rating_v as select avg(v.value)/25+1 as rating, p.pkg_id from opendata_package p
                 inner join votingapi_vote v on p.pkg_node_id = v.entity_id group by p.pkg_id;

    create or replace view opendata_package_count_v as select count(c.*), o.pkg_id from comment c
        inner join opendata_package o
        on o.pkg_node_id = c.nid and c.status = 1 group by o.pkg_id;

    alter view public.opendata_package_v owner to <db_user>;
    alter view public.opendata_package_rating_v owner to <db_user>;
    alter view public.opendata_package_count_v owner to <db_user>;

Substitute <db_user> with the appropriate SQL user account.
