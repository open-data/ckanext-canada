#!/bin/bash

set -e

HERE=`dirname $0`
cd "$HERE/.."
python setup.py compile_catalog -d ckanext/canada/i18n --domain ckanext-canada
