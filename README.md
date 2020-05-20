# ckanext-canada

Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

Features:

* Forms and Validation for GoC Metadata Schema

Installation:

* Use [open-data fork of CKAN](https://github.com/open-data/ckan>),
  branch canada-v2.6

From a clean database you must run:

```bash
ckanapi load organizations -I transitional_orgs.jsonl
```

Once to create the organizations this extension requires
before loading any data.


## Plugins in this extension

`canada_forms`
  dataset forms for Open Canada metadata schema

`canada_public`
  base and public facing Open Canada templates (requires
  `canada_forms`)

`canada_internal`
  templates for internal site and registration (requires
  `canada_forms`` and `canada_public``)

`canada_package`
  package processing between CKAN and Solr

`canada_obd`
  Open By Default site plugin


## Requirements

Project | Github group/repo | Branch | Plugins
--- | --- | --- | ---
CKAN | [open-data/ckan](https://github.com/open-data/ckan) | canada-v2.6 | N/A
canada extension | [open-data/ckanext-canada](https://github.com/open-data/ckanext-canada) | master | see above
Scheming extension | [open-data/ckanext-scheming](https://github.com/open-data/ckanext-scheming) | master | scheming_datasets
Fluent extension | [open-data/ckanext-fluent](https://github.com/open-data/ckanext-fluent>) | master | N/A
ckanapi | [ckan/ckanapi](https://github.com/ckan/ckanapi>) | master | N/A
ckanext-googleanalytics | [ofkn/ckanext-googleanalytics](https://github.com/okfn/ckanext-googleanalytics>) | master | googleanalytics
Recombinant extension | [open-data/ckanext-recombinant](https://github.com/open-data/ckanext-recombinant) | master | recombinant


## OD Configuration: development.ini or production.ini

The CKAN ini file needs the following settings for the registry server:

```ini
ckan.plugins = dcat dcat_json_interface googleanalytics canada_forms canada_internal
        canada_public canada_package canada_activity datastore recombinant
        scheming_datasets fluent extendedactivity
```

For the public server use only:

```ini
ckan.plugins = dcat dcat_json_interface googleanalytics canada_forms
        canada_public canada_package scheming_datasets fluent

canada.portal_url = http://myserver.com

adobe_analytics.js = //path to the js file needed to trigger Adobe Analytics

foresee.survey_js_url = // path to the js file for adding a layer of Foresee survey for conducting user experience testing 
```

Both servers need:

```ini
licenses_group_url = file://<path to this extension>/ckanext/canada/public/static/licenses.json

ckan.i18n_directory = <path to this extension>/build

ckan.auth.create_dataset_if_not_in_organization = false

ckan.activity_streams_email_notifications = false

ckan.datasets_per_page = 10

googleanalytics.id = UA-1010101-1 (your analytics account id)
googleanalytics.account = Account name (i.e. data.gov.uk, see top level item at https://www.google.com/analytics)
```

## OD Configuration: Adding WET Resource files

For the use of the Portal or Registry sites, the installation of the WET-BOEW theme extension isn't required anymore, because the templates it provides are now included in the `canada_public` and `canada_internal` plugins. All what's needed is to add the resource files:

### Externally hosted:

Set `wet_boew.url` (in your .ini file) to the root URL where the WET resources are hosted:

*Example*:

```ini
wet_boew.url = http://domain.com/wet-boew/v4.0.31
```

### Internally Hosted:

1. Extract the WET 4.0.x core CDN and desired themes cdn package to a folder::

	```bash
        export WET_VERSION=v4.0.31
        export GCWEB_VERSION=v5.1
        mkdir wet-boew && curl -L https://github.com/wet-boew/wet-boew-cdn/archive/$WET_VERSION.tar.gz | tar -zx --strip-components 1 - -directory=wet-boew
        mkdir GCWeb && curl -L https://github.com/wet-boew/themes-cdn/archive/$GCWEB_VERSION-gcweb.tar.gz | tar -zx --strip-components 1 --directory=GCWeb
	```

2. Set the `extra_public_paths` settings to that path where the files are extracted:

	*Example*:

	```ini
	extra_public_paths = /home/user/wet-boew/v4.0.31
	```


### Additional Configuration:

Set `wet_theme.geo_map_type` to indicate what style of [WET Geomap widget](http://wet-boew.github.io/wet-boew/docs/ref/geomap/geomap-en.html) to use. Set this to either 'static' or 'dynamic':

```ini
wet_theme.geo_map_type = static
```


## OBD Configuration

We use a different list of plugins for Open By Default:

```ini
ckan.plugins = dcat dcat_json_interface googleanalytics canada_forms
        canada_obd canada_package wet_boew_gcweb scheming_datasets
        fluent cloudstorage

ckan.extra_resource_fields = language
```

Update OBD documents (example):

```bash
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
```

## Configuration: Solr

This extension uses a custom Solr schema based on the ckan 2.6 schema. You can find the schema in the root directory of the project.
Overwrite the default CKAN Solr schema with this one in order to enable search faceting over custom metadata fields.

You will need to rebuild your search index using:

```bash
paster --plugin ckan search-index rebuild
```

## Compiling the updated French localization strings

Each time you install or update this extension you need to install the
updated translations by running:

```bash
bin/build-combined-ckan-mo.sh
```

This script overwrites the ckan French translations by combining it with
ours.

# Integrating with OGC Django Search App

Optionally the extension can integrate with the OGC Search application by updating the
custom Solr core used by the search application in addition to the regular CKAN Solr core.
When enabled, the extension will update the second Solr core after a package update or delete.
The hooks for this are set in the DataGCCAPackageController. For this to happen, two configuration values
need to be set:

```ini
ckanext.canada.adv_search_enabled = True
ckanext.canada.adv_search_solr_core = http://127.0.0.1:8983/solr/core_od_search
```

The first setting must to set to true to enable the integration, and the second setting provides the URL to the
custom OGC Search core.

The Django search code uses the NLTK toolkit (http://www.nltk.org/) to extract a summarized description. To install
the NLTK parsers, run the following python commands after activating the virtual environment:

```ini
import nltk
nltk.download('punkt')
```

If not integrating, these settings may be omitted or `ckanext.canada.adv_search_enabled` may be set to `False`.

## Proactive Disclosure Data Flow

![data flow diagram](pd-data-flow.svg)

1. ckanext-canada (this repository)
   - [PD yaml files](ckanext/canada/tables) are read by ckanext-recombinant and used to
     generate most of the pages, tables, triggers and metadata shown.
   - [add+edit forms](ckanext/canada/templates/internal/recombinant) use form snippets
     from ckanext-scheming and validation enforced by datastore triggers. They are
     currently part of the ckanext-canada extension but should be moved into
     ckanext-recombinant or another reusable extension once the trigger-validation
     pattern becomes standardized
   - [datatable preview](ckanext/canada/templates/internal/package/wet_datatable.html)
     is part of ckanext-canada because this code predates the datatables view feature
     that is now part of ckan. It should be removed from here so we can use the ckan
     datatable view instead
   - [filter scripts](bin/filter) cover all the business logic required to "clean" PD data
     before it is released to the public. a [Makefile](bin/pd/Makefile) is used to
     extract raw CSV data, make backups, run these filters and publish CSV data
2. [ckanext-recombinant](https://github.com/open-data/ckanext-recombinant)
   - XLSX data dictionary
   - reference lists
   - API docs
   - schema json
   - delete form
   - XLSX template UL/DL
   - combine command
3. [ckan](https://github.com/ckan/ckan)
   - datastore API
   - datastore triggers
   - datastore tables
   - dataset metadata
4. CSV files
   - raw CSV data
   - nightly backups
   - published CSV data
5. [deplane](https://github.com/open-data/deplane)
   - data element profile
6. [ogc_search](https://github.com/open-data/ogc_search)
   - advanced search
