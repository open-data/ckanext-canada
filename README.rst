ckanext-canada
==============

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Features:

* Forms and Validation for GoC Metadata Schema

Installation:

* Use `open-data fork of CKAN <https://github.com/open-data/ckan>`_ ,
  branch canada-v2.5

From a clean database you must run::

   ckanapi load organizations -I transitional_orgs.jsonl

Once to create the organizations this extension requires
before loading any data.


Plugins in this extension
-------------------------

``canada_forms``
  dataset forms for Open Canada metadata schema

``canada_public``
  base and public facing Open Canada templates (requires
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
   - canada-v2.5
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
 * - Scheming extension
   - `open-data/ckanext-scheming <https://github.com/open-data/ckanext-scheming>`_
   - master
   - scheming_datasets
 * - Fluent extension
   - `open-data/ckanext-fluent <https://github.com/open-data/ckanext-fluent>`_
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

The CKAN ini file needs the following settings for the registry server::

   ckan.plugins = googleanalytics canada_forms canada_internal
        canada_public canada_package wet_boew_theme_gc_intranet datastore recombinant
        scheming_datasets scheming_organizations fluent

   recombinant.tables = ckanext.canada:recombinant_tables.yaml

For the public server use only::

   ckan.plugins = googleanalytics canada_forms
        canada_public canada_package wet_boew_gcweb
        scheming_datasets scheming_organizations fluent

   canada.portal_url = http://myserver.com

Both servers need::

   scheming.organization_schemas = ckanext.canada:schemas/organization.yaml

   scheming.dataset_schemas =
       ckanext.canada:schemas/dataset.yaml
       ckanext.canada:schemas/info.yaml

   scheming.presets = ckanext.scheming:presets.json
       ckanext.fluent:presets.json
       ckanext.canada:schemas/presets.yaml

   licenses_group_url = file://<path to this extension>/ckanext/canada/public/static/licenses.json

   ckan.i18n_directory = <path to this extension>/build

   ckan.auth.create_dataset_if_not_in_organization = false

   ckan.activity_streams_email_notifications = false

   ckan.datasets_per_page = 10

   googleanalytics.id = UA-1010101-1 (your analytics account id)
   googleanalytics.account = Account name (i.e. data.gov.uk, see top level item at https://www.google.com/analytics)


Configuration: Solr
----------------------

This extension uses a custom Solr schema based on the ckan 2.5 schema. You can find the schema in the root directory of the project.
Overwrite the default CKAN Solr schema with this one in order to enable search faceting over custom metadata fields.

You will need to rebuild your search index using::

   paster --plugin ckan search-index rebuild


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

    create or replace view opendata_package_v as  SELECT to_char(to_timestamp(c.created::double precision), 'YYYY-MM-DD'::text) AS changed,
    c.name,
    c.thread,
    f.comment_body_value,
    c.language,
    o.pkg_id
     FROM comment c
     JOIN field_data_comment_body f ON c.cid = f.entity_id
     JOIN opendata_package o ON (c.nid IN ( SELECT n.nid
     FROM node n
    WHERE n.nid = o.pkg_node_id AND c.status = 1))
    ORDER BY c.thread;

    create view opendata_package_rating_v as select avg(v.value)/25+1 as rating, p.pkg_id from opendata_package p
                 inner join votingapi_vote v on p.pkg_node_id = v.entity_id group by p.pkg_id;

    create or replace view opendata_package_count_v as select count(c.*), o.pkg_id from comment c
        inner join opendata_package o
        on o.pkg_node_id = c.nid and c.status = 1 group by o.pkg_id;

    alter view public.opendata_package_v owner to <db_user>;
    alter view public.opendata_package_rating_v owner to <db_user>;
    alter view public.opendata_package_count_v owner to <db_user>;

Substitute <db_user> with the appropriate SQL user account.
