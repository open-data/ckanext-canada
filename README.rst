ckanext-canada
==============

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Team: Ian Ward, Ross Thompson, Peder Jakobsen, Denis Zgonjanin

Features:

* Forms and Validation for GoC Metadata Schema

Installation:

* Use `open-data fork of CKAN <https://github.com/open-data/ckan>`_ ,
  branch canada-v2.3

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
   - canada-v2.3
   - N/A
 * - data.gc.ca extension
   - `open-data/ckanext-canada <https://github.com/open-data/ckanext-canada>`_
   - wet4-scheming
   - * canada_forms
     * canada_internal
     * canada_public
     * canada_package
 * - WET-BOEW theme
   - `open-data/ckanext-wet-boew <https://github.com/open-data/ckanext-wet-boew>`_
   - wet4-scheming
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
        canada_public canada_package wet_theme datastore recombinant
        scheming_datasets fluent

   recombinant.tables = ckanext.canada:recombinant_tables.json

For the public server use only::

   ckan.plugins = googleanalytics canada_forms
        canada_public canada_package wet_theme
        scheming_datasets fluent

   canada.portal_url = http://myserver.com

Both servers need::

   scheming.dataset_schemas =
       ckanext.canada:schemas/dataset.yaml
       ckanext.canada:schemas/info.yaml

   scheming.presets = ckanext.scheming:presets.json
       ckanext.fluent:presets.json
       ckanext.canada:schemas/presets.json

   licenses_group_url = file://<path to this extension>/ckanext/canada/public/static/licenses.json

   ckan.i18n_directory = <path to this extension>/build

   ckan.auth.create_dataset_if_not_in_organization = false

   ckan.activity_streams_email_notifications = false

   ckan.datasets_per_page = 10

   googleanalytics.id = UA-1010101-1 (your analytics account id)
   googleanalytics.account = Account name (i.e. data.gov.uk, see top level item at https://www.google.com/analytics)


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

Automating ATI and PD Dataset Promotion from Registry to Portal (Optional)
--------------------------------------------------------------------------

This section outlines the process of automating the promotion of ATI
and PD datasets from the Registry to the Portal through the invocation
of the ``bin/reg2portal.sh`` and ``bin/csv2solr.sh`` scripts.

*The Registry*

On the registry, the ``bin/reg2portal.sh`` script pushes specified
datasets to the registry's CKAN installation. It takes the following
parameters:

  ``CKAN-INI-FILE``
    The path to the configuration file of the CKAN registry installation

  ``PORTAL-URL``
    The URL of the CKAN public portal

  ``API-KEY``
    The API key to use in invoking the CKAN API to propagate ATI and PD
    datasets to the portal

  ``TARGET-DATASET:PACKAGE-ID ...``
    One or more space-separated and colon-delimited mappings
    (e.g. ``ati:00000000-0000-0000-0000-000000000000``) between target
    datasets and their respective names or identifiers on the portal

  ``VIRTUAL-ENV-HOME`` (optional)
    If present, the root directory of the python virtual environment to
    activate, under which the script will operate

First, the execution of the script activates the virtual environment
if specified.

Then, it uses ckanext-recombinant to parse all target datasets from
its (JSON) recombinant tables file. For each such target dataset
mapped on the command line, the execution queries ckanext-recombinant
for its respective dataset types (e.g.; ati-none, ati-summaries).
The script calls ckanext-recombinant to combine CKAN content for
each of these dataset types into a temporary .csv file for promotion.

The script then calls, for each target dataset mapped on the command
line, the ``bin\reg2portal.py`` script, specifying:
* the CKAN configuration file
* the URL for the portal
* the API key
* the mapped identifier for the target dataset
* all paths to temporary combined .csv files germane to the target dataset

The ``bin\reg2portal.py`` script invokes the CKAN API to patch the
package by its specified identifier, clearing out existing resources
and uploading the combined .csv files to the portal in their stead.

Finally, the ``bin\reg2portal.sh`` script cleans up the temporary
files it created in its operations.

For the registry host, a sample crontab entry automating daily
ATI and PD propagation (specifying names for the datasets on the
registry, to a portal on host devubu3) follows:

    ``0 2 * * * /opt/open-data/ckanext-canada/bin/reg2portal.sh /opt/open-data/ckanext-canada/development.ini http://devubu3:5000 141d4974-7d48-47b9-a003-b09d5f8e7c3a ati:ati pd:pd /opt/venvs/env-ckan-2.1 >> /var/log/reg2portal.log 2>&1``

*The Portal*

On the portal, the ``bin/csv2solr.sh`` script rebuilds the configured
local solr core with the content of specified datasets from the local
CKAN installation. It takes the following parameters:

  ``CKAN-INI-FILE``
    The path to the configuration file of the CKAN portal installation

  ``TARGET-DATASET:PACKAGE-ID ...``
    One or more space-separated and colon-delimited mappings
    (e.g. ``pd:11111111-1111-1111-1111-111111111111``) between target
    datasets and their respective names or identifiers on the portal

  ``VIRTUAL-ENV-HOME`` (optional)
    If present, the root directory of the python virtual environment to
    activate, under which the script will operate

First, the execution of the script activates the virtual environment
if specified.

Then, uses ckanext-recombinant to parse all target datasets from
its (JSON) recombinant tables file. For each such target dataset
mapped on the command line, the script calls ckanext-canada to
locate its associated resources on the portal. The operation
downloads these resources and uses them to rebuild the target
dataset from them via ckanext-canada.

Finally, the script cleans up the temporary files it created
in its operations.

For the portal host, a sample crontab entry automating daily
ATI and PD solr core rebuild (specifying identifiers for the
datasets on the portal) follows:

    ``0 2 * * * /opt/open-data/ckanext-canada/bin/csv2solr.sh /opt/open-data/ckanext-canada/development.ini ati:636893c9-e4b4-451c-b652-571f2f1349dd pd:ca8f5f4b-b5d8-4884-a8d5-4a87dca4f6f6 /opt/venvs/env-ckan-2.3 >> /var/log/csv2solr.log 2>&1``
