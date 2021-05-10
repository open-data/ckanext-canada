#!/bin/bash

set -e

HERE=`dirname $0`
cd "$HERE/.."
python setup.py compile_catalog -f -d ../ckan/ckan/i18n --domain ckan --locale fr
python setup.py compile_catalog -d ckanext/canada/i18n --domain ckanext-canada
python setup.py compile_catalog -d ../ckanext-recombinant/ckanext/recombinant/i18n --domain ckanext-recombinant
