#!/bin/bash

set -e

HERE=`dirname $0`
cd "$HERE/.."
python setup.py compile_catalog -f -d ../ckan/ckan/i18n --domain ckan --locale fr
python setup.py compile_catalog -d ckanext/canada/i18n --domain ckanext-canada
python setup.py compile_catalog -d ../ckanext-recombinant/ckanext/recombinant/i18n --domain ckanext-recombinant
python setup.py compile_catalog --locale en -d ../goodtables/i18n/ -D goodtables
python setup.py compile_catalog --locale fr -d ../goodtables/i18n/ -D goodtables
python setup.py compile_catalog --locale en -d ../ckanext/validation/i18n -D ckanext-validation
python setup.py compile_catalog --locale fr -d ../ckanext/validation/i18n -D ckanext-validation
