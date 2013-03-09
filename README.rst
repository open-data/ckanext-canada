ckanext-canada
==============

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Team: Ian Ward, Ross Thompson, Peder Jakobsen

Features:

* Forms and Validation for GoC Metadata Schema (in progress)
* Batch import of data (coming, currently in a separate extension)

Installation:

* Use CKAN Version: 2.0+
* After every pull or fetch, use ``python setup.py develop`` just in case entry points have changed.

From a clean database you must run::

   paster canada create-vocabularies -c <path to config file>

Once to create the tag vocabularies this extension requires before loading
any data.

Plugins
-------

* ``canada_forms`` - dataset forms for data.gc.ca metadata schema
* ``canada_public`` - base and public facing data.gc.ca templates (requires
  ``canada_forms`` and ``wet_theme`` from ckanext-wet-boew)
* ``canada_internal`` - templates for internal site and registration (requires
  ``canada_forms`` and ``canada_public``)

