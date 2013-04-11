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



