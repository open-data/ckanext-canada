ckanext-canada
==============

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Features:

* Forms and Validation for GoC Metadata Schema

Installation:

* Use `open-data fork of CKAN <https://github.com/open-data/ckan>`_ ,
  branch canada-v2.6

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
  ``canada_forms``)

``canada_internal``
  templates for internal site and registration (requires
  ``canada_forms`` and ``canada_public``)

``canada_package``
  package processing between CKAN and Solr

``canada_obd``
  Open By Default site plugin


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
   - canada-v2.6
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


OD Configuration: development.ini or production.ini
---------------------------------------------------

The CKAN ini file needs the following settings for the registry server::

   ckan.plugins = dcat dcat_json_interface googleanalytics canada_forms canada_internal
        canada_public canada_package canada_activity datastore recombinant
        scheming_datasets fluent extendedactivity

For the public server use only::

   ckan.plugins = dcat dcat_json_interface googleanalytics canada_forms
        canada_public canada_package scheming_datasets fluent

   canada.portal_url = http://myserver.com

Both servers need::

   licenses_group_url = file://<path to this extension>/ckanext/canada/public/static/licenses.json

   ckan.i18n_directory = <path to this extension>/build

   ckan.auth.create_dataset_if_not_in_organization = false

   ckan.activity_streams_email_notifications = false

   ckan.datasets_per_page = 10

   googleanalytics.id = UA-1010101-1 (your analytics account id)
   googleanalytics.account = Account name (i.e. data.gov.uk, see top level item at https://www.google.com/analytics)
   loop11.key = bca42f834d21755c050b437dcc881bcde963b08e


OD Configuration: Adding WET Resource files
-------------------------------------------
For the use of the Portal or Registry sites, the installation of the WET-BOEW theme extension isn't required anymore, because the templates it provides are now included in the ``canada_public`` an ``canada_internal`` plugins. All what's needed is to add the resource files:
  
Externally hosted:
   Set ``wet_boew.url`` (in your .ini file) to the root URL where the WET resources are hosted:
   
   *Example*::

      wet_boew.url = http://domain.com/wet-boew/v4.0.31


Internally Hosted:
   1. Extract the WET 4.0.x core CDN and desired themes cdn package to a folder::
   
         export WET_VERSION=v4.0.31
         mkdir wet-boew && curl -L https://github.com/wet-boew/wet-boew-cdn/archive/$WET_VERSION.tar.gz | tar -zx --strip-components 1 - -directory=wet-boew
         mkdir GCWeb && curl -L https://github.com/wet-boew/themes-cdn/archive/$WET_VERSION-gcweb.tar.gz | tar -zx --strip-components 1 --directory=GCWeb
   2. Set the ``extra_public_paths`` settings to that path where the files are extracted:
   
      *Example*::
      
         extra_public_paths = /home/user/wet-boew/v4.0.31
 
Additional Configuration:
   Set ``wet_theme.geo_map_type`` to indicate what style of `WET Geomap widget <http://wet-boew.github.io/wet-boew/docs/ref/geomap/geomap-en.html>`_ to use. Set this to either 'static' or 'dynamic'::
 
      wet_theme.geo_map_type = static



OBD Configuration
-----------------

We use a different list of plugins for Open By Default::

   ckan.plugins = dcat dcat_json_interface googleanalytics canada_forms
        canada_obd canada_package wet_boew_gcweb scheming_datasets
        fluent cloudstorage

   ckan.extra_resource_fields = language

Update OBD documents (example)::
   touch /tmp/marker
   import_xml2obd.py  pull ./production.ini ./obd-repo  > /tmp/pull.log
   find ./obd-repo -type f -newer /tmp/marker > ./new.txt
   import_xml2obd.py ./obd-repo  http://obd-dev.canadacentral.cloudapp.azure.com/ckan ./new.txt >  ./data/obd-20170704.jsonl
   import_xml2obd.py upload  http://obd-dev.canadacentral.cloudapp.azure.com/ckan <site API key> ./data/obd-20170704.jsonl ./obd-repo

Delete OBD documents (only change the dataset state):
   import_xml2obd.py delete ./to_delete.csv ./obd-repo  http://obd-dev.canadacentral.cloudapp.azure.com/ckan <site API key>

Verify OBD documents:
   # check resource exists
   import_xml2obd.py <site_url> azure_user azure_key azure_container

   # check duplicates
   import_xml2obd.py de-dup <site_url>

Configuration: Solr
----------------------

This extension uses a custom Solr schema based on the ckan 2.6 schema. You can find the schema in the root directory of the project.
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

Integrating with OGC Django Search App
--------------------------------------

Optionally the extension can integrate with the OGC Search application by updating the
custom Solr core used by the search application in addition to the regular CKAN Solr core.
When enabled, the extension will update the second Solr core after a package update or delete.
The hooks for this are set in the DataGCCAPackageController. For this to happen, two configuration values
need to be set::

   ckanext.canada.adv_search_enabled = True
   ckanext.canada.adv_search_solr_core = http://127.0.0.1:8983/solr/core_od_search

The first setting must to set to true to enable the integration, and the second setting provides the URL to the
custom OGC Search core.

The Django search code uses the NLTK toolkit (http://www.nltk.org/) to extract a summarized description. To install
the NLTK parsers, run the following python commands after activating the virtual environment::

   import nltk
   nltk.download('punkt')

If not integrating, these settings may be omitted or ``ckanext.canada.adv_search_enabled`` may be set to ``False``.


