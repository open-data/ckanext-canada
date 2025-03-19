# CKANEXT Canada

## Government of Canada CKAN Extension - Extension à CKAN du Gouvernement du Canada

[![CircleCI](https://dl.circleci.com/status-badge/img/gh/open-data/ckanext-canada/tree/master.svg?style=svg)](https://dl.circleci.com/status-badge/redirect/gh/open-data/ckanext-canada/tree/master)

| Table of Contents    |
| -------- |
| [Requirements](#requirements)  |
| [Installation](#installation) |
| [Plugins](#plugins)    |
| [Configurations](#configurations)    |
| [SOLR](#solr)    |
| [Localization](#localization)    |
| [Migrations](#migrations)    |
| [Data Flows](#data-flows)    |

## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.6 and earlier | no    |
| 2.7             | no    |
| 2.8             | no    |
| 2.9             | no    |
| 2.10             | yes    |
| 2.11             | no    |

Compatibility with Python versions:

| Python version    | Compatible?   |
| --------------- | ------------- |
| 2.7 and earlier | no    |
| 3.7 and later            | yes    |

Required extensions, forks, and branches:

* [CKAN Fork](https://github.com/open-data/ckan/tree/canada-v2.10) *(canada-v2.10 branch)*
* [CKANAPI](https://github.com/ckan/ckanapi)
* [CKANEXT Recombinant](https://github.com/open-data/ckanext-recombinant)
* [CKANEXT Fluent](https://github.com/ckan/ckanext-fluent)
* [CKANEXT Scheming](https://github.com/ckan/ckanext-scheming)
* [CKANEXT Security Fork](https://github.com/open-data/ckanext-security/tree/canada-v2.10) *(canada-v2.10 branch)*
* [CKANEXT Validation Fork](https://github.com/open-data/ckanext-validation/tree/canada-v2.10) *(canada-v2.10 branch)*
* [Frictionless-py Fork](https://github.com/open-data/frictionless-py/tree/canada-v2.10) *(canada-v2.10 branch)*
* [CKANEXT XLoader Fork](https://github.com/open-data/ckanext-xloader/tree/canada-v2.10) *(canada-v2.10 branch)*
* [CKANEXT CloudStorage Fork](https://github.com/open-data/ckanext-cloudstorage/tree/canada-v2.10) *(canada-v2.10 branch)*
* [CKANEXT DCAT Fork](https://github.com/open-data/ckanext-dcat/tree/canada-v2.10) *(canada-v2.10 branch)*
* [CKANEXT Power BI View](https://github.com/open-data/ckanext-power-bi)
* [CKANEXT Open API View](https://github.com/open-data/ckanext-openapiview)
* [CKANEXT GC Notify](https://github.com/open-data/ckanext-gcnotify)

## Installation

To install ckanext-canada:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv:
  ```
  git clone https://github.com/open-data/ckanext-canada.git
  cd ckanext-canada
  pip install -e .
	pip install -r requirements.txt
  python setup.py develop
  ```
3. Add the [plugin entry points](#plugins) to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).


## Plugins

### Theme

`canada_theme` adds templates, template helpers, and webassets . This plugin should load first.

### Forms

`canada_forms` adds dataset and resource forms and extra blueprint functionality for them. This should load after `canada_theme` but before the other `canada` plugins

### Public

`canada_public` adds actions, logic, and functionality specific to the Canada data portal.

### Internal

`canada_internal` adds actions, logic, and functionality specific to the Canada data registry.

### Datasets

`canada_datasets` extends the ckanext-scheming plugin, modifying specific functionality for the Canada data portal.

### Security

`canada_security` extends the ckanext-security plugin, modifying specific functionality for the Canada data portal.

## Configurations

### Portal

The CKAN ini file needs the following settings for the portal:

```ini
ckan.plugins = canada_theme
               activity
               dcat
               dcat_json_interface
               canada_forms
               canada_public
               canada_datasets
               scheming_organizations
               fluent
               recombinant
               cloudstorage
               canada_security
               datastore
               text_view
               image_view
               datatables_view
               webpage_view
               openapi_view
               power_bi_view
```

### Registry

The CKAN ini file needs the following settings for the registry:

```ini
ckan.plugins =  canada_theme
                activity
                validation
                canada_forms
                canada_internal
                canada_public
                recombinant
                datastore
                dsaudit
                canada_datasets
                scheming_organizations
                fluent
                cloudstorage
                canada_security
                xloader
                datatables_view
                image_view
                text_view
                webpage_view
                openapi_view
                power_bi_view
                gcnotify
```

### General

Both applications need at least the following:

```ini
ckanext.power_bi.internal_i18n = true

recombinant.definitions = ckanext.canada:tables/ati.yaml
                          ckanext.canada:tables/briefingt.yaml
                          ckanext.canada:tables/qpnotes.yaml
                          ckanext.canada:tables/contracts.yaml
                          ckanext.canada:tables/contractsa.yaml
                          ckanext.canada:tables/grants.yaml
                          ckanext.canada:tables/hospitalityq.yaml
                          ckanext.canada:tables/reclassification.yaml
                          ckanext.canada:tables/travela.yaml
                          ckanext.canada:tables/travelq.yaml
                          ckanext.canada:tables/wrongdoing.yaml
                          ckanext.canada:tables/inventory.yaml
                          ckanext.canada:tables/consultations.yaml
                          ckanext.canada:tables/service.yaml
                          ckanext.canada:tables/dac.yaml
                          ckanext.canada:tables/nap5.yaml
                          ckanext.canada:tables/experiment.yaml
                          ckanext.canada:tables/adminaircraft.yaml

recombinant.tables = ckanext.canada:recombinant_tables.yaml

scheming.dataset_schemas =
    ckanext.canada:schemas/dataset.yaml
    ckanext.canada:schemas/info.yaml
    ckanext.canada:schemas/prop.yaml

scheming.presets =
    ckanext.scheming:presets.json
    ckanext.fluent:presets.json
    ckanext.canada:schemas/presets.yaml
    ckanext.validation:presets.json

scheming.organization_schemas = ckanext.canada:schemas/organization.yaml

ckanext.csrf_filter.same_site = Strict
ckanext.csrf_filter.exempt_rules = ^/datatable.*
ckanext.xloader.clean_datastore_tables = True
ckanext.validation.clean_validation_reports = True
ckan.feeds.pretty = True
ckan.feeds.include_private = True
ckan.auth.create_dataset_if_not_in_organization = false
ckan.activity_streams_email_notifications = false
ckan.record_private_activity = True
ckan.activity_streams_enabled = True
ckan.csrf_protection.ignore_extensions = False

licenses_group_url = file://<path to this extension>/ckanext/canada/public/static/licenses.json

ckanext.canada.datastore_source_domain_allow_list = canada.ca www.canada.ca

ckan.locales_offered = en fr
```

## SOLR

This extension uses a custom Solr schema based on the CKAN 2.10 schema. Overwrite the default CKAN Solr schema with this one in order to enable search faceting over custom metadata fields.

You will need to rebuild your search index using:

```bash
ckan -c <INI> search-index rebuild
```

## Localization

To update strings in the translation files:

```bash
python setup.py extract_messages
```

Extract messages will gather `gettext` calls in Python, JS, and Jinja2 files. It will also use th custom PD extractor to get specific strings for the Recombinant YAML files.

To update the English and French catalog files:

```bash
python setup.py update_catalog
```

This will update both English and French PO files. You will need to confirm that there are NO `fuzzy` translations in either of the PO files.

After updating the PO files and ensuring that there are no fuzzies, you may commit the two PO files along with the POT file.

### Compiling localization strings

Each time you install or update this extension you need to install the
updated translations by running:

```bash
python setup.py compile_catalog
```

## Migrations

### Creating a plugin migration

If adding or modifying custom database models in the CKAN framework, you can create a migration following the [docs.](https://docs.ckan.org/en/2.10/contributing/database-migrations.html)

After making the migration, you can apply it with:
```shell
ckan -c <INI> db upgrade --plugin=<PLUGIN NAME>
```
or (execute twice):
```shell
ckan -c <INI> db pending-migrations --apply
ckan -c <INI> db pending-migrations --apply
```

### Manually reloading Proactive Disclosure Data

This needs to be done if the data types change in the schema. The data will need to be exported, deleted from the database, and then reloaded so the new datatypes are created properly in the database.

1. Extract the current version of the data from the registry for each table, e.g for contracts migrations we need contracts.csv and contracts-nil.csv:

```bash
mkdir migrate-contracts  # a new working directory
ckan -c <INI> recombinant combine contracts contracts-nil -d migrate-contracts
```

2. Remove the old tables from the database. Deleting contracts will delete both the contracts and contracts-nil tables:

```bash
ckan -c <INI> recombinant delete contracts
```

3. Reload the data

```bash
cd migrate-contracts
ckan -c <INI> recombinant load-csv contracts.csv contracts-nil.csv
```

### Advanced data migrations

Any advanced data migrations should be created in the [DataOps repo](https://github.com/open-data/data-ops) and should adopt the concept that the Python script runs independatly from this plugin code and CKAN application context.

## Data Flows

### Open Data Flow

The custom command `ckan -c <INI> canada portal-update` is a worker function that copies datasets, resources, views, and datastore tables from the Registry to the Portal. This relies on the `activity` plugin and the capability to record Private activity.

1. Datasets that are "ready to publish" and have a "published date" are proccessed into the `canada copy-datasets` command;
2. Gathers resources, views, and datastore tables from the Registry;
3. If there are differences between the Registry and Portal dataset/resources, then copies the Registry data to the Portal (including dumping the Registry datastore table into the Portal datastore table).

The Django Search App uses an action API endpoint from the `activity` plugin to add/update/remove datasets from the Django Search Index.

### Proactive Disclosure Data Flow

![data flow diagram](docs/pd-data-flow.svg)

1. ckanext-canada (this repository)
   - [PD yaml files](ckanext/canada/tables) are read by ckanext-recombinant and used to
     generate most of the pages, tables, triggers and metadata shown.
   - [add+edit forms](ckanext/canada/templates/recombinant) use form snippets
     from ckanext-scheming and validation enforced by datastore triggers. They are
     currently part of the ckanext-canada extension but should be moved into
     ckanext-recombinant or another reusable extension once the trigger-validation
     pattern becomes standardized
   - [datatable preview](ckanext/canada/templates/snippets/pd_datatable.html)
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
6. [ogc_search](https://github.com/open-data/oc_search)
   - advanced search
